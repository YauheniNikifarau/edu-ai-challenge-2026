import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/integrations/supabase/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CalendarRange, Calendar, Pencil, QrCode, Download, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import { exportEventCsv } from "@/lib/event-csv";

export const Route = createFileRoute("/my-events")({
  head: () => ({
    meta: [
      { title: "My Events — Evently" },
      { name: "description", content: "Events you host or co-manage on Evently." },
    ],
  }),
  component: MyEventsPage,
});

type Row = {
  id: string;
  title: string;
  start_at: string;
  end_at: string;
  status: string;
  cover_image_url: string | null;
  host_id: string;
  host_name: string;
  roles: string[]; // host/checker for current user
};

function MyEventsPage() {
  const { user, loading } = useAuth();
  const [events, setEvents] = useState<Row[]>([]);
  const [fetching, setFetching] = useState(true);

  const [roleFilter, setRoleFilter] = useState<"all" | "host" | "checker">("all");
  const [search, setSearch] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    (async () => {
      setFetching(true);
      const { data: hm } = await supabase
        .from("host_members")
        .select("host_id, role")
        .eq("user_id", user.id);
      const memberships = (hm ?? []) as { host_id: string; role: string }[];
      const rolesByHost = new Map<string, string[]>();
      for (const m of memberships) {
        const arr = rolesByHost.get(m.host_id) ?? [];
        arr.push(m.role);
        rolesByHost.set(m.host_id, arr);
      }
      const hostIds = Array.from(rolesByHost.keys());
      if (hostIds.length === 0) {
        setEvents([]);
        setFetching(false);
        return;
      }
      const [{ data: hosts }, { data: evs }] = await Promise.all([
        supabase.from("hosts").select("id, name").in("id", hostIds),
        supabase
          .from("events")
          .select("id, title, start_at, end_at, status, cover_image_url, host_id")
          .in("host_id", hostIds)
          .is("deleted_at", null)
          .order("start_at", { ascending: false }),
      ]);
      const hostNameMap = new Map<string, string>();
      for (const h of (hosts ?? []) as { id: string; name: string }[]) {
        hostNameMap.set(h.id, h.name);
      }
      const rows: Row[] = ((evs ?? []) as Omit<Row, "host_name" | "roles">[]).map((e) => ({
        ...e,
        host_name: hostNameMap.get(e.host_id) ?? "",
        roles: rolesByHost.get(e.host_id) ?? [],
      }));
      setEvents(rows);
      setFetching(false);
    })();
  }, [user?.id]);

  const filtered = useMemo(() => {
    const fromTs = from ? new Date(from).getTime() : null;
    const toTs = to ? new Date(to).getTime() + 24 * 60 * 60 * 1000 : null;
    const q = search.trim().toLowerCase();
    return events.filter((e) => {
      if (roleFilter !== "all" && !e.roles.includes(roleFilter)) return false;
      if (q && !e.title.toLowerCase().includes(q) && !e.host_name.toLowerCase().includes(q)) return false;
      const startTs = new Date(e.start_at).getTime();
      if (fromTs && startTs < fromTs) return false;
      if (toTs && startTs > toTs) return false;
      return true;
    });
  }, [events, roleFilter, search, from, to]);

  if (loading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/my-events" }} />;

  const now = Date.now();

  const handleExport = async (e: Row) => {
    setBusy(e.id);
    try {
      await exportEventCsv(e.id, e.title);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">My Events</h1>
      <p className="mt-2 text-muted-foreground">Events you host or help manage.</p>

      <div className="mt-6 flex flex-wrap gap-3">
        <div className="w-44">
          <Select value={roleFilter} onValueChange={(v) => setRoleFilter(v as typeof roleFilter)}>
            <SelectTrigger><SelectValue placeholder="Role" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All roles</SelectItem>
              <SelectItem value="host">Host</SelectItem>
              <SelectItem value="checker">Checker</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Input
          placeholder="Search title or host"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64"
        />
        <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="w-44" />
        <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="w-44" />
      </div>

      {fetching ? null : filtered.length === 0 ? (
        <div className="mt-10 rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center">
          <CalendarRange className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-4 text-sm text-muted-foreground">No events match your filters.</p>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {filtered.map((e) => {
            const ended = new Date(e.end_at).getTime() < now;
            const isHost = e.roles.includes("host");
            return (
              <li key={e.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                <div className="h-14 w-20 shrink-0 overflow-hidden rounded-lg bg-muted">
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
                    {e.roles.map((r) => (
                      <Badge key={r} variant={r === "host" ? "default" : "secondary"}>
                        {r}
                      </Badge>
                    ))}
                    {ended && <Badge variant="destructive">Ended</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(e.start_at).toLocaleString(undefined, {
                      month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
                    })}
                    {" · "}{e.host_name}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {isHost && (
                    <Button asChild size="sm" variant="outline">
                      <Link to="/dashboard/events/$id/edit" params={{ id: e.id }}>
                        <Pencil className="h-4 w-4" /> Edit
                      </Link>
                    </Button>
                  )}
                  <Button asChild size="sm" variant="outline">
                    <Link to="/dashboard/events/$id/checkin" params={{ id: e.id }}>
                      <QrCode className="h-4 w-4" /> Check-in
                    </Link>
                  </Button>
                  {isHost && (
                    <>
                      <Button size="sm" variant="outline" disabled={busy === e.id} onClick={() => handleExport(e)}>
                        <Download className="h-4 w-4" /> Export CSV
                      </Button>
                      <Button asChild size="sm" variant="outline">
                        <Link to="/dashboard">
                          <BarChart3 className="h-4 w-4" /> Stats
                        </Link>
                      </Button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
