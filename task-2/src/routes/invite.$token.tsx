import { createFileRoute, Navigate, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { acceptHostInvite } from "@/server/invites.functions";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/invite/$token")({
  head: () => ({ meta: [{ title: "Accept Invite — Evently" }] }),
  component: InvitePage,
});

function InvitePage() {
  const { token } = Route.useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const ran = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading || !user || ran.current) return;
    ran.current = true;
    (async () => {
      try {
        const res = await acceptHostInvite({ data: { token } });
        if (!res.ok) {
          setError(res.error);
          return;
        }
        toast.success(`You've joined ${res.hostName} as ${res.role}.`);
        navigate({ to: "/dashboard", replace: true });
      } catch {
        setError("This invite link is invalid or has expired.");
      }
    })();
  }, [loading, user, token, navigate]);

  if (loading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: `/invite/${token}` }} />;

  if (error) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <h1 className="text-2xl font-semibold">Invite unavailable</h1>
        <p className="mt-3 text-sm text-muted-foreground">{error}</p>
        <Button asChild className="mt-6" variant="outline">
          <Link to="/">Go home</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-20 text-center text-sm text-muted-foreground">
      Accepting invite…
    </div>
  );
}
