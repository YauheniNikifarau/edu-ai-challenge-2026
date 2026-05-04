import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { CalendarIcon, MapPin, Users } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type SearchParams = {
  q?: string;
  from?: string; // YYYY-MM-DD
  to?: string;
  loc?: string;
  includePast?: boolean;
};

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Explore Events — Evently" },
      { name: "description", content: "Discover community events near you on Evently." },
      { property: "og:title", content: "Explore Events — Evently" },
      { property: "og:description", content: "Discover community events near you on Evently." },
    ],
  }),
  validateSearch: (search: Record<string, unknown>): SearchParams => ({
    q: typeof search.q === "string" && search.q ? search.q : undefined,
    from: typeof search.from === "string" && search.from ? search.from : undefined,
    to: typeof search.to === "string" && search.to ? search.to : undefined,
    loc: typeof search.loc === "string" && search.loc ? search.loc : undefined,
    includePast:
      search.includePast === true || search.includePast === "true" ? true : undefined,
  }),
  component: ExplorePage,
});

type EventRow = {
  id: string;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  timezone: string;
  venue_address: string | null;
  online_link: string | null;
  capacity: number;
  cover_image_url: string | null;
  host_id: string;
  hosts: { name: string; slug: string } | null;
};

function formatInTz(iso: string, tz: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeZone: tz,
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return new Date(iso).toLocaleString();
  }
}

function ExplorePage() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/" });

  const [qInput, setQInput] = useState(search.q ?? "");
  const [locInput, setLocInput] = useState(search.loc ?? "");
  const [events, setEvents] = useState<EventRow[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  // Sync local inputs when URL changes externally
  useEffect(() => {
    setQInput(search.q ?? "");
  }, [search.q]);
  useEffect(() => {
    setLocInput(search.loc ?? "");
  }, [search.loc]);

  // Debounced text search
  useEffect(() => {
    const t = setTimeout(() => {
      if ((search.q ?? "") !== qInput) {
        navigate({
          search: (prev: SearchParams) => ({ ...prev, q: qInput.trim() || undefined }),
          replace: true,
        });
      }
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qInput]);

  useEffect(() => {
    const t = setTimeout(() => {
      if ((search.loc ?? "") !== locInput) {
        navigate({
          search: (prev: SearchParams) => ({ ...prev, loc: locInput.trim() || undefined }),
          replace: true,
        });
      }
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locInput]);

  const fromDate = useMemo(() => (search.from ? new Date(search.from + "T00:00:00") : undefined), [search.from]);
  const toDate = useMemo(() => (search.to ? new Date(search.to + "T00:00:00") : undefined), [search.to]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      let query = supabase
        .from("events")
        .select("id,title,description,start_at,end_at,timezone,venue_address,online_link,capacity,cover_image_url,host_id,hosts(name,slug)")
        .eq("status", "published")
        .eq("visibility", "public")
        .is("deleted_at", null)
        .order("start_at", { ascending: true })
        .limit(100);

      if (!search.includePast) {
        query = query.gt("end_at", new Date().toISOString());
      }
      if (search.q) {
        const safe = search.q.replace(/[%,]/g, " ");
        query = query.or(`title.ilike.%${safe}%,description.ilike.%${safe}%`);
      }
      if (search.loc) {
        const safe = search.loc.replace(/[%,]/g, " ");
        query = query.ilike("venue_address", `%${safe}%`);
      }
      if (search.from) {
        query = query.gte("start_at", new Date(search.from + "T00:00:00").toISOString());
      }
      if (search.to) {
        const end = new Date(search.to + "T00:00:00");
        end.setDate(end.getDate() + 1);
        query = query.lt("start_at", end.toISOString());
      }

      const { data, error } = await query;
      if (cancelled) return;
      if (error) {
        setEvents([]);
        setLoading(false);
        return;
      }
      const rows = (data as unknown as EventRow[]) ?? [];
      setEvents(rows);

      // Fetch RSVP counts
      const ids = rows.map((r) => r.id);
      if (ids.length) {
        const { data: rsvps } = await supabase
          .from("rsvps")
          .select("event_id,status")
          .in("event_id", ids)
          .eq("status", "confirmed");
        const c: Record<string, number> = {};
        (rsvps ?? []).forEach((r: { event_id: string }) => {
          c[r.event_id] = (c[r.event_id] ?? 0) + 1;
        });
        if (!cancelled) setCounts(c);
      } else {
        setCounts({});
      }
      setLoading(false);
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [search.q, search.loc, search.from, search.to, search.includePast]);

  const setFrom = (d?: Date) => {
    navigate({
      search: (prev: SearchParams) => ({ ...prev, from: d ? format(d, "yyyy-MM-dd") : undefined }),
      replace: true,
    });
  };
  const setTo = (d?: Date) => {
    navigate({
      search: (prev: SearchParams) => ({ ...prev, to: d ? format(d, "yyyy-MM-dd") : undefined }),
      replace: true,
    });
  };
  const toggleIncludePast = (v: boolean) => {
    navigate({
      search: (prev: SearchParams) => ({ ...prev, includePast: v ? true : undefined }),
      replace: true,
    });
  };
  const clearFilters = () => {
    setQInput("");
    setLocInput("");
    navigate({ search: {}, replace: true });
  };

  const hasFilters = !!(search.q || search.from || search.to || search.loc || search.includePast);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Explore events</h1>
        <p className="mt-2 text-muted-foreground">Discover what's happening in your community.</p>
      </header>

      <section className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="q">Search</Label>
            <Input
              id="q"
              placeholder="Search by title or description"
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="loc">Location</Label>
            <Input
              id="loc"
              placeholder="Filter by venue address"
              value={locInput}
              onChange={(e) => setLocInput(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>From</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("w-full justify-start text-left font-normal", !fromDate && "text-muted-foreground")}
                >
                  <CalendarIcon className="h-4 w-4" />
                  {fromDate ? format(fromDate, "PPP") : <span>Pick a start date</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={fromDate}
                  onSelect={setFrom}
                  initialFocus
                  className={cn("p-3 pointer-events-auto")}
                />
              </PopoverContent>
            </Popover>
          </div>
          <div className="space-y-2">
            <Label>To</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("w-full justify-start text-left font-normal", !toDate && "text-muted-foreground")}
                >
                  <CalendarIcon className="h-4 w-4" />
                  {toDate ? format(toDate, "PPP") : <span>Pick an end date</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={toDate}
                  onSelect={setTo}
                  initialFocus
                  className={cn("p-3 pointer-events-auto")}
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Switch
              id="includePast"
              checked={!!search.includePast}
              onCheckedChange={toggleIncludePast}
            />
            <Label htmlFor="includePast" className="cursor-pointer">Include past events</Label>
          </div>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      </section>

      <section className="mt-8">
        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-72 animate-pulse rounded-2xl border border-border bg-card" />
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center">
            <h2 className="text-lg font-medium">No events found</h2>
            <p className="mt-1 text-sm text-muted-foreground">Try adjusting your filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {events.map((ev) => {
              const isPast = new Date(ev.end_at).getTime() < Date.now();
              const going = counts[ev.id] ?? 0;
              return (
                <a
                  key={ev.id}
                  href={`/events/${ev.id}`}
                  className="group flex flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md"
                >
                  <div className="aspect-[16/9] overflow-hidden bg-muted">
                    {ev.cover_image_url ? (
                      <img
                        src={ev.cover_image_url}
                        alt=""
                        className="h-full w-full object-cover transition-transform group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                        <CalendarIcon className="h-10 w-10" />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-1 flex-col p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="line-clamp-2 text-base font-semibold leading-tight">{ev.title}</h3>
                      {isPast && <Badge variant="destructive" className="shrink-0">Ended</Badge>}
                    </div>
                    <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <CalendarIcon className="h-3.5 w-3.5" />
                        <span>{formatInTz(ev.start_at, ev.timezone)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <MapPin className="h-3.5 w-3.5" />
                        <span className="line-clamp-1">
                          {ev.venue_address || (ev.online_link ? "Online" : "—")}
                        </span>
                      </div>
                      {ev.hosts?.name && (
                        <div className="line-clamp-1 text-xs">by {ev.hosts.name}</div>
                      )}
                    </div>
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Users className="h-3.5 w-3.5" />
                      <span>
                        {going} / {ev.capacity} going
                      </span>
                    </div>
                  </div>
                </a>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
