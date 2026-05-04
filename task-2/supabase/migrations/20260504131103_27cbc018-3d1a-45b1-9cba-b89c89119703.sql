-- Create public bucket for host logos
insert into storage.buckets (id, name, public)
values ('host-assets', 'host-assets', true)
on conflict (id) do nothing;

-- Public read
create policy "Host assets are publicly readable"
on storage.objects for select
using (bucket_id = 'host-assets');

-- Authenticated users can upload to their own folder (first path segment = user id)
create policy "Users upload host assets in own folder"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'host-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users update own host assets"
on storage.objects for update
to authenticated
using (
  bucket_id = 'host-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users delete own host assets"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'host-assets'
  and auth.uid()::text = (storage.foldername(name))[1]
);