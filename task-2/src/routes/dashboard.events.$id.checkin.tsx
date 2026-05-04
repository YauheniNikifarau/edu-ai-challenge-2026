import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Calendar, CheckCircle2, Users, Clock } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboard/events/$id/checkin")({
  head: () => ({ meta: [{ title: "Check In — Evently" }] }),
  component: CheckinPage,
});

type EventRow = {
  id: string;
  host_id: string;
  title: string;
  start_at: string;
  timezone: string;
};

const ticketSchema = z.string().trim().uuid({ message: "Enter a valid ticket code." });

function CheckinPage() {
  const { id } = Route.useParams();
  const { user } = useAuth();

  const [event, setEvent] = useState<EventRow | null>(null);
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  const [checkedIn, setCheckedIn] = useState(0);
  const [confirmed, setConfirmed] = useState(0);
  const [waitlisted, setWaitlisted] = useState(0);

  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const sessionCheckIns = useRef<string[]>([]);
  const [hasSessionCheckIn, setHasSessionCheckIn] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refreshCounters = useCallback(async (eventId: string) => {
    const [ci, conf, wait] = await Promise.all([
      supabase
        .from("check_ins")
        .select("id", { count: "exact", head: true })
        .eq("event_id", eventId)
        .eq("undone", false),
      supabase
        .from("rsvps")
        .select("id", { count: "exact", head: true })
        .eq("event_id", eventId)
        .eq("status", "confirmed"),
      supabase
        .from("rsvps")
        .select("id", { count: "exact", head: true })
        .eq("event_id", eventId)
        .eq("status", "waitlist"),
    ]);
    setCheckedIn(ci.count ?? 0);
    setConfirmed(conf.count ?? 0);
    setWaitlisted(wait.count ?? 0);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const { data: ev } = await supabase
        .from("events")
        .select("id,host_id,title,start_at,timezone")
        .eq("id", id)
        .maybeSingle();
      if (cancelled) return;
      const evt = (ev as EventRow) ?? null;
      setEvent(evt);

      if (evt && user) {
        const { data: hm } = await supabase
          .from("host_members")
          .select("role")
          .eq("host_id", evt.host_id)
          .eq("user_id", user.id);
        const roles = (hm ?? []).map((r) => (r as { role: string }).role);
        setAllowed(roles.includes("host") || roles.includes("checker"));
        await refreshCounters(evt.id);
      } else {
        setAllowed(false);
      }
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [id, user?.id, refreshCounters]);

  useEffect(() => {
    if (!event || !allowed) return;
    const channel = supabase
      .channel(`checkins:${event.id}`)
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "check_ins", filter: `event_id=eq.${event.id}` },
        () => {
          void refreshCounters(event.id);
        },
      )
      .subscribe();
    return () => {
      void supabase.removeChannel(channel);
    };
  }, [event?.id, allowed, refreshCounters]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!event || !user || submitting) return;

    const parsed = ticketSchema.safeParse(code);
    if (!parsed.success) {
      toast.error(parsed.error.issues[0]?.message ?? "Invalid code.");
      return;
    }
    const ticketCode = parsed.data;

    setSubmitting(true);
    try {
      const { data: ticket } = await supabase
        .from("tickets")
        .select("id,user_id")
        .eq("event_id", event.id)
        .eq("ticket_code", ticketCode)
        .maybeSingle();

      if (!ticket) {
        toast.error("Ticket not found.");
        return;
      }
      const t = ticket as { id: string; user_id: string };

      const { data: existing } = await supabase
        .from("check_ins")
        .select("id")
        .eq("ticket_id", t.id)
        .eq("undone", false)
        .limit(1);

      if (existing && existing.length > 0) {
        toast.error("Already checked in.");
        return;
      }

      const { data: inserted, error: insErr } = await supabase
        .from("check_ins")
        .insert({
          ticket_id: t.id,
          event_id: event.id,
          checked_in_by: user.id,
        })
        .select("id")
        .single();
      if (insErr) throw insErr;

      sessionCheckIns.current.push((inserted as { id: string }).id);
      setHasSessionCheckIn(true);

      const { data: profile } = await supabase
        .from("profiles")
        .select("display_name")
        .eq("id", t.user_id)
        .maybeSingle();
      const name = (profile as { display_name: string | null } | null)?.display_name ?? "Attendee";

      toast.success(`${name} ✓ Checked in`);
      setCode("");
      inputRef.current?.focus();
      await refreshCounters(event.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not check in.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUndo = async () => {
    if (!event) return;
    const lastId = sessionCheckIns.current[sessionCheckIns.current.length - 1];
    if (!lastId) return;
    const { error } = await supabase
      .from("check_ins")
      .update({ undone: true })
      .eq("id", lastId);
    if (error) {
      toast.error(error.message);
      return;
    }
    sessionCheckIns.current.pop();
    setHasSessionCheckIn(sessionCheckIns.current.length > 0);
    toast.success("Check-in undone.");
    await refreshCounters(event.id);
  };

  if (loading) return null;

  if (!event) {
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

  if (!allowed) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <h1 className="text-3xl font-semibold">403 — Access denied</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          You don't have permission to check in attendees for this event.
        </p>
        <Button asChild variant="outline" className="mt-6">
          <Link to="/dashboard">Back to dashboard</Link>
        </Button>
      </div>
    );
  }

  const dateFmt = new Intl.DateTimeFormat(undefined, {
    timeZone: event.timezone,
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">{event.title}</h1>
        <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          {dateFmt.format(new Date(event.start_at))}
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3">
        <Card className="p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <CheckCircle2 className="h-4 w-4" />
            Checked in
          </div>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {checkedIn} <span className="text-base text-muted-foreground">/ {confirmed}</span>
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Users className="h-4 w-4" />
            Waitlist
          </div>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{waitlisted}</p>
        </Card>
      </div>

      <Card className="p-5">
        <form onSubmit={handleSubmit} className="space-y-3">
          <label htmlFor="code" className="text-sm font-medium">
            Ticket code
          </label>
          <Input
            id="code"
            ref={inputRef}
            placeholder="Paste or type ticket code (UUID)"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoFocus
            autoComplete="off"
            spellCheck={false}
            maxLength={64}
          />
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button type="submit" disabled={submitting || !code.trim()}>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Check In
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleUndo}
              disabled={!hasSessionCheckIn}
            >
              <Clock className="mr-2 h-4 w-4" />
              Undo last check-in
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
