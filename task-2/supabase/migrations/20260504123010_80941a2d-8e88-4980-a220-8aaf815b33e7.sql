
-- PROFILES
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at timestamptz not null default now()
);
alter table public.profiles enable row level security;

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', new.email));
  return new;
end;
$$;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- HOSTS
create table public.hosts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles(id) on delete cascade,
  name text not null,
  logo_url text,
  bio text,
  contact_email text,
  slug text unique not null,
  created_at timestamptz not null default now()
);
alter table public.hosts enable row level security;

-- HOST MEMBERS
create table public.host_members (
  id uuid primary key default gen_random_uuid(),
  host_id uuid not null references public.hosts(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('host','checker')),
  invited_at timestamptz not null default now(),
  accepted_at timestamptz,
  unique (host_id, user_id)
);
alter table public.host_members enable row level security;

-- HOST INVITE TOKENS
create table public.host_invite_tokens (
  id uuid primary key default gen_random_uuid(),
  host_id uuid not null references public.hosts(id) on delete cascade,
  role text not null check (role in ('host','checker')),
  token uuid unique not null default gen_random_uuid(),
  expires_at timestamptz,
  created_at timestamptz not null default now()
);
alter table public.host_invite_tokens enable row level security;

-- EVENTS
create table public.events (
  id uuid primary key default gen_random_uuid(),
  host_id uuid not null references public.hosts(id) on delete cascade,
  title text not null,
  description text,
  start_at timestamptz not null,
  end_at timestamptz not null,
  timezone text not null,
  venue_address text,
  online_link text,
  capacity integer not null,
  cover_image_url text,
  visibility text not null default 'public' check (visibility in ('public','unlisted')),
  status text not null default 'draft' check (status in ('draft','published')),
  pricing_type text not null default 'free' check (pricing_type in ('free','paid')),
  created_at timestamptz not null default now()
);
alter table public.events enable row level security;
create index events_status_visibility_start on public.events (status, visibility, start_at);
create index events_host_id_idx on public.events (host_id);

-- RSVPS
create table public.rsvps (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  status text not null check (status in ('confirmed','waitlist','cancelled')),
  waitlist_position integer,
  created_at timestamptz not null default now(),
  unique (event_id, user_id)
);
alter table public.rsvps enable row level security;
create index rsvps_event_status_idx on public.rsvps (event_id, status);
create index rsvps_user_idx on public.rsvps (user_id);

-- TICKETS
create table public.tickets (
  id uuid primary key default gen_random_uuid(),
  rsvp_id uuid not null references public.rsvps(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_id uuid not null references public.events(id) on delete cascade,
  ticket_code uuid unique not null default gen_random_uuid(),
  created_at timestamptz not null default now()
);
alter table public.tickets enable row level security;
create index tickets_ticket_code_idx on public.tickets (ticket_code);

-- CHECK-INS
create table public.check_ins (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid not null references public.tickets(id) on delete cascade,
  event_id uuid not null references public.events(id) on delete cascade,
  checked_in_by uuid not null references public.profiles(id),
  checked_in_at timestamptz not null default now(),
  undone boolean not null default false
);
alter table public.check_ins enable row level security;
create index check_ins_ticket_active_idx on public.check_ins (ticket_id) where undone = false;

-- FEEDBACK
create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  rating integer not null check (rating between 1 and 5),
  comment text,
  created_at timestamptz not null default now(),
  unique (event_id, user_id)
);
alter table public.feedback enable row level security;

-- GALLERY PHOTOS
create table public.gallery_photos (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  uploaded_by uuid not null references public.profiles(id) on delete cascade,
  storage_path text not null,
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now()
);
alter table public.gallery_photos enable row level security;

-- REPORTS
create table public.reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid not null references public.profiles(id) on delete cascade,
  target_type text not null check (target_type in ('event','photo')),
  target_id uuid not null,
  reason text,
  status text not null default 'pending' check (status in ('pending','hidden','resolved')),
  created_at timestamptz not null default now()
);
alter table public.reports enable row level security;

-- NOTIFICATIONS
create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type text not null,
  payload jsonb,
  read boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.notifications enable row level security;

-- =========================
-- SECURITY DEFINER HELPERS
-- =========================
create or replace function public.is_host_member(_host_id uuid, _user_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.host_members where host_id = _host_id and user_id = _user_id);
$$;

create or replace function public.has_host_role(_host_id uuid, _user_id uuid, _role text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.host_members where host_id = _host_id and user_id = _user_id and role = _role);
$$;

create or replace function public.is_host_team_for_event(_event_id uuid, _user_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.events e
    join public.host_members hm on hm.host_id = e.host_id
    where e.id = _event_id and hm.user_id = _user_id
  );
$$;

create or replace function public.has_event_host_role(_event_id uuid, _user_id uuid, _role text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.events e
    join public.host_members hm on hm.host_id = e.host_id
    where e.id = _event_id and hm.user_id = _user_id and hm.role = _role
  );
$$;

-- =========================
-- POLICIES
-- =========================

-- profiles
create policy "Profiles viewable by everyone" on public.profiles for select using (true);
create policy "Users insert own profile" on public.profiles for insert with check (auth.uid() = id);
create policy "Users update own profile" on public.profiles for update using (auth.uid() = id);

-- hosts
create policy "Hosts viewable by everyone" on public.hosts for select using (true);
create policy "Owners insert hosts" on public.hosts for insert with check (auth.uid() = owner_id);
create policy "Owners update hosts" on public.hosts for update using (auth.uid() = owner_id);

-- host_members
create policy "Members read own/team membership" on public.host_members for select
  using (user_id = auth.uid() or public.is_host_member(host_id, auth.uid()));
create policy "Authenticated insert memberships" on public.host_members for insert to authenticated with check (true);

-- host_invite_tokens
create policy "Host members view invite tokens" on public.host_invite_tokens for select
  using (public.is_host_member(host_id, auth.uid()));
create policy "Host role creates invite tokens" on public.host_invite_tokens for insert
  with check (public.has_host_role(host_id, auth.uid(), 'host'));

-- events
create policy "Published or team-readable events" on public.events for select
  using (status = 'published' or public.is_host_member(host_id, auth.uid()));
create policy "Host role inserts events" on public.events for insert
  with check (public.has_host_role(host_id, auth.uid(), 'host'));
create policy "Host role updates events" on public.events for update
  using (public.has_host_role(host_id, auth.uid(), 'host'));

-- rsvps
create policy "RSVP owner or host team reads" on public.rsvps for select
  using (user_id = auth.uid() or public.is_host_team_for_event(event_id, auth.uid()));
create policy "Authenticated rsvps" on public.rsvps for insert to authenticated with check (user_id = auth.uid());
create policy "Owner updates own rsvp" on public.rsvps for update using (user_id = auth.uid());

-- tickets
create policy "Ticket owner or host team reads" on public.tickets for select
  using (user_id = auth.uid() or public.is_host_team_for_event(event_id, auth.uid()));
create policy "Authenticated insert tickets" on public.tickets for insert to authenticated with check (user_id = auth.uid());

-- check_ins
create policy "Host team reads check-ins" on public.check_ins for select
  using (public.is_host_team_for_event(event_id, auth.uid()));
create policy "Host team inserts check-ins" on public.check_ins for insert
  with check (public.is_host_team_for_event(event_id, auth.uid()));
create policy "Host team updates check-ins" on public.check_ins for update
  using (public.is_host_team_for_event(event_id, auth.uid()));

-- feedback
create policy "Feedback readable by author or host team" on public.feedback for select
  using (user_id = auth.uid() or public.is_host_team_for_event(event_id, auth.uid()));
create policy "Authenticated submits feedback" on public.feedback for insert to authenticated with check (user_id = auth.uid());
create policy "Author updates own feedback" on public.feedback for update using (user_id = auth.uid());

-- gallery_photos
create policy "Approved photos public; uploader/host see all" on public.gallery_photos for select
  using (status = 'approved' or uploaded_by = auth.uid() or public.is_host_team_for_event(event_id, auth.uid()));
create policy "Authenticated upload photos" on public.gallery_photos for insert to authenticated with check (uploaded_by = auth.uid());
create policy "Host role updates photo status" on public.gallery_photos for update
  using (public.has_event_host_role(event_id, auth.uid(), 'host'));

-- reports
create policy "Reporter reads own reports" on public.reports for select using (reporter_id = auth.uid());
create policy "Authenticated creates reports" on public.reports for insert to authenticated with check (reporter_id = auth.uid());

-- notifications
create policy "Owner reads notifications" on public.notifications for select using (user_id = auth.uid());
create policy "Owner updates notifications" on public.notifications for update using (user_id = auth.uid());
