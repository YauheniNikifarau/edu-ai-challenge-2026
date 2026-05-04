import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

export const getEventAttendeeEmails = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ eventId: z.string().uuid() }).parse(d))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context as { supabase: any; userId: string };

    // Verify caller is on the host team for this event
    const { data: ev } = await supabase
      .from("events")
      .select("id, host_id")
      .eq("id", data.eventId)
      .maybeSingle();
    if (!ev) throw new Response("Event not found", { status: 404 });

    const { data: hm } = await supabase
      .from("host_members")
      .select("role")
      .eq("host_id", ev.host_id)
      .eq("user_id", userId);
    const roles = (hm ?? []).map((r: { role: string }) => r.role);
    if (!roles.includes("host") && !roles.includes("checker")) {
      throw new Response("Forbidden", { status: 403 });
    }

    const { data: rsvps } = await supabase
      .from("rsvps")
      .select("user_id")
      .eq("event_id", data.eventId);
    const userIds = Array.from(new Set(((rsvps ?? []) as { user_id: string }[]).map((r) => r.user_id)));

    const emails: Record<string, string> = {};
    for (const uid of userIds) {
      const { data: u } = await supabaseAdmin.auth.admin.getUserById(uid);
      if (u?.user?.email) emails[uid] = u.user.email;
    }
    return { emails };
  });
