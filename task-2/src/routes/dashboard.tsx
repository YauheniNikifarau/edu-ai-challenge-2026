import { createFileRoute, Link, Navigate, Outlet, useMatches } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useMyHost } from "@/lib/use-my-host";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  ExternalLink,
  Pencil,
  Calendar,
  Plus,
  QrCode,
  Copy,
  Eye,
  EyeOff,
  Download,
  Check,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { exportEventCsv } from "@/lib/event-csv";
import { TeamSection } from "@/components/TeamSection";
import { ReportsSection } from "@/components/ReportsSection";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Host Dashboard — Evently" },
      { name: "description", content: "Manage your host profile and events on Evently." },
    ],
  }),
  component: DashboardPage,
});

type EventRow = {
  id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  timezone: string;
  status: string;
  visibility: string;
  pricing_type: string;
  cover_image_url: string | null;
  venue_address: string | null;
  online_link: string | null;
  capacity: number;
};

type Stats = { going: number; waitlist: number; checkedIn: number };

function DashboardPage() {
  const { user, loading } = useAuth();
  const { host, loading: hostLoading } = useMyHost();
  const matches = useMatches();
  const isChild = matches.some(
    (m) => m.routeId !== "/dashboard" && m.routeId.startsWith("/dashboard/"),
  );

  const [events, setEvents] = useState<EventRow[]>([]);
  const [stats, setStats] = useState<Record<string, Stats>>({});
  const [busy, setBusy] = useState<string | null>(null);

  const loadEvents = useCallback(async () => {
    if (!host) return;
    const { data } = await supabase
      .from("events")
      .select(
        "id,title,description,start_at,end_at,timezone,status,visibility,pricing_type,cover_image_url,venue_address,online_link,capacity",
      )
      .eq("host_id", host.id)
      .is("deleted_at", null)
      .order("start_at", { ascending: false });
    const list = (data as EventRow[]) ?? [];
    setEvents(list);

    const entries = await Promise.all(
      list.map(async (e) => {
        const [going, waitlist, checkedIn] = await Promise.all([
          supabase.from("rsvps").select("id", { count: "exact", head: true }).eq("event_id", e.id).eq("status", "confirmed"),
          supabase.from("rsvps").select("id", { count: "exact", head: true }).eq("event_id", e.id).eq("status", "waitlist"),
          supabase.from("check_ins").select("id", { count: "exact", head: true }).eq("event_id", e.id).eq("undone", false),
        ]);
        return [e.id, { going: going.count ?? 0, waitlist: waitlist.count ?? 0, checkedIn: checkedIn.count ?? 0 }] as const;
      }),
    );
    setStats(Object.fromEntries(entries));
  }, [host]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  if (loading || hostLoading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/dashboard" }} />;
  if (!host) return <Navigate to="/become-a-host" />;
  if (isChild) return <Outlet />;

  const now = Date.now();
  const upcoming = events.filter((e) => new Date(e.end_at).getTime() >= now).sort(
    (a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
  );
  const past = events.filter((e) => new Date(e.end_at).getTime() < now);

  const togglePublish = async (e: EventRow) => {
    setBusy(e.id);
    const next = e.status === "published" ? "draft" : "published";
    const { error } = await supabase.from("events").update({ status: next }).eq("id", e.id);
    setBusy(null);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success(next === "published" ? "Event published." : "Event unpublished.");
    void loadEvents();
  };

  const duplicate = async (e: EventRow) => {
    setBusy(e.id);
    const { error } = await supabase.from("events").insert({
      host_id: host.id,
      title: `${e.title} (copy)`,
      description: e.description,
      start_at: e.start_at,
      end_at: e.end_at,
      timezone: e.timezone,
      status: "draft",
      visibility: e.visibility,
      pricing_type: e.pricing_type,
      cover_image_url: e.cover_image_url,
      venue_address: e.venue_address,
      online_link: e.online_link,
      capacity: e.capacity,
    });
    setBusy(null);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Event duplicated as draft.");
    void loadEvents();
  };

  const handleExport = async (e: EventRow) => {
    setBusy(e.id);
    try {
      await exportEventCsv(e.id, e.title);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  const renderEvent = (e: EventRow, opts: { showGallery?: boolean } = {}) => {
    const s = stats[e.id] ?? { going: 0, waitlist: 0, checkedIn: 0 };
    return (
      <Card key={e.id} className="overflow-hidden">
        <div className="flex flex-col gap-4 p-4 sm:flex-row">
          <div className="h-24 w-full shrink-0 overflow-hidden rounded-lg bg-muted sm:h-20 sm:w-32">
            {e.cover_image_url ? (
              <img src={e.cover_image_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <Calendar className="h-5 w-5 text-muted-foreground" />
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="truncate font-medium">{e.title}</p>
              <Badge variant={e.status === "published" ? "default" : "secondary"}>
                {e.status === "published" ? "Published" : "Draft"}
              </Badge>
              {new Date(e.end_at).getTime() < now && <Badge variant="destructive">Ended</Badge>}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {new Date(e.start_at).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span>
                <strong className="text-foreground tabular-nums">{s.going}</strong> Going
              </span>
              <span>
                <strong className="text-foreground tabular-nums">{s.waitlist}</strong> Waitlist
              </span>
              <span>
                <strong className="text-foreground tabular-nums">{s.checkedIn}</strong> Checked-in
              </span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button asChild size="sm" variant="outline">
                <Link to="/dashboard/events/$id/edit" params={{ id: e.id }}>
                  <Pencil className="h-4 w-4" /> Edit
                </Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link to="/dashboard/events/$id/checkin" params={{ id: e.id }}>
                  <QrCode className="h-4 w-4" /> Check-in
                </Link>
              </Button>
              <Button size="sm" variant="outline" disabled={busy === e.id} onClick={() => duplicate(e)}>
                <Copy className="h-4 w-4" /> Duplicate
              </Button>
              <Button size="sm" variant="outline" disabled={busy === e.id} onClick={() => togglePublish(e)}>
                {e.status === "published" ? (
                  <>
                    <EyeOff className="h-4 w-4" /> Unpublish
                  </>
                ) : (
                  <>
                    <Eye className="h-4 w-4" /> Publish
                  </>
                )}
              </Button>
              <Button size="sm" variant="outline" disabled={busy === e.id} onClick={() => handleExport(e)}>
                <Download className="h-4 w-4" /> Export CSV
              </Button>
            </div>
          </div>
        </div>
        {opts.showGallery && <GalleryModeration eventId={e.id} />}
      </Card>
    );
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          {host.logo_url ? (
            <img src={host.logo_url} alt="" className="h-16 w-16 rounded-xl border border-border object-cover" />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-primary text-xl font-semibold text-primary-foreground">
              {host.name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">{host.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">/hosts/{host.slug}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/hosts/$slug" params={{ slug: host.slug }}>
              <ExternalLink className="h-4 w-4" /> View public page
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link to="/dashboard/profile">
              <Pencil className="h-4 w-4" /> Edit profile
            </Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/dashboard/events/new">
              <Plus className="h-4 w-4" /> New event
            </Link>
          </Button>
        </div>
      </div>

      <section className="mt-12">
        <h2 className="text-xl font-semibold">Upcoming Events</h2>
        {upcoming.length === 0 ? (
          <div className="mt-4 rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center text-sm text-muted-foreground">
            No upcoming events.
          </div>
        ) : (
          <div className="mt-4 space-y-3">{upcoming.map((e) => renderEvent(e))}</div>
        )}
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-semibold">Past Events</h2>
        {past.length === 0 ? (
          <div className="mt-4 rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center text-sm text-muted-foreground">
            No past events yet.
          </div>
        ) : (
          <div className="mt-4 space-y-3">{past.map((e) => renderEvent(e, { showGallery: true }))}</div>
        )}
      </section>

      <TeamSection hostId={host.id} />
      <ReportsSection hostId={host.id} />
    </div>
  );
}

type PendingPhoto = {
  id: string;
  storage_path: string;
  status: string;
};

function GalleryModeration({ eventId }: { eventId: string }) {
  const [photos, setPhotos] = useState<PendingPhoto[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const { data } = await supabase
      .from("gallery_photos")
      .select("id,storage_path,status")
      .eq("event_id", eventId)
      .eq("status", "pending")
      .order("created_at", { ascending: false });
    setPhotos((data as PendingPhoto[]) ?? []);
    setLoading(false);
  }, [eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  const moderate = async (id: string, status: "approved" | "rejected") => {
    const { error } = await supabase.from("gallery_photos").update({ status }).eq("id", id);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success(status === "approved" ? "Photo approved." : "Photo rejected.");
    void load();
  };

  if (loading) return null;
  if (photos.length === 0) return null;

  return (
    <div className="border-t border-border bg-muted/30 p-4">
      <p className="mb-3 text-xs font-medium text-muted-foreground">
        Gallery — {photos.length} pending
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {photos.map((p) => {
          const url = supabase.storage.from("event-assets").getPublicUrl(p.storage_path).data.publicUrl;
          return (
            <div key={p.id} className="overflow-hidden rounded-lg border border-border bg-card">
              <div className="aspect-square w-full overflow-hidden bg-muted">
                <img src={url} alt="" className="h-full w-full object-cover" />
              </div>
              <div className="flex gap-1 p-2">
                <Button size="sm" variant="outline" className="flex-1" onClick={() => moderate(p.id, "approved")}>
                  <Check className="h-3 w-3" /> Approve
                </Button>
                <Button size="sm" variant="outline" className="flex-1" onClick={() => moderate(p.id, "rejected")}>
                  <X className="h-3 w-3" /> Reject
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
