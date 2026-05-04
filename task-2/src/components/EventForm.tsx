import { useEffect, useMemo, useState, type FormEvent } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";
import { getTimezones, getDefaultTimezone } from "@/lib/timezones";

export type EventFormValues = {
  title: string;
  description: string;
  start_local: string; // datetime-local
  end_local: string; // datetime-local
  timezone: string;
  venue_address: string;
  online_link: string;
  capacity: number;
  cover_image_url: string | null;
  visibility: "public" | "unlisted";
  pricing_type: "free" | "paid";
};

export type EventFormProps = {
  hostId: string;
  initial?: Partial<EventFormValues> & { id?: string };
  submitLabel?: string;
  onSaved: (eventId: string) => void;
};

// Convert a "YYYY-MM-DDTHH:mm" wall-clock time in a given IANA tz to a UTC ISO string.
function localWallToUTC(localStr: string, tz: string): string {
  // localStr like "2026-05-04T18:30"
  const [datePart, timePart = "00:00"] = localStr.split("T");
  const [y, m, d] = datePart.split("-").map(Number);
  const [hh, mm] = timePart.split(":").map(Number);
  // Construct a UTC instant for the same wall clock, then adjust by the tz offset.
  const utcGuess = Date.UTC(y, (m ?? 1) - 1, d ?? 1, hh ?? 0, mm ?? 0, 0);
  // Find what wall clock that instant looks like in the target tz.
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(new Date(utcGuess));
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0);
  const asTz = Date.UTC(
    get("year"),
    get("month") - 1,
    get("day"),
    get("hour") % 24,
    get("minute"),
    get("second"),
  );
  const offset = asTz - utcGuess;
  return new Date(utcGuess - offset).toISOString();
}

// Convert a UTC ISO string to a "YYYY-MM-DDTHH:mm" wall-clock string in the given tz.
function utcToLocalWall(iso: string, tz: string): string {
  const d = new Date(iso);
  const fmt = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

export function EventForm({ hostId, initial, submitLabel = "Save", onSaved }: EventFormProps) {
  const { user } = useAuth();
  const timezones = useMemo(() => getTimezones(), []);

  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [timezone, setTimezone] = useState(initial?.timezone ?? getDefaultTimezone());
  const [startLocal, setStartLocal] = useState(initial?.start_local ?? "");
  const [endLocal, setEndLocal] = useState(initial?.end_local ?? "");
  const [venueAddress, setVenueAddress] = useState(initial?.venue_address ?? "");
  const [onlineLink, setOnlineLink] = useState(initial?.online_link ?? "");
  const [capacity, setCapacity] = useState<number>(initial?.capacity ?? 50);
  const [visibility, setVisibility] = useState<"public" | "unlisted">(
    initial?.visibility ?? "public",
  );
  const [coverUrl, setCoverUrl] = useState<string | null>(initial?.cover_image_url ?? null);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initial) {
      if (initial.title !== undefined) setTitle(initial.title);
      if (initial.description !== undefined) setDescription(initial.description);
      if (initial.timezone) setTimezone(initial.timezone);
      if (initial.start_local !== undefined) setStartLocal(initial.start_local);
      if (initial.end_local !== undefined) setEndLocal(initial.end_local);
      if (initial.venue_address !== undefined) setVenueAddress(initial.venue_address);
      if (initial.online_link !== undefined) setOnlineLink(initial.online_link);
      if (initial.capacity !== undefined) setCapacity(initial.capacity);
      if (initial.visibility) setVisibility(initial.visibility);
      if (initial.cover_image_url !== undefined) setCoverUrl(initial.cover_image_url);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial?.id]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (!title.trim()) return toast.error("Title is required");
    if (!startLocal || !endLocal) return toast.error("Start and end times are required");
    if (capacity < 1) return toast.error("Capacity must be at least 1");

    const startUtc = localWallToUTC(startLocal, timezone);
    const endUtc = localWallToUTC(endLocal, timezone);
    if (new Date(endUtc).getTime() <= new Date(startUtc).getTime()) {
      return toast.error("End time must be after start time");
    }
    if (!venueAddress.trim() && !onlineLink.trim()) {
      return toast.error("Provide a venue address or an online link");
    }

    setSubmitting(true);
    try {
      let finalCoverUrl = coverUrl;
      if (coverFile) {
        const ext = coverFile.name.split(".").pop() || "jpg";
        const path = `${user.id}/${crypto.randomUUID()}.${ext}`;
        const { error: upErr } = await supabase.storage
          .from("event-assets")
          .upload(path, coverFile, { contentType: coverFile.type });
        if (upErr) throw upErr;
        finalCoverUrl = supabase.storage.from("event-assets").getPublicUrl(path).data.publicUrl;
      }

      const payload = {
        host_id: hostId,
        title: title.trim(),
        description: description.trim() || null,
        start_at: startUtc,
        end_at: endUtc,
        timezone,
        venue_address: venueAddress.trim() || null,
        online_link: onlineLink.trim() || null,
        capacity,
        visibility,
        pricing_type: "free",
        cover_image_url: finalCoverUrl,
      };

      if (initial?.id) {
        const { error } = await supabase
          .from("events")
          .update(payload)
          .eq("id", initial.id);
        if (error) throw error;
        toast.success("Event updated");
        onSaved(initial.id);
      } else {
        const { data, error } = await supabase
          .from("events")
          .insert({ ...payload, status: "draft" })
          .select("id")
          .single();
        if (error) throw error;
        toast.success("Event created");
        onSaved(data.id);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save event");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-5 rounded-2xl border border-border bg-card p-6 shadow-sm">
      <div className="space-y-2">
        <Label htmlFor="title">Title *</Label>
        <Input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          rows={6}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={5000}
        />
      </div>

      <div className="space-y-2">
        <Label>Timezone *</Label>
        <Select value={timezone} onValueChange={setTimezone}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="max-h-72">
            {timezones.map((tz) => (
              <SelectItem key={tz} value={tz}>
                {tz}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="start">Starts at *</Label>
          <Input
            id="start"
            type="datetime-local"
            required
            value={startLocal}
            onChange={(e) => setStartLocal(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="end">Ends at *</Label>
          <Input
            id="end"
            type="datetime-local"
            required
            value={endLocal}
            onChange={(e) => setEndLocal(e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="venue">Venue address</Label>
        <Input
          id="venue"
          placeholder="123 Main St, City"
          value={venueAddress}
          onChange={(e) => setVenueAddress(e.target.value)}
          maxLength={300}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="online">Online link</Label>
        <Input
          id="online"
          type="url"
          placeholder="https://..."
          value={onlineLink}
          onChange={(e) => setOnlineLink(e.target.value)}
          maxLength={500}
        />
        <p className="text-xs text-muted-foreground">Provide a venue address, an online link, or both.</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="capacity">Capacity *</Label>
        <Input
          id="capacity"
          type="number"
          required
          min={1}
          value={capacity}
          onChange={(e) => setCapacity(Math.max(1, Number(e.target.value) || 1))}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="cover">Cover image</Label>
        {coverUrl && (
          <img src={coverUrl} alt="" className="h-32 w-full rounded-lg border border-border object-cover" />
        )}
        <Input
          id="cover"
          type="file"
          accept="image/*"
          onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="space-y-2">
        <Label>Visibility</Label>
        <Select value={visibility} onValueChange={(v) => setVisibility(v as "public" | "unlisted")}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="public">Public</SelectItem>
            <SelectItem value="unlisted">Unlisted</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Pricing</Label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="default"
            size="sm"
            className="pointer-events-none"
            aria-pressed
          >
            Free
          </Button>
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  tabIndex={0}
                  className="inline-flex cursor-not-allowed"
                  aria-label="Paid (coming soon)"
                >
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    aria-disabled="true"
                    className="pointer-events-none opacity-50"
                  >
                    Paid
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>Coming soon</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <span className="ml-1 text-xs text-muted-foreground">Paid events coming soon</span>
        </div>
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}

export { utcToLocalWall };
