import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Clock, MapPin, LinkIcon, Users } from "lucide-react";
import { toast } from "sonner";
import { TicketCard } from "@/components/TicketCard";
import { FeedbackSection } from "@/components/FeedbackSection";
import { EventGallery } from "@/components/EventGallery";
import { ReportButton } from "@/components/ReportButton";

export const Route = createFileRoute("/events/$id")({
  head: () => ({
    meta: [
      { title: "Event — Evently" },
      { name: "description", content: "View event details on Evently." },
    ],
  }),
  component: EventDetailPage,
});

type EventRow = {
  id: string;
  host_id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  timezone: string;
  venue_address: string | null;
  online_link: string | null;
  capacity: number;
  cover_image_url: string | null;
  status: string;
  visibility: string;
};

type HostRow = { id: string; name: string; slug: string; logo_url: string | null };

type RsvpRow = { id: string; status: string; waitlist_position: number | null };
type TicketRow = { id: string; ticket_code: string };

function EventDetailPage() {
  const { id } = Route.useParams();
  const { user, profile } = useAuth();
  const navigate = useNavigate();

  const [event, setEvent] = useState<EventRow | null>(null);
  const [host, setHost] = useState<HostRow | null>(null);
  const [isHostMember, setIsHostMember] = useState(false);
  const [loading, setLoading] = useState(true);

  const [confirmedCount, setConfirmedCount] = useState(0);
  const [myRsvp, setMyRsvp] = useState<RsvpRow | null>(null);
  const [myTicket, setMyTicket] = useState<TicketRow | null>(null);
  const [acting, setActing] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    const { data: ev } = await supabase
      .from("events")
      .select("*")
      .eq("id", id)
      .is("deleted_at", null)
      .maybeSingle();
    const evt = (ev as EventRow) ?? null;
    setEvent(evt);

    if (evt) {
      const { data: h } = await supabase
        .from("hosts")
        .select("id, name, slug, logo_url")
        .eq("id", evt.host_id)
        .maybeSingle();
      setHost((h as HostRow) ?? null);

      const { count } = await supabase
        .from("rsvps")
        .select("id", { count: "exact", head: true })
        .eq("event_id", evt.id)
        .eq("status", "confirmed");
      setConfirmedCount(count ?? 0);

      if (user) {
        const { data: hm } = await supabase
          .from("host_members")
          .select("id")
          .eq("host_id", evt.host_id)
          .eq("user_id", user.id)
          .limit(1);
        setIsHostMember(!!(hm && hm.length > 0));

        const { data: r } = await supabase
          .from("rsvps")
          .select("id,status,waitlist_position")
          .eq("event_id", evt.id)
          .eq("user_id", user.id)
          .in("status", ["confirmed", "waitlist"])
          .order("created_at", { ascending: false })
          .limit(1)
          .maybeSingle();
        const rsvp = (r as RsvpRow) ?? null;
        setMyRsvp(rsvp);

        if (rsvp?.status === "confirmed") {
          const { data: t } = await supabase
            .from("tickets")
            .select("id,ticket_code")
            .eq("event_id", evt.id)
            .eq("user_id", user.id)
            .order("created_at", { ascending: false })
            .limit(1)
            .maybeSingle();
          setMyTicket((t as TicketRow) ?? null);
        } else {
          setMyTicket(null);
        }
      } else {
        setIsHostMember(false);
        setMyRsvp(null);
        setMyTicket(null);
      }
    }
    setLoading(false);
  }, [id, user?.id]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleRsvp = async () => {
    if (!user || !event) return;
    setActing(true);
    try {
      const { data: rsvp, error: rsvpErr } = await supabase
        .from("rsvps")
        .insert({ event_id: event.id, user_id: user.id, status: "confirmed" })
        .select("id")
        .single();
      if (rsvpErr) throw rsvpErr;

      const { error: tErr } = await supabase
        .from("tickets")
        .insert({ event_id: event.id, user_id: user.id, rsvp_id: rsvp.id });
      if (tErr) throw tErr;

      toast.success("You're going! Check your ticket below.");
      await loadAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not RSVP");
    } finally {
      setActing(false);
    }
  };

  const handleJoinWaitlist = async () => {
    if (!user || !event) return;
    setActing(true);
    try {
      const { data: maxRow } = await supabase
        .from("rsvps")
        .select("waitlist_position")
        .eq("event_id", event.id)
        .eq("status", "waitlist")
        .order("waitlist_position", { ascending: false })
        .limit(1)
        .maybeSingle();
      const nextPos = ((maxRow?.waitlist_position as number | null) ?? 0) + 1;

      const { error } = await supabase.from("rsvps").insert({
        event_id: event.id,
        user_id: user.id,
        status: "waitlist",
        waitlist_position: nextPos,
      });
      if (error) throw error;

      toast.success("You've joined the waitlist. We'll notify you if a spot opens.");
      await loadAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not join waitlist");
    } finally {
      setActing(false);
    }
  };

  const handleCancel = async () => {
    if (!user || !event || !myRsvp) return;
    setActing(true);
    try {
      const wasConfirmed = myRsvp.status === "confirmed";
      const { error } = await supabase
        .from("rsvps")
        .update({ status: "cancelled", waitlist_position: null })
        .eq("id", myRsvp.id);
      if (error) throw error;

      // Promote next waitlister if a confirmed seat freed up
      if (wasConfirmed) {
        const { data: next } = await supabase
          .from("rsvps")
          .select("id,user_id,waitlist_position")
          .eq("event_id", event.id)
          .eq("status", "waitlist")
          .order("waitlist_position", { ascending: true })
          .limit(1)
          .maybeSingle();

        if (next) {
          const promoted = next as { id: string; user_id: string };
          await supabase
            .from("rsvps")
            .update({ status: "confirmed", waitlist_position: null })
            .eq("id", promoted.id);
          await supabase
            .from("tickets")
            .insert({ event_id: event.id, user_id: promoted.user_id, rsvp_id: promoted.id });
          // notifications has no INSERT policy from clients; skip silently if it fails.
          await supabase
            .from("notifications")
            .insert({
              user_id: promoted.user_id,
              type: "waitlist_promoted",
              payload: { event_id: event.id, event_title: event.title },
            } as never);
        }
      }

      toast.success("Your RSVP has been cancelled.");
      await loadAll();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not cancel RSVP");
    } finally {
      setActing(false);
    }
  };

  if (loading) return null;

  if (!event || (event.status !== "published" && !isHostMember)) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <h1 className="text-7xl font-bold">404</h1>
        <p className="mt-4 text-muted-foreground">Event not found.</p>
        <Button asChild className="mt-6">
          <Link to="/">Go home</Link>
        </Button>
      </div>
    );
  }

  const isPast = new Date(event.end_at).getTime() < Date.now();
  const isFull = confirmedCount >= event.capacity;
  const start = new Date(event.start_at);
  const end = new Date(event.end_at);
  const dateFmt = new Intl.DateTimeFormat(undefined, {
    timeZone: event.timezone,
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  const timeFmt = new Intl.DateTimeFormat(undefined, {
    timeZone: event.timezone,
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });

  const title = `${event.title} — Evently`;
  const description = (event.description ?? "").slice(0, 160) || `${event.title} on Evently.`;

  const renderRsvpAction = () => {
    if (isPast) return null;
    if (!user) {
      return (
        <Button
          size="lg"
          onClick={() =>
            navigate({ to: "/sign-in", search: { returnTo: `/events/${event.id}` } })
          }
        >
          RSVP
        </Button>
      );
    }
    if (myRsvp?.status === "confirmed") {
      return (
        <Button size="lg" variant="outline" onClick={handleCancel} disabled={acting}>
          Cancel RSVP
        </Button>
      );
    }
    if (myRsvp?.status === "waitlist") {
      return (
        <div className="flex flex-wrap items-center gap-3">
          <Button size="lg" disabled>
            You're on the waitlist
            {myRsvp.waitlist_position ? ` (#${myRsvp.waitlist_position})` : ""}
          </Button>
          <Button variant="ghost" onClick={handleCancel} disabled={acting}>
            Leave waitlist
          </Button>
        </div>
      );
    }
    if (isFull) {
      return (
        <Button size="lg" onClick={handleJoinWaitlist} disabled={acting}>
          Join Waitlist
        </Button>
      );
    }
    return (
      <Button size="lg" onClick={handleRsvp} disabled={acting}>
        RSVP
      </Button>
    );
  };

  return (
    <>
      <Helmet>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta property="og:title" content={event.title} />
        <meta property="og:description" content={description} />
        <meta property="og:type" content="event" />
        {event.cover_image_url && <meta property="og:image" content={event.cover_image_url} />}
        <meta name="twitter:card" content="summary_large_image" />
        {event.cover_image_url && <meta name="twitter:image" content={event.cover_image_url} />}
      </Helmet>

      <article className="mx-auto max-w-3xl px-4 py-10">
        {event.cover_image_url ? (
          <img
            src={event.cover_image_url}
            alt=""
            className="aspect-video w-full rounded-2xl border border-border object-cover"
          />
        ) : (
          <div className="flex aspect-video w-full items-center justify-center rounded-2xl border border-border bg-muted">
            <Calendar className="h-12 w-12 text-muted-foreground" />
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-2">
          {event.status === "draft" && <Badge variant="secondary">Draft</Badge>}
          {event.visibility === "unlisted" && <Badge variant="outline">Unlisted</Badge>}
          {isPast && <Badge variant="destructive">Ended</Badge>}
        </div>

        <h1 className="mt-3 text-4xl font-semibold tracking-tight">{event.title}</h1>

        {host && (
          <div className="mt-4 flex items-center gap-3">
            {host.logo_url ? (
              <img src={host.logo_url} alt="" className="h-10 w-10 rounded-lg border border-border object-cover" />
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-primary-foreground">
                {host.name.slice(0, 2).toUpperCase()}
              </div>
            )}
            <div className="text-sm">
              <p className="text-muted-foreground">Hosted by</p>
              <Link to="/hosts/$slug" params={{ slug: host.slug }} className="font-medium hover:underline">
                {host.name}
              </Link>
            </div>
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-3 rounded-2xl border border-border bg-card p-5 sm:grid-cols-2">
          <div className="flex items-start gap-3">
            <Calendar className="mt-0.5 h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{dateFmt.format(start)}</p>
              <p className="text-xs text-muted-foreground">
                {dateFmt.format(end) !== dateFmt.format(start) ? `→ ${dateFmt.format(end)}` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Clock className="mt-0.5 h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">
                {timeFmt.format(start)} → {timeFmt.format(end)}
              </p>
              <p className="text-xs text-muted-foreground">{event.timezone}</p>
            </div>
          </div>
          {event.venue_address && (
            <div className="flex items-start gap-3">
              <MapPin className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <p className="text-sm">{event.venue_address}</p>
            </div>
          )}
          {event.online_link && (
            <div className="flex items-start gap-3">
              <LinkIcon className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <a
                href={event.online_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline"
              >
                Online link
              </a>
            </div>
          )}
          <div className="flex items-start gap-3">
            <Users className="mt-0.5 h-5 w-5 text-muted-foreground" />
            <p className="text-sm">
              {confirmedCount} / {event.capacity} going
            </p>
          </div>
        </div>

        {event.description && (
          <div className="prose prose-neutral mt-8 max-w-none whitespace-pre-wrap text-foreground">
            {event.description}
          </div>
        )}

        <div className="mt-10">
          {isPast ? (
            <p className="text-sm text-muted-foreground">This event has ended.</p>
          ) : (
            renderRsvpAction()
          )}
        </div>

        {myTicket && (
          <div className="mt-8">
            <TicketCard
              event={event}
              ticketCode={myTicket.ticket_code}
              attendeeName={profile?.display_name ?? user?.email ?? "Attendee"}
            />
          </div>
        )}

        <EventGallery eventId={event.id} canUpload={!!user && myRsvp?.status === "confirmed"} />

        {isPast && (
          <FeedbackSection eventId={event.id} canSubmit={!!user && myRsvp?.status === "confirmed"} />
        )}

        <div className="mt-10 flex justify-end border-t border-border pt-4">
          <ReportButton targetType="event" targetId={event.id} />
        </div>
      </article>
    </>
  );
}
