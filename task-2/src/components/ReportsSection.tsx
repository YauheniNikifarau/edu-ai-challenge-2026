import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Flag, EyeOff, Check } from "lucide-react";
import { toast } from "sonner";

type Report = {
  id: string;
  target_type: string;
  target_id: string;
  reason: string | null;
  reporter_id: string;
  status: string;
  created_at: string;
  reporter_name: string | null;
  context: string;
};

export function ReportsSection({ hostId }: { hostId: string }) {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const { data: events } = await supabase
      .from("events")
      .select("id, title")
      .eq("host_id", hostId);
    const eventList = (events ?? []) as { id: string; title: string }[];
    const eventIds = eventList.map((e) => e.id);
    const eventTitle = new Map(eventList.map((e) => [e.id, e.title]));

    let photoIds: string[] = [];
    let photoEvent = new Map<string, string>();
    if (eventIds.length) {
      const { data: photos } = await supabase
        .from("gallery_photos")
        .select("id, event_id")
        .in("event_id", eventIds);
      const list = (photos ?? []) as { id: string; event_id: string }[];
      photoIds = list.map((p) => p.id);
      photoEvent = new Map(list.map((p) => [p.id, p.event_id]));
    }

    const { data: rs } = await supabase
      .from("reports")
      .select("id, target_type, target_id, reason, reporter_id, status, created_at")
      .eq("status", "pending")
      .or(
        [
          eventIds.length ? `and(target_type.eq.event,target_id.in.(${eventIds.join(",")}))` : null,
          photoIds.length ? `and(target_type.eq.gallery_photo,target_id.in.(${photoIds.join(",")}))` : null,
        ].filter(Boolean).join(","),
      )
      .order("created_at", { ascending: false });

    const list = (rs ?? []) as Omit<Report, "reporter_name" | "context">[];
    const reporterIds = Array.from(new Set(list.map((r) => r.reporter_id)));
    const { data: profiles } = reporterIds.length
      ? await supabase.from("profiles").select("id, display_name").in("id", reporterIds)
      : { data: [] };
    const nameMap = new Map<string, string | null>();
    for (const p of (profiles ?? []) as { id: string; display_name: string | null }[]) {
      nameMap.set(p.id, p.display_name);
    }

    setReports(
      list.map((r) => ({
        ...r,
        reporter_name: nameMap.get(r.reporter_id) ?? null,
        context:
          r.target_type === "event"
            ? eventTitle.get(r.target_id) ?? "(unknown event)"
            : `Photo in ${eventTitle.get(photoEvent.get(r.target_id) ?? "") ?? "(unknown event)"}`,
      })),
    );
    setLoading(false);
  }, [hostId]);

  useEffect(() => {
    void load();
  }, [load]);

  const hide = async (r: Report) => {
    const { error: updErr } = await supabase
      .from("reports")
      .update({ status: "hidden" })
      .eq("id", r.id);
    if (updErr) {
      toast.error(updErr.message);
      return;
    }
    if (r.target_type === "event") {
      await supabase.from("events").update({ status: "draft" }).eq("id", r.target_id);
    } else if (r.target_type === "gallery_photo") {
      await supabase.from("gallery_photos").update({ status: "rejected" }).eq("id", r.target_id);
    }
    toast.success("Content hidden.");
    void load();
  };

  const dismiss = async (r: Report) => {
    const { error } = await supabase.from("reports").update({ status: "resolved" }).eq("id", r.id);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Report dismissed.");
    void load();
  };

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <Flag className="h-5 w-5" /> Reports
      </h2>
      {loading ? null : reports.length === 0 ? (
        <Card className="mt-4 p-6 text-center text-sm text-muted-foreground">No pending reports.</Card>
      ) : (
        <div className="mt-4 space-y-3">
          {reports.map((r) => (
            <Card key={r.id} className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{r.target_type === "event" ? "Event" : "Photo"}</Badge>
                <span className="text-sm font-medium">{r.context}</span>
              </div>
              <p className="mt-2 text-sm">{r.reason || <em className="text-muted-foreground">No reason provided.</em>}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Reported by {r.reporter_name ?? "Anonymous"} · {new Date(r.created_at).toLocaleString()}
              </p>
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => hide(r)}>
                  <EyeOff className="h-4 w-4" /> Hide
                </Button>
                <Button size="sm" variant="outline" onClick={() => dismiss(r)}>
                  <Check className="h-4 w-4" /> Dismiss
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
