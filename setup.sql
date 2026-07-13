-- ANNA DIAMOND 広告ボード テーブル作成（Supabase SQL Editorに貼って実行）
create table if not exists board_members (
  id serial primary key,
  name text not null unique,
  pin text not null
);

create table if not exists board_posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  week text,
  sections jsonb not null default '[]',
  created_at timestamptz not null default now()
);

create table if not exists board_comments (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references board_posts(id) on delete cascade,
  section_id text not null,
  author text not null,
  body text not null,
  created_at timestamptz not null default now()
);

alter table board_members enable row level security;
alter table board_posts enable row level security;
alter table board_comments enable row level security;

create policy "anon read members" on board_members for select using (true);
create policy "anon read posts" on board_posts for select using (true);
create policy "anon insert posts" on board_posts for insert with check (true);
create policy "anon read comments" on board_comments for select using (true);
create policy "anon insert comments" on board_comments for insert with check (true);

insert into board_members (name, pin) values
  ('はるな', '3172'),
  ('けんと', '8254'),
  ('あんな', '6091'),
  ('はるな（個人）', '4437')
on conflict (name) do nothing;
