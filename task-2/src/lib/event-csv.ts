import { supabase } from "@/integrations/supabase/client";
import { getEventAttendeeEmails } from "@/server/attendees.functions";

function escape(v: string | null | undefined) {
  const s = (v ?? "").toString();
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function slugify(s: string) {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || "event";
}

export async function exportEventCsv(eventId: string, eventTitle: string) {
  const { data: rsvps } = await supabase
    .from("rsvps")
    .select("id,user_id,status")
    .eq("event_id", eventId);

  const rsvpRows = (rsvps ?? []) as { id: string; user_id: string; status: string }[];
  const userIds = Array.from(new Set(rsvpRows.map((r) => r.user_id)));

  const [{ data: profiles }, { data: tickets }, { data: checkIns }] = await Promise.all([
    userIds.length
      ? supabase.from("profiles").select("id,display_name").in("id", userIds)
      : Promise.resolve({ data: [] as { id: string; display_name: string | null }[] }),
    supabase.from("tickets").select("id,rsvp_id").eq("event_id", eventId),
    supabase.from("check_ins").select("ticket_id,checked_in_at,undone").eq("event_id", eventId).eq("undone", false),
  ]);

  const profileMap = new Map<string, string>();
  for (const p of (profiles ?? []) as { id: string; display_name: string | null }[]) {
    profileMap.set(p.id, p.display_name ?? "");
  }
  const ticketByRsvp = new Map<string, string>();
  for (const t of (tickets ?? []) as { id: string; rsvp_id: string }[]) {
    ticketByRsvp.set(t.rsvp_id, t.id);
  }
  const checkinByTicket = new Map<string, string>();
  for (const c of (checkIns ?? []) as { ticket_id: string; checked_in_at: string }[]) {
    checkinByTicket.set(c.ticket_id, c.checked_in_at);
  }

  let emailMap: Record<string, string> = {};
  try {
    const res = await getEventAttendeeEmails({ data: { eventId } });
    emailMap = res.emails ?? {};
  } catch {
    // ignore — leave emails blank if unauthorized
  }

  const header = ["Name", "Email", "RSVP Status", "Check-in Time"];
  const lines = [header.join(",")];
  for (const r of rsvpRows) {
    const name = profileMap.get(r.user_id) ?? "";
    const email = emailMap[r.user_id] ?? "";
    const ticketId = ticketByRsvp.get(r.id);
    const checkInTime = ticketId ? checkinByTicket.get(ticketId) ?? "" : "";
    lines.push([escape(name), escape(email), escape(r.status), escape(checkInTime)].join(","));
  }

  const csv = "\uFEFF" + lines.join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${slugify(eventTitle)}-attendees.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
