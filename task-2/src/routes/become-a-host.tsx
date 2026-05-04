import { createFileRoute, Navigate, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth";
import { useMyHost, slugify } from "@/lib/use-my-host";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export const Route = createFileRoute("/become-a-host")({
  head: () => ({
    meta: [
      { title: "Become a Host — Evently" },
      { name: "description", content: "Register as a host on Evently to start creating community events." },
    ],
  }),
  component: BecomeHostPage,
});

function BecomeHostPage() {
  const { user, loading } = useAuth();
  const { host, loading: hostLoading } = useMyHost();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [bio, setBio] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user?.email && !contactEmail) setContactEmail(user.email);
  }, [user?.email, contactEmail]);

  useEffect(() => {
    if (!slugTouched) setSlug(slugify(name));
  }, [name, slugTouched]);

  if (loading || hostLoading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/become-a-host" }} />;
  if (host) return <Navigate to="/dashboard" />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !slug.trim() || !contactEmail.trim()) {
      toast.error("Please fill in all required fields");
      return;
    }
    setSubmitting(true);
    try {
      // Check slug uniqueness
      const { data: existing } = await supabase
        .from("hosts")
        .select("id")
        .eq("slug", slug)
        .maybeSingle();
      if (existing) {
        toast.error("That slug is taken. Try another.");
        setSubmitting(false);
        return;
      }

      let logoUrl: string | null = null;
      if (logoFile) {
        const ext = logoFile.name.split(".").pop() || "png";
        const path = `${user.id}/${crypto.randomUUID()}.${ext}`;
        const { error: upErr } = await supabase.storage
          .from("host-assets")
          .upload(path, logoFile, { upsert: false, contentType: logoFile.type });
        if (upErr) throw upErr;
        logoUrl = supabase.storage.from("host-assets").getPublicUrl(path).data.publicUrl;
      }

      const { data: hostRow, error: hostErr } = await supabase
        .from("hosts")
        .insert({
          owner_id: user.id,
          name: name.trim(),
          slug: slug.trim(),
          bio: bio.trim() || null,
          contact_email: contactEmail.trim(),
          logo_url: logoUrl,
        })
        .select("id")
        .single();
      if (hostErr) throw hostErr;

      const { error: memberErr } = await supabase
        .from("host_members")
        .insert({ host_id: hostRow.id, user_id: user.id, role: "host", accepted_at: new Date().toISOString() });
      if (memberErr) throw memberErr;

      toast.success("You're now a host!");
      navigate({ to: "/dashboard" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to register as host");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Become a Host</h1>
      <p className="mt-2 text-muted-foreground">
        Set up your host profile to start creating events on Evently.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="space-y-2">
          <Label htmlFor="name">Host name *</Label>
          <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="slug">URL slug *</Label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">/hosts/</span>
            <Input
              id="slug"
              required
              value={slug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(slugify(e.target.value));
              }}
              maxLength={60}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="logo">Logo</Label>
          <Input
            id="logo"
            type="file"
            accept="image/*"
            onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="bio">Short bio</Label>
          <Textarea id="bio" rows={4} value={bio} onChange={(e) => setBio(e.target.value)} maxLength={500} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="contactEmail">Contact email *</Label>
          <Input
            id="contactEmail"
            type="email"
            required
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
          />
        </div>

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Creating host..." : "Create host"}
        </Button>
      </form>
    </div>
  );
}
