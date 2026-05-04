import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Helmet } from "react-helmet-async";
import { supabase } from "@/integrations/supabase/client";
import { Mail, MapPin, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/hosts/$slug")({
  head: () => ({
    meta: [
      { title: "Host — Evently" },
      { name: "description", content: "Host profile and events on Evently." },
    ],
  }),
  component: HostPublicPage,
});

type Host = {
  id: string;
  slug: string;
  name: string;
  bio: string | null;
  logo_url: string | null;
  contact_email: string | null;
};

type EventRow = {
  id: string;
  title: string;
  description: string | null;
  cover_image_url: string | null;
  start_at: string;
  end_at: string;
  venue_address: string | null;
  online_link: string | null;
};

function HostPublicPage() {
  const { slug } = Route.useParams();
  const [host, setHost] = useState<Host | null>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const { data: h } = await supabase
        .from("hosts")
        .select("id, slug, name, bio, logo_url, contact_email")
        .eq("slug", slug)
        .maybeSingle();
      if (cancelled) return;
      setHost(h as Host | null);
      if (h) {
        const { data: ev } = await supabase
          .from("events")
          .select("id, title, description, cover_image_url, start_at, end_at, venue_address, online_link")
          .eq("host_id", h.id)
          .eq("status", "published")
          .order("start_at", { ascending: false });
        if (!cancelled) setEvents((ev as EventRow[]) ?? []);
      }
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) return null;

  if (!host) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <h1 className="text-2xl font-semibold">Host not found</h1>
        <p className="mt-2 text-muted-foreground">This host doesn't exist or has been removed.</p>
      </div>
    );
  }

  const title = `${host.name} — Evently`;
  const description = host.bio?.slice(0, 160) || `Events hosted by ${host.name} on Evently.`;
  const now = Date.now();

  return (
    <>
      <Helmet>
        <title>{title}</title>
        <meta name="description" content={description} />
        <meta property="og:title" content={title} />
        <meta property="og:description" content={description} />
        <meta property="og:type" content="profile" />
        {host.logo_url && <meta property="og:image" content={host.logo_url} />}
        <meta name="twitter:card" content="summary_large_image" />
        {host.logo_url && <meta name="twitter:image" content={host.logo_url} />}
      </Helmet>

      <div className="mx-auto max-w-5xl px-4 py-12">
        <header className="flex flex-col items-start gap-6 sm:flex-row sm:items-center">
          {host.logo_url ? (
            <img src={host.logo_url} alt={host.name} className="h-24 w-24 rounded-2xl border border-border object-cover" />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-primary text-2xl font-semibold text-primary-foreground">
              {host.name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <div className="flex-1">
            <h1 className="text-3xl font-semibold tracking-tight">{host.name}</h1>
            {host.bio && <p className="mt-2 max-w-2xl text-muted-foreground">{host.bio}</p>}
            {host.contact_email && (
              <a
                href={`mailto:${host.contact_email}`}
                className="mt-3 inline-flex items-center gap-2 text-sm text-primary hover:underline"
              >
                <Mail className="h-4 w-4" />
                {host.contact_email}
              </a>
            )}
          </div>
        </header>

        <section className="mt-12">
          <h2 className="text-xl font-semibold">Events</h2>
          {events.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-border bg-card/50 p-12 text-center">
              <Calendar className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-4 text-sm text-muted-foreground">No published events yet.</p>
            </div>
          ) : (
            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {events.map((e) => {
                const ended = new Date(e.end_at).getTime() < now;
                const start = new Date(e.start_at);
                return (
                  <Link
                    key={e.id}
                    to="/events/$id"
                    params={{ id: e.id }}
                    className="group overflow-hidden rounded-2xl border border-border bg-card transition-shadow hover:shadow-md"
                  >
                    <div className="aspect-video w-full overflow-hidden bg-muted">
                      {e.cover_image_url ? (
                        <img
                          src={e.cover_image_url}
                          alt=""
                          className="h-full w-full object-cover transition-transform group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                          <Calendar className="h-10 w-10" />
                        </div>
                      )}
                    </div>
                    <div className="p-4">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold leading-tight">{e.title}</h3>
                        {ended && <Badge variant="secondary">Ended</Badge>}
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        {start.toLocaleString(undefined, {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </p>
                      {(e.venue_address || e.online_link) && (
                        <p className="mt-1 flex items-center gap-1 truncate text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3 shrink-0" />
                          <span className="truncate">{e.venue_address || "Online"}</span>
                        </p>
                      )}
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </>
  );
}
