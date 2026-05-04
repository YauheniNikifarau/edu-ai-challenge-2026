-- Soft-delete column for events
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone;
CREATE INDEX IF NOT EXISTS events_deleted_at_idx ON public.events(deleted_at);

-- Allow host role to delete events (hard delete used by client; we'll soft-delete by default)
DROP POLICY IF EXISTS "Host role deletes events" ON public.events;
CREATE POLICY "Host role deletes events"
ON public.events
FOR DELETE
USING (has_host_role(host_id, auth.uid(), 'host'));

-- Storage bucket for event assets (cover images)
INSERT INTO storage.buckets (id, name, public)
VALUES ('event-assets', 'event-assets', true)
ON CONFLICT (id) DO NOTHING;

-- Public read of event-assets
DROP POLICY IF EXISTS "Event assets are publicly accessible" ON storage.objects;
CREATE POLICY "Event assets are publicly accessible"
ON storage.objects FOR SELECT
USING (bucket_id = 'event-assets');

-- Authenticated users can upload to their own folder (first path segment = auth.uid())
DROP POLICY IF EXISTS "Users upload event assets to own folder" ON storage.objects;
CREATE POLICY "Users upload event assets to own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'event-assets' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Users update own event assets" ON storage.objects;
CREATE POLICY "Users update own event assets"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'event-assets' AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "Users delete own event assets" ON storage.objects;
CREATE POLICY "Users delete own event assets"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'event-assets' AND auth.uid()::text = (storage.foldername(name))[1]);