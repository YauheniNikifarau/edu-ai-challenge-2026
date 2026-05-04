
-- Create placeholder auth users (profiles auto-created via handle_new_user trigger if present;
-- otherwise insert profiles manually below)
INSERT INTO auth.users (id, instance_id, aud, role, email, encrypted_password, email_confirmed_at, created_at, updated_at, raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous)
VALUES
  ('44444444-4444-4444-4444-444444444444','00000000-0000-0000-0000-000000000000','authenticated','authenticated','owner@communityhub.example','',now(),now(),now(),'{"provider":"email","providers":["email"]}','{"display_name":"Hub Owner"}',false,false),
  ('11111111-1111-1111-1111-111111111111','00000000-0000-0000-0000-000000000000','authenticated','authenticated','alice@example.com','',now(),now(),now(),'{"provider":"email","providers":["email"]}','{"display_name":"Alice Demo"}',false,false),
  ('22222222-2222-2222-2222-222222222222','00000000-0000-0000-0000-000000000000','authenticated','authenticated','bob@example.com','',now(),now(),now(),'{"provider":"email","providers":["email"]}','{"display_name":"Bob Demo"}',false,false),
  ('33333333-3333-3333-3333-333333333333','00000000-0000-0000-0000-000000000000','authenticated','authenticated','carol@example.com','',now(),now(),now(),'{"provider":"email","providers":["email"]}','{"display_name":"Carol Demo"}',false,false)
ON CONFLICT (id) DO NOTHING;

-- Ensure profiles exist (in case trigger didn't run)
INSERT INTO public.profiles (id, display_name) VALUES
  ('44444444-4444-4444-4444-444444444444','Hub Owner'),
  ('11111111-1111-1111-1111-111111111111','Alice Demo'),
  ('22222222-2222-2222-2222-222222222222','Bob Demo'),
  ('33333333-3333-3333-3333-333333333333','Carol Demo')
ON CONFLICT (id) DO NOTHING;

-- Host
INSERT INTO public.hosts (id, owner_id, name, slug, bio, contact_email, logo_url) VALUES (
  'aaaaaaaa-0000-0000-0000-000000000001','44444444-4444-4444-4444-444444444444',
  'Community Hub','community-hub',
  'We organize free community events across the city.',
  'hello@communityhub.example',
  'https://picsum.photos/seed/communityhub/200/200'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO public.host_members (host_id, user_id, role, accepted_at)
VALUES ('aaaaaaaa-0000-0000-0000-000000000001','44444444-4444-4444-4444-444444444444','host', now())
ON CONFLICT DO NOTHING;

-- Events
INSERT INTO public.events (id, host_id, title, description, start_at, end_at, timezone, venue_address, capacity, visibility, status, pricing_type, cover_image_url) VALUES
('bbbbbbbb-0000-0000-0000-000000000001','aaaaaaaa-0000-0000-0000-000000000001',
 'Summer Networking Mixer',
 'Join us for an evening of networking, light refreshments, and great conversations. Open to everyone.',
 (date_trunc('day', now() + interval '30 days') + interval '22 hours'),
 (date_trunc('day', now() + interval '30 days') + interval '25 hours'),
 'America/New_York','123 Main Street, New York, NY 10001',50,'public','published','free',
 'https://picsum.photos/seed/mixer/1200/600'),
('bbbbbbbb-0000-0000-0000-000000000002','aaaaaaaa-0000-0000-0000-000000000001',
 'Spring Workshop: Intro to Public Speaking',
 'A hands-on workshop for beginners who want to build confidence speaking in front of groups.',
 (date_trunc('day', now() - interval '30 days') + interval '14 hours'),
 (date_trunc('day', now() - interval '30 days') + interval '17 hours'),
 'America/New_York','456 Oak Avenue, New York, NY 10002',30,'public','published','free',
 'https://picsum.photos/seed/workshop/1200/600')
ON CONFLICT (id) DO NOTHING;

-- RSVPs
INSERT INTO public.rsvps (id, event_id, user_id, status) VALUES
('cccccccc-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','11111111-1111-1111-1111-111111111111','confirmed'),
('cccccccc-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000002','22222222-2222-2222-2222-222222222222','confirmed'),
('cccccccc-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-000000000002','33333333-3333-3333-3333-333333333333','confirmed')
ON CONFLICT (id) DO NOTHING;

-- Tickets
INSERT INTO public.tickets (id, event_id, user_id, rsvp_id) VALUES
('dddddddd-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','11111111-1111-1111-1111-111111111111','cccccccc-0000-0000-0000-000000000001'),
('dddddddd-0000-0000-0000-000000000002','bbbbbbbb-0000-0000-0000-000000000002','22222222-2222-2222-2222-222222222222','cccccccc-0000-0000-0000-000000000002'),
('dddddddd-0000-0000-0000-000000000003','bbbbbbbb-0000-0000-0000-000000000002','33333333-3333-3333-3333-333333333333','cccccccc-0000-0000-0000-000000000003')
ON CONFLICT (id) DO NOTHING;

-- Check-in
INSERT INTO public.check_ins (id, event_id, ticket_id, checked_in_by, checked_in_at, undone) VALUES
('eeeeeeee-0000-0000-0000-000000000001','bbbbbbbb-0000-0000-0000-000000000002','dddddddd-0000-0000-0000-000000000001','44444444-4444-4444-4444-444444444444',
 (date_trunc('day', now() - interval '30 days') + interval '14 hours 15 minutes'), false)
ON CONFLICT (id) DO NOTHING;
