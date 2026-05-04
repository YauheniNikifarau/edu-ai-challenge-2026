import QRCode from "react-qr-code";
import { Button } from "@/components/ui/button";
import { Calendar, Download } from "lucide-react";

export type TicketCardEvent = {
  id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  timezone: string;
  venue_address: string | null;
  online_link: string | null;
};

export type TicketCardProps = {
  event: TicketCardEvent;
  ticketCode: string;
  attendeeName: string;
};

function toGcalDate(iso: string) {
  // YYYYMMDDTHHMMSSZ
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    d.getUTCFullYear().toString() +
    pad(d.getUTCMonth() + 1) +
    pad(d.getUTCDate()) +
    "T" +
    pad(d.getUTCHours()) +
    pad(d.getUTCMinutes()) +
    pad(d.getUTCSeconds()) +
    "Z"
  );
}

function buildGoogleCalendarUrl(event: TicketCardEvent) {
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: event.title,
    dates: `${toGcalDate(event.start_at)}/${toGcalDate(event.end_at)}`,
    details: event.description ?? "",
    location: event.venue_address ?? event.online_link ?? "",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function escapeIcs(text: string) {
  return text.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/,/g, "\\,").replace(/;/g, "\\;");
}

function buildIcs(event: TicketCardEvent) {
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Evently//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:${event.id}@evently`,
    `DTSTAMP:${toGcalDate(new Date().toISOString())}`,
    `DTSTART:${toGcalDate(event.start_at)}`,
    `DTEND:${toGcalDate(event.end_at)}`,
    `SUMMARY:${escapeIcs(event.title)}`,
    `DESCRIPTION:${escapeIcs(event.description ?? "")}`,
    `LOCATION:${escapeIcs(event.venue_address ?? event.online_link ?? "")}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ];
  return lines.join("\r\n");
}

function downloadIcs(event: TicketCardEvent) {
  const blob = new Blob([buildIcs(event)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${event.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function TicketCard({ event, ticketCode, attendeeName }: TicketCardProps) {
  const dateFmt = new Intl.DateTimeFormat(undefined, {
    timeZone: event.timezone,
    weekday: "short",
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="flex flex-col gap-6 sm:flex-row">
        <div className="flex-shrink-0 self-center rounded-xl bg-white p-3">
          <QRCode value={ticketCode} size={144} />
        </div>
        <div className="flex-1 space-y-2">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Your ticket</p>
          <h3 className="text-lg font-semibold leading-tight">{event.title}</h3>
          <p className="text-sm text-muted-foreground">{dateFmt.format(new Date(event.start_at))}</p>
          <p className="text-sm">
            <span className="text-muted-foreground">Attendee:</span>{" "}
            <span className="font-medium">{attendeeName}</span>
          </p>
          <p className="break-all rounded-md bg-muted px-2 py-1 font-mono text-xs">{ticketCode}</p>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Button asChild variant="outline" size="sm">
          <a href={buildGoogleCalendarUrl(event)} target="_blank" rel="noopener noreferrer">
            <Calendar /> Add to Google Calendar
          </a>
        </Button>
        <Button variant="outline" size="sm" onClick={() => downloadIcs(event)}>
          <Download /> Download .ics
        </Button>
      </div>
    </div>
  );
}
