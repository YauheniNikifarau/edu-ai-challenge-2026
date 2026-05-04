ALTER TABLE public.check_ins REPLICA IDENTITY FULL;
ALTER PUBLICATION supabase_realtime ADD TABLE public.check_ins;