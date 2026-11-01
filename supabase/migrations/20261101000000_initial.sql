-- Each row belongs to an authenticated user. No service-role key is used by the client.
create extension if not exists pgcrypto;
create table public.profiles (id uuid primary key references auth.users(id) on delete cascade, display_name text, created_at timestamptz not null default now());
create table public.conversations (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, title text not null, created_at timestamptz not null default now());
create table public.messages (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, conversation_id uuid not null references public.conversations(id) on delete cascade, role text not null check (role in ('user','assistant')), content text not null, created_at timestamptz not null default now());
create table public.memories (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, content text not null, created_at timestamptz not null default now());
create table public.user_preferences (user_id uuid primary key references auth.users(id) on delete cascade, settings jsonb not null default '{}', updated_at timestamptz not null default now());
create table public.tasks (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, title text not null, status text not null default 'pending', details jsonb not null default '{}', created_at timestamptz not null default now());
create table public.research_reports (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, title text not null, content text not null, created_at timestamptz not null default now());
create table public.devices (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade, name text not null, last_seen timestamptz not null default now());
create index memories_user_created_idx on public.memories(user_id, created_at desc);
create index messages_conversation_idx on public.messages(conversation_id, created_at);
-- Child ownership must match the parent even when a client supplies an arbitrary conversation id.
alter table public.conversations add constraint conversations_id_user_unique unique (id,user_id);
alter table public.messages add constraint messages_owner_parent_fk foreign key (conversation_id,user_id) references public.conversations(id,user_id) on delete cascade;
do $$ declare t text; begin
  foreach t in array array['conversations','messages','memories','user_preferences','tasks','research_reports','devices'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy own_rows on public.%I for all to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id)', t);
  end loop;
end $$;
alter table public.profiles enable row level security;
create policy own_profile on public.profiles for all to authenticated using (auth.uid() = id) with check (auth.uid() = id);
