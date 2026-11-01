-- Snapshots are append-only via the RPC. Retrying the same ID is idempotent.
alter table public.messages add column position integer;
create unique index messages_conversation_position_idx on public.messages(conversation_id, position) where position is not null;

create or replace function public.save_conversation_snapshot(snapshot_id uuid, snapshot_title text, snapshot_messages jsonb)
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare
  actor uuid := auth.uid();
  item jsonb;
  idx integer := 0;
begin
  if actor is null then raise exception 'Authentication required'; end if;
  if snapshot_id is null or snapshot_title is null or length(trim(snapshot_title)) = 0 or length(snapshot_title) > 200 then
    raise exception 'Invalid title';
  end if;
  if jsonb_typeof(snapshot_messages) is distinct from 'array' or jsonb_array_length(snapshot_messages) not between 1 and 200 then
    raise exception 'Invalid messages';
  end if;
  for item in select value from jsonb_array_elements(snapshot_messages) loop
    if jsonb_typeof(item) is distinct from 'object' or item->>'role' is null or item->>'role' not in ('user','assistant')
      or jsonb_typeof(item->'content') is distinct from 'string' or length(trim(item->>'content')) = 0 or length(item->>'content') > 100000 then
      raise exception 'Invalid message';
    end if;
  end loop;
  -- An existing snapshot owned by this account is never overwritten on retry.
  if exists (select 1 from public.conversations where id = snapshot_id and user_id = actor) then return snapshot_id; end if;
  insert into public.conversations(id, user_id, title) values(snapshot_id, actor, snapshot_title);
  for item in select value from jsonb_array_elements(snapshot_messages) loop
    insert into public.messages(user_id, conversation_id, role, content, position)
      values(actor, snapshot_id, item->>'role', item->>'content', idx);
    idx := idx + 1;
  end loop;
  return snapshot_id;
end;
$$;
revoke all on function public.save_conversation_snapshot(uuid,text,jsonb) from public;
grant execute on function public.save_conversation_snapshot(uuid,text,jsonb) to authenticated;
