
-- Gallery storage bucket
insert into storage.buckets (id, name, public)
values ('gallery', 'gallery', true)
on conflict (id) do nothing;

create policy "Gallery photos are publicly viewable"
on storage.objects for select
using (bucket_id = 'gallery');

create policy "Authenticated users upload to own folder in gallery"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'gallery'
  and auth.uid()::text = (storage.foldername(name))[1]
);

create policy "Users can delete their own gallery uploads"
on storage.objects for delete
to authenticated
using (
  bucket_id = 'gallery'
  and auth.uid()::text = (storage.foldername(name))[1]
);

-- Reports: allow host team to read & update reports targeting their events/photos
create or replace function public.is_report_for_host_team(_target_type text, _target_id uuid, _user_id uuid)
returns boolean
language sql
stable security definer
set search_path = public
as $$
  select case
    when _target_type = 'event' then exists (
      select 1 from public.events e
      join public.host_members hm on hm.host_id = e.host_id
      where e.id = _target_id and hm.user_id = _user_id
    )
    when _target_type = 'gallery_photo' then exists (
      select 1 from public.gallery_photos g
      join public.events e on e.id = g.event_id
      join public.host_members hm on hm.host_id = e.host_id
      where g.id = _target_id and hm.user_id = _user_id
    )
    else false
  end;
$$;

create policy "Host team reads reports about their content"
on public.reports for select
using (public.is_report_for_host_team(target_type, target_id, auth.uid()));

create policy "Host team updates reports about their content"
on public.reports for update
using (public.is_report_for_host_team(target_type, target_id, auth.uid()));
