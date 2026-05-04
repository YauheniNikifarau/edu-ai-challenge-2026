import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Ticket } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { TicketCard, type TicketCardEvent } from "@/components/TicketCard";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/my-tickets")({
  head: () => ({
    meta: [
      { title: "My Tickets — Evently" },
      { name: "description", content: "View your event tickets and check-in codes." },
    ],
  }),
  component: MyTicketsPage,
});

type Row = {
  id: string;
  ticket_code: string;
  event_id: string;
  rsvp_id: string;
  events: TicketCardEvent & { end_at: string };
  rsvps: { status: string } | null;
};

function MyTicketsPage() {
  const { user, profile, loading } = useAuth();
  const [tickets, setTickets] = useState<Row[]>([]);
  const [busy, setBusy] = useState(true);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      setBusy(true);
      const nowIso = new Date().toISOString();
      const { data } = await supabase
        .from("tickets")
        .select(
          "id,ticket_code,event_id,rsvp_id,events!inner(id,title,description,start_at,end_at,timezone,venue_address,online_link),rsvps!inner(status)",
        )
        .eq("user_id", user.id)
        .eq("rsvps.status", "confirmed")
        .gt("events.end_at", nowIso)
        .order("created_at", { ascending: true });
      if (cancelled) return;
      setTickets(((data as unknown) as Row[]) ?? []);
      setBusy(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  if (loading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/my-tickets" }} />;

  const attendeeName = profile?.display_name ?? user.email ?? "Attendee";

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">My Tickets</h1>
      <p className="mt-2 text-muted-foreground">Tickets for upcoming events you're attending.</p>

      {busy ? (
        <div className="mt-10 h-40 animate-pulse rounded-2xl border border-border bg-card" />
      ) : tickets.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center">
          <Ticket className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">You don't have any tickets yet.</p>
          <Button asChild className="mt-6">
            <Link to="/">Explore events</Link>
          </Button>
        </div>
      ) : (
        <div className="mt-8 space-y-6">
          {tickets.map((t) => (
            <TicketCard
              key={t.id}
              event={t.events}
              ticketCode={t.ticket_code}
              attendeeName={attendeeName}
            />
          ))}
        </div>
      )}
    </div>
  );
}
