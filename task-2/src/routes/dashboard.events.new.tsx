import { createFileRoute, Navigate, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth";
import { useMyHost } from "@/lib/use-my-host";
import { EventForm } from "@/components/EventForm";

export const Route = createFileRoute("/dashboard/events/new")({
  head: () => ({
    meta: [
      { title: "New Event — Evently" },
      { name: "description", content: "Create a new event on Evently." },
    ],
  }),
  component: NewEventPage,
});

function NewEventPage() {
  const { user, loading } = useAuth();
  const { host, loading: hostLoading } = useMyHost();
  const navigate = useNavigate();

  if (loading || hostLoading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/dashboard/events/new" }} />;
  if (!host) return <Navigate to="/become-a-host" />;

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">New event</h1>
      <p className="mt-2 text-sm text-muted-foreground">Fill in the details. You can publish later.</p>
      <div className="mt-8">
        <EventForm
          hostId={host.id}
          submitLabel="Create draft"
          onSaved={(id) => navigate({ to: "/dashboard/events/$id/edit", params: { id } })}
        />
      </div>
    </div>
  );
}
