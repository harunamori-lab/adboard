-- 広告ボード v2 追加権限（解決・リアクション・削除を有効化）
-- Supabase SQL Editor に貼って Run。※画像アップは無くても既に動きます。
create policy "anon update comments" on board_comments for update using (true) with check (true);
create policy "anon delete comments" on board_comments for delete using (true);
