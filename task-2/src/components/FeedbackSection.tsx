import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Star } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

const schema = z.object({
  rating: z.number().int().min(1).max(5),
  comment: z.string().trim().max(1000).optional(),
});

export function FeedbackSection({ eventId, canSubmit }: { eventId: string; canSubmit: boolean }) {
  const { user } = useAuth();
  const [mine, setMine] = useState<{ rating: number; comment: string | null } | null>(null);
  const [agg, setAgg] = useState<{ avg: number; count: number }>({ avg: 0, count: 0 });
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const { data: list } = await supabase
      .from("feedback")
      .select("rating, comment, user_id")
      .eq("event_id", eventId);
    const rows = (list ?? []) as { rating: number; comment: string | null; user_id: string }[];
    const count = rows.length;
    const avg = count ? rows.reduce((s, r) => s + r.rating, 0) / count : 0;
    setAgg({ avg, count });
    if (user) {
      const m = rows.find((r) => r.user_id === user.id);
      setMine(m ? { rating: m.rating, comment: m.comment } : null);
    }
  }, [eventId, user?.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const submit = async () => {
    if (!user) return;
    const parsed = schema.safeParse({ rating, comment: comment || undefined });
    if (!parsed.success) {
      toast.error("Please pick a star rating.");
      return;
    }
    setBusy(true);
    const { error } = await supabase.from("feedback").insert({
      event_id: eventId,
      user_id: user.id,
      rating: parsed.data.rating,
      comment: parsed.data.comment ?? null,
    });
    setBusy(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Thanks for your feedback!");
    void load();
  };

  return (
    <section className="mt-12">
      <h2 className="text-xl font-semibold">Feedback</h2>

      <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
        <div className="flex">
          {[1, 2, 3, 4, 5].map((n) => (
            <Star
              key={n}
              className={`h-4 w-4 ${n <= Math.round(agg.avg) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40"}`}
            />
          ))}
        </div>
        <span>
          {agg.count > 0
            ? `${agg.avg.toFixed(1)} · ${agg.count} review${agg.count === 1 ? "" : "s"}`
            : "No reviews yet"}
        </span>
      </div>

      {canSubmit && (
        <Card className="mt-4 p-5">
          {mine ? (
            <div>
              <p className="text-sm font-medium">Thanks for your feedback!</p>
              <div className="mt-2 flex">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star
                    key={n}
                    className={`h-5 w-5 ${n <= mine.rating ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40"}`}
                  />
                ))}
              </div>
              {mine.comment && <p className="mt-2 text-sm text-muted-foreground">{mine.comment}</p>}
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium">Leave Feedback</p>
              <div className="mt-3 flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onMouseEnter={() => setHover(n)}
                    onMouseLeave={() => setHover(0)}
                    onClick={() => setRating(n)}
                    aria-label={`${n} star${n === 1 ? "" : "s"}`}
                  >
                    <Star
                      className={`h-7 w-7 transition-colors ${
                        n <= (hover || rating) ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40"
                      }`}
                    />
                  </button>
                ))}
              </div>
              <Textarea
                className="mt-3"
                placeholder="Share your thoughts (optional)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                maxLength={1000}
                rows={3}
              />
              <Button className="mt-3" onClick={submit} disabled={busy || rating === 0}>
                Submit feedback
              </Button>
            </div>
          )}
        </Card>
      )}
    </section>
  );
}
