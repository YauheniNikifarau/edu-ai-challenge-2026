import { createFileRoute, Link, Navigate, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { useMyHost } from "@/lib/use-my-host";
import { EventForm, utcToLocalWall } from "@/components/EventForm";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Trash2, Copy, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/dashboard/events/$id/edit")({
  head: () => ({
    meta: [
      { title: "Edit Event — Evently" },
      { name: "description", content: "Edit an event on Evently." },
    ],
  }),
  component: EditEventPage,
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
  visibility: string;
  pricing_type: string;
  status: string;
};

function EditEventPage() {
  const { id } = Route.useParams();
  const { user, loading } = useAuth();
  const { host, loading: hostLoading } = useMyHost();
  const navigate = useNavigate();

  const [event, setEvent] = useState<EventRow | null>(null);
  const [fetching, setFetching] = useState(true);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    const { data } = await supabase
      .from("events")
      .select("*")
      .eq("id", id)
      .is("deleted_at", null)
      .maybeSingle();
    setEvent((data as EventRow) ?? null);
    setFetching(false);
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading || hostLoading || fetching) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: `/dashboard/events/${id}/edit` }} />;
  if (!host) return <Navigate to="/become-a-host" />;
  if (!event || event.host_id !== host.id) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <h1 className="text-2xl font-semibold">Event not found</h1>
        <p className="mt-2 text-muted-foreground">This event doesn't exist or you don't have access.</p>
        <Button asChild className="mt-6">
          <Link to="/dashboard">Back to dashboard</Link>
        </Button>
      </div>
    );
  }

  const setStatus = async (status: "draft" | "published") => {
    setBusy(true);
    const { error } = await supabase.from("events").update({ status }).eq("id", event.id);
    setBusy(false);
    if (error) return toast.error(error.message);
    toast.success(status === "published" ? "Event published" : "Event unpublished");
    refresh();
  };

  const duplicate = async () => {
    setBusy(true);
    const { data, error } = await supabase
      .from("events")
      .insert({
        host_id: event.host_id,
        title: `${event.title} (Copy)`,
        description: event.description,
        start_at: event.start_at,
        end_at: event.end_at,
        timezone: event.timezone,
        venue_address: event.venue_address,
        online_link: event.online_link,
        capacity: event.capacity,
        cover_image_url: event.cover_image_url,
        visibility: event.visibility,
        pricing_type: event.pricing_type,
        status: "draft",
      })
      .select("id")
      .single();
    setBusy(false);
    if (error) return toast.error(error.message);
    toast.success("Event duplicated");
    navigate({ to: "/dashboard/events/$id/edit", params: { id: data.id } });
  };

  const remove = async () => {
    setBusy(true);
    const { error } = await supabase
      .from("events")
      .update({ deleted_at: new Date().toISOString(), status: "draft" })
      .eq("id", event.id);
    setBusy(false);
    if (error) return toast.error(error.message);
    toast.success("Event deleted");
    navigate({ to: "/dashboard" });
  };

  const isPast = new Date(event.end_at).getTime() < Date.now();

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight">Edit event</h1>
            <Badge variant={event.status === "published" ? "default" : "secondary"}>
              {event.status === "published" ? "Published" : "Draft"}
            </Badge>
            {isPast && <Badge variant="destructive">Ended</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{event.title}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/events/$id" params={{ id: event.id }}>
              <ExternalLink className="h-4 w-4" /> View
            </Link>
          </Button>
          {event.status === "draft" ? (
            <Button size="sm" disabled={busy} onClick={() => setStatus("published")}>
              <Eye className="h-4 w-4" /> Publish
            </Button>
          ) : (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => setStatus("draft")}>
              <EyeOff className="h-4 w-4" /> Unpublish
            </Button>
          )}
          <Button size="sm" variant="outline" disabled={busy} onClick={duplicate}>
            <Copy className="h-4 w-4" /> Duplicate
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button size="sm" variant="destructive" disabled={busy}>
                <Trash2 className="h-4 w-4" /> Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this event?</AlertDialogTitle>
                <AlertDialogDescription>
                  This event will be removed and no longer visible to attendees. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={remove}>Delete</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      <div className="mt-8">
        <EventForm
          hostId={host.id}
          submitLabel="Save changes"
          initial={{
            id: event.id,
            title: event.title,
            description: event.description ?? "",
            start_local: utcToLocalWall(event.start_at, event.timezone),
            end_local: utcToLocalWall(event.end_at, event.timezone),
            timezone: event.timezone,
            venue_address: event.venue_address ?? "",
            online_link: event.online_link ?? "",
            capacity: event.capacity,
            cover_image_url: event.cover_image_url,
            visibility: (event.visibility as "public" | "unlisted") ?? "public",
            pricing_type: "free",
          }}
          onSaved={() => refresh()}
        />
      </div>
    </div>
  );
}
