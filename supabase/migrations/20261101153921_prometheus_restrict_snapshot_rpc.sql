-- Supabase default privileges may explicitly grant EXECUTE to anon.
revoke all on function public.save_conversation_snapshot(uuid,text,jsonb) from anon;
revoke all on function public.save_conversation_snapshot(uuid,text,jsonb) from public;
grant execute on function public.save_conversation_snapshot(uuid,text,jsonb) to authenticated;
