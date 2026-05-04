import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

export const acceptHostInvite = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ token: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    const { userId } = context as { userId: string };

    const { data: tok } = await supabaseAdmin
      .from("host_invite_tokens")
      .select("id, host_id, role, expires_at")
      .eq("token", data.token)
      .maybeSingle();

    if (!tok) {
      return { ok: false as const, error: "This invite link is invalid or has expired." };
    }
    if (tok.expires_at && new Date(tok.expires_at).getTime() < Date.now()) {
      await supabaseAdmin.from("host_invite_tokens").delete().eq("id", tok.id);
      return { ok: false as const, error: "This invite link is invalid or has expired." };
    }

    const { data: existing } = await supabaseAdmin
      .from("host_members")
      .select("id")
      .eq("host_id", tok.host_id)
      .eq("user_id", userId)
      .eq("role", tok.role)
      .maybeSingle();

    if (!existing) {
      const { error: insErr } = await supabaseAdmin.from("host_members").insert({
        host_id: tok.host_id,
        user_id: userId,
        role: tok.role,
        accepted_at: new Date().toISOString(),
      });
      if (insErr) return { ok: false as const, error: insErr.message };
    }

    await supabaseAdmin.from("host_invite_tokens").delete().eq("id", tok.id);

    const { data: host } = await supabaseAdmin
      .from("hosts")
      .select("name")
      .eq("id", tok.host_id)
      .maybeSingle();

    return { ok: true as const, hostName: host?.name ?? "the team", role: tok.role };
  });
