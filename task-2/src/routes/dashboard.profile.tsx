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

export const Route = createFileRoute("/dashboard/profile")({
  head: () => ({
    meta: [
      { title: "Edit Host Profile — Evently" },
      { name: "description", content: "Edit your host profile on Evently." },
    ],
  }),
  component: EditProfilePage,
});

function EditProfilePage() {
  const { user, loading } = useAuth();
  const { host, loading: hostLoading, refresh } = useMyHost();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [bio, setBio] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (host) {
      setName(host.name);
      setSlug(host.slug);
      setBio(host.bio ?? "");
      setContactEmail(host.contact_email ?? "");
    }
  }, [host]);

  if (loading || hostLoading) return null;
  if (!user) return <Navigate to="/sign-in" search={{ returnTo: "/dashboard/profile" }} />;
  if (!host) return <Navigate to="/become-a-host" />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      // Slug uniqueness check if changed
      if (slug !== host.slug) {
        const { data: existing } = await supabase
          .from("hosts")
          .select("id")
          .eq("slug", slug)
          .maybeSingle();
        if (existing) {
          toast.error("That slug is taken.");
          setSubmitting(false);
          return;
        }
      }

      let logoUrl = host.logo_url;
      if (logoFile) {
        // Delete old logo if it lives in our bucket
        if (host.logo_url) {
          const marker = "/host-assets/";
          const idx = host.logo_url.indexOf(marker);
          if (idx >= 0) {
            const oldPath = host.logo_url.slice(idx + marker.length);
            await supabase.storage.from("host-assets").remove([oldPath]);
          }
        }
        const ext = logoFile.name.split(".").pop() || "png";
        const path = `${user.id}/${crypto.randomUUID()}.${ext}`;
        const { error: upErr } = await supabase.storage
          .from("host-assets")
          .upload(path, logoFile, { contentType: logoFile.type });
        if (upErr) throw upErr;
        logoUrl = supabase.storage.from("host-assets").getPublicUrl(path).data.publicUrl;
      }

      const { error } = await supabase
        .from("hosts")
        .update({
          name: name.trim(),
          slug: slug.trim(),
          bio: bio.trim() || null,
          contact_email: contactEmail.trim(),
          logo_url: logoUrl,
        })
        .eq("id", host.id);
      if (error) throw error;

      await refresh();
      toast.success("Profile updated");
      navigate({ to: "/dashboard" });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Edit host profile</h1>

      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-2xl border border-border bg-card p-6 shadow-sm">
        <div className="space-y-2">
          <Label htmlFor="name">Host name *</Label>
          <Input id="name" required value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="slug">URL slug *</Label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">/hosts/</span>
            <Input id="slug" required value={slug} onChange={(e) => setSlug(slugify(e.target.value))} maxLength={60} />
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="logo">Replace logo</Label>
          {host.logo_url && (
            <img src={host.logo_url} alt="" className="h-16 w-16 rounded-lg border border-border object-cover" />
          )}
          <Input id="logo" type="file" accept="image/*" onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="bio">Short bio</Label>
          <Textarea id="bio" rows={4} value={bio} onChange={(e) => setBio(e.target.value)} maxLength={500} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="contactEmail">Contact email *</Label>
          <Input id="contactEmail" type="email" required value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : "Save changes"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate({ to: "/dashboard" })}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
