# Shared Backend Implementation Handoff

更新日: 2026-09-26

この文書は「午後三時、夏の果。」側で共通Auth/DB実装を開始するための引き継ぎ仕様。

## Before coding

必ず以下を読む。

1. `SPEC.md`
2. `CHARACTER_SPRITE_SPEC.md`
3. `docs/SHARED_BACKEND.md`
4. Shared World Core:
   - `keisasaki3/keisasaki3.github.io/shared-world-core/docs/ARCHITECTURE.md`
   - `.../docs/AUTH.md`
   - `.../docs/DATABASE.md`
   - `.../supabase/migrations/001_initial_schema.sql`
   - `.../supabase/seed.sql`

## Goal

既存ゲーム性・マップ・heartbeat・WebSocket再接続を壊さず、プレイヤー識別と永続状態だけを共通Supabaseへ接続する。

## Required behavior

### Authentication

- Supabase Authを導入
- Google OAuth + email/passwordを利用可能にする
- 未ログイン時はゲーム参加前にログイン
- `auth.users.id` を永続player IDとして使用

### Profile

- `profiles.display_name` を表示名に使用
- `profiles.race_id` を種族に使用
- race_id未設定なら種族選択を表示
- 種族ごとに全員同じ見た目
- 個別avatar customizationは追加しない

### Races

DBの `races` を正本とする。

現在:
- teddy
- ancient-robot
- rabbit-jk

sprite asset pathは既存規格を維持する。

### WebSocket

- WebSocket接続時に認証済みuser_idを扱えるようにする
- クライアントが任意の他人user_idを名乗れる設計にしない
- 可能ならSupabase access tokenをserverへ渡し、serverで検証してuser_idを決定する
- 既存heartbeat / ping / backoff reconnectを維持

### Persistent position

`summer_end_player_state` を利用する。

保存対象:
- map_id
- x
- y
- direction

DBへ毎フレーム書かない。

保存候補:
- 15秒程度のthrottle
- map transition
- disconnect/logout

ログイン後は保存位置があればそこから開始。無ければ現在の初期spawnを使用。

### Shared status

`player_presence.status`:
- studying
- reading
- busy
- afk

online/offlineはWebSocket接続/last_seenから判定する。

## Security

- clientへservice role keyを絶対に入れない
- serverのみservice roleを使用可
- browserにはpublishable/anon keyのみ
- 他人の `summer_end_player_state` をclientから直接取得しない
- 他プレイヤーのリアルタイム位置は既存WebSocket snapshot経由

## Environment variables

具体名は実装時に既存Render構成と合わせるが、概ね以下を想定する。

Client:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Server:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

secret値をGitへcommitしない。

## Verification

最低限:

1. Googleまたはemail loginできる
2. 同一アカウントで再ログインして同じprofileになる
3. race変更が永続化される
4. 別ブラウザでも同じrace/display_nameになる
5. map/座標が再ログイン後に復元される
6. 二人同時接続で既存presence表示が壊れない
7. 時間経過で他playerが消える既修正問題を再発させない
8. disconnect -> reconnectでその場復帰
9. service role keyがclient bundleに含まれない
10. `npm run build` と既存sprite validationが成功

## Documentation after implementation

- `SPEC.md` を実装後の状態へ更新
- `docs/SHARED_BACKEND.md` の未実装表現を更新
- TODOがある場合はGitに明記
- コードだけ変更して仕様書を放置しない
