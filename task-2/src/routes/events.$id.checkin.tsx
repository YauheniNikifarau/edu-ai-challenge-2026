import { createFileRoute, Navigate } from "@tanstack/react-router";

export const Route = createFileRoute("/events/$id/checkin")({
  component: RedirectToDashboardCheckin,
});

function RedirectToDashboardCheckin() {
  const { id } = Route.useParams();
  return <Navigate to="/dashboard/events/$id/checkin" params={{ id }} replace />;
}
