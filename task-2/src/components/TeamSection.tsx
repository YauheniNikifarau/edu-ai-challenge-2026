import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { UserPlus, Copy, Users } from "lucide-react";
import { toast } from "sonner";

type Member = { id: string; user_id: string; role: string; display_name: string | null };
type Token = { id: string; token: string; role: string; expires_at: string | null };

export function TeamSection({ hostId }: { hostId: string }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { data: hm } = await supabase
      .from("host_members")
      .select("id, user_id, role")
      .eq("host_id", hostId);
    const list = (hm ?? []) as { id: string; user_id: string; role: string }[];
    const ids = Array.from(new Set(list.map((m) => m.user_id)));
    const { data: profiles } = ids.length
      ? await supabase.from("profiles").select("id, display_name").in("id", ids)
      : { data: [] as { id: string; display_name: string | null }[] };
    const nameMap = new Map<string, string | null>();
    for (const p of (profiles ?? []) as { id: string; display_name: string | null }[]) {
      nameMap.set(p.id, p.display_name);
    }
    setMembers(list.map((m) => ({ ...m, display_name: nameMap.get(m.user_id) ?? null })));

    const { data: toks } = await supabase
      .from("host_invite_tokens")
      .select("id, token, role, expires_at")
      .eq("host_id", hostId)
      .order("created_at", { ascending: false });
    setTokens((toks as Token[]) ?? []);
  }, [hostId]);

  useEffect(() => {
    void load();
  }, [load]);

  const createInvite = async (role: "host" | "checker") => {
    setBusy(true);
    const expires = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
    const { error } = await supabase
      .from("host_invite_tokens")
      .insert({ host_id: hostId, role, expires_at: expires });
    setBusy(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success(`Invite link created for ${role}.`);
    void load();
  };

  const copyLink = async (token: string) => {
    const url = `${window.location.origin}/invite/${token}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Invite link copied.");
    } catch {
      toast.error("Could not copy. Link: " + url);
    }
  };

  return (
    <section className="mt-12">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Users className="h-5 w-5" /> Team
        </h2>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" disabled={busy} onClick={() => createInvite("checker")}>
            <UserPlus className="h-4 w-4" /> Invite Checker
          </Button>
          <Button size="sm" disabled={busy} onClick={() => createInvite("host")}>
            <UserPlus className="h-4 w-4" /> Invite Co-host
          </Button>
        </div>
      </div>

      <Card className="mt-4 p-4">
        <p className="mb-2 text-xs font-medium text-muted-foreground">Members</p>
        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">No team members yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {members.map((m) => (
              <li key={m.id} className="flex items-center justify-between py-2">
                <span className="text-sm">{m.display_name ?? m.user_id.slice(0, 8)}</span>
                <Badge variant={m.role === "host" ? "default" : "secondary"}>{m.role}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {tokens.length > 0 && (
        <Card className="mt-3 p-4">
          <p className="mb-2 text-xs font-medium text-muted-foreground">Pending invites</p>
          <ul className="space-y-2">
            {tokens.map((t) => {
              const url = typeof window !== "undefined" ? `${window.location.origin}/invite/${t.token}` : `/invite/${t.token}`;
              const expired = t.expires_at && new Date(t.expires_at).getTime() < Date.now();
              return (
                <li key={t.id} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Badge variant={t.role === "host" ? "default" : "secondary"}>{t.role}</Badge>
                  <Input readOnly value={url} className="flex-1 font-mono text-xs" />
                  <Button size="sm" variant="outline" onClick={() => copyLink(t.token)}>
                    <Copy className="h-4 w-4" /> Copy
                  </Button>
                  {expired && <Badge variant="destructive">expired</Badge>}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </section>
  );
}
