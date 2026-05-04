import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ImagePlus, Image as ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { ReportButton } from "./ReportButton";

type Photo = {
  id: string;
  storage_path: string;
  status: string;
  uploaded_by: string;
};

export function EventGallery({ eventId, canUpload }: { eventId: string; canUpload: boolean }) {
  const { user } = useAuth();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const { data } = await supabase
      .from("gallery_photos")
      .select("id, storage_path, status, uploaded_by")
      .eq("event_id", eventId)
      .order("created_at", { ascending: false });
    setPhotos((data as Photo[]) ?? []);
  }, [eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!user) return;
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please choose an image file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error("Image must be under 10 MB.");
      return;
    }
    setUploading(true);
    try {
      const ext = file.name.split(".").pop() ?? "jpg";
      const path = `${user.id}/${eventId}/${crypto.randomUUID()}.${ext}`;
      const { error: upErr } = await supabase.storage.from("gallery").upload(path, file, {
        cacheControl: "3600",
        upsert: false,
      });
      if (upErr) throw upErr;

      const { error: insErr } = await supabase.from("gallery_photos").insert({
        event_id: eventId,
        uploaded_by: user.id,
        storage_path: path,
        status: "pending",
      });
      if (insErr) throw insErr;

      toast.success("Your photo has been submitted for review.");
      void load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const visible = photos.filter(
    (p) => p.status === "approved" || (user && p.uploaded_by === user.id),
  );

  return (
    <section className="mt-12">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <ImageIcon className="h-5 w-5" /> Gallery
        </h2>
        {canUpload && (
          <>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleUpload}
            />
            <Button size="sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
              <ImagePlus className="h-4 w-4" /> Upload Photo
            </Button>
          </>
        )}
      </div>

      {visible.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">No photos yet.</p>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {visible.map((p) => {
            const url = supabase.storage.from("gallery").getPublicUrl(p.storage_path).data.publicUrl;
            const mine = user && p.uploaded_by === user.id;
            return (
              <div key={p.id} className="overflow-hidden rounded-lg border border-border bg-card">
                <div className="aspect-square w-full overflow-hidden bg-muted">
                  <img src={url} alt="" className="h-full w-full object-cover" loading="lazy" />
                </div>
                <div className="flex items-center justify-between p-2">
                  {mine && p.status !== "approved" ? (
                    <Badge variant={p.status === "rejected" ? "destructive" : "secondary"}>
                      {p.status}
                    </Badge>
                  ) : (
                    <span />
                  )}
                  {p.status === "approved" && <ReportButton targetType="gallery_photo" targetId={p.id} label="" />}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
