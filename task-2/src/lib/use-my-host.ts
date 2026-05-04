import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";

export type MyHost = {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  bio: string | null;
  contact_email: string | null;
  owner_id: string;
};

export function useMyHost() {
  const { user, loading: authLoading } = useAuth();
  const [host, setHost] = useState<MyHost | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!user) {
      setHost(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    // Find any host where user is a member
    const { data: memberships } = await supabase
      .from("host_members")
      .select("host_id")
      .eq("user_id", user.id)
      .limit(1);

    if (!memberships || memberships.length === 0) {
      setHost(null);
      setLoading(false);
      return;
    }
    const { data: h } = await supabase
      .from("hosts")
      .select("id, slug, name, logo_url, bio, contact_email, owner_id")
      .eq("id", memberships[0].host_id)
      .maybeSingle();
    setHost((h as MyHost) ?? null);
    setLoading(false);
  };

  useEffect(() => {
    if (authLoading) return;
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, authLoading]);

  return { host, loading, refresh };
}

export function slugify(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
}
