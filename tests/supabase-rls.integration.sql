-- Run as a privileged SQL editor user against a disposable/test project.
-- All users and data created by this test are rolled back.
begin;
do $test$
declare
  a uuid := gen_random_uuid(); b uuid := gen_random_uuid(); snap uuid := gen_random_uuid(); visible integer; denied boolean := false;
begin
  insert into auth.users (id, email, aud, role) values
    (a, 'prometheus-rls-' || a::text || '@example.invalid', 'authenticated', 'authenticated'),
    (b, 'prometheus-rls-' || b::text || '@example.invalid', 'authenticated', 'authenticated');
  perform set_config('role', 'authenticated', true);
  perform set_config('request.jwt.claim.sub', a::text, true);
  insert into public.memories(user_id, content) values (a, 'test memory');
  perform public.save_conversation_snapshot(snap, 'test', '[{"role":"user","content":"test"}]'::jsonb);
  select count(*) into visible from public.messages where conversation_id = snap;
  if visible <> 1 then raise exception 'Owner cannot read snapshot'; end if;
  perform set_config('request.jwt.claim.sub', b::text, true);
  select count(*) into visible from public.memories where user_id = a;
  if visible <> 0 then raise exception 'Another user can read memory'; end if;
  select count(*) into visible from public.messages where conversation_id = snap;
  if visible <> 0 then raise exception 'Another user can read messages'; end if;
  begin
    insert into public.memories(user_id, content) values (a, 'unauthorized');
  exception when insufficient_privilege then denied := true;
  end;
  if not denied then raise exception 'Another user can write memory'; end if;
  perform set_config('role', 'none', true);
end
$test$;
rollback;
