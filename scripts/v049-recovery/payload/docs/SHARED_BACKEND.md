# 午後三時、夏の果。 — Shared World Core Integration

更新: 2026-09-26 / β 0.49

## Source of Truth

共通仕様の正本は `keisasaki3/keisasaki3.github.io/shared-world-core/`。

- `docs/ARCHITECTURE.md`
- `docs/AUTH.md`
- `docs/DATABASE.md`
- `supabase/migrations/001_initial_schema.sql`
- `supabase/seed.sql`

この文書は夏の果側の接続・責務だけを記載する。

## 実装ファイル

### client

`client/src/shared-backend.ts`

- Supabase browser clientの生成
- session取得
- Google OAuth
- Email/Password login・signup
- `profiles` 読み書き
- `races` 読み込み
- `player_presence` 初期値読み書き

クライアントが持つのはpublishable/anon keyだけ。

`client/src/main.ts`

- Shared AuthログインUI
- race未設定時の選択
- display_name/statusの共通値反映
- access tokenをWebSocket joinへ付与
- status表示・変更
- reconnect時に現在位置をjoin resumeとして送信

### server

`server/shared-backend.js`

- server-only Supabase client
- access token検証
- profile/race/presence/state読み込み
- presence更新
- durable Summer End state保存

`server/server.js`

- authenticated player idを `auth.users.id` に固定
- clientのname/raceを認証モードでは信用しない
- live movementは従来どおりWebSocket authoritative
- 15秒throttle/map transition/logout/disconnectでdurable state保存
- duplicate accountはnew socket wins

## Login flow

1. clientがSupabase sessionを取得する。
2. 未認証ならGoogleまたはEmail/Passwordでログインする。
3. `profiles` を取得する。trigger遅延などで存在しない場合はown-row upsert fallbackを使用する。
4. `races` を取得し、現行sprite対応raceだけを候補にする。
5. `profiles.race_id IS NULL` の場合だけ種族選択を要求する。
6. display_name/race/statusを共通DBへ保存する。
7. WebSocket joinに `accessToken` を添付する。
8. serverが `auth.getUser(accessToken)` を実行して user idを確定する。
9. serverが `profiles / races / player_presence / summer_end_player_state` をservice roleで読み、playerを構成する。
10. welcome後は従来WebSocketゲームへ入る。

## Identity authority

認証モード:

- `player.id`: Supabase `auth.users.id`
- `player.name`: `profiles.display_name`
- `player.race`: `profiles.race_id`
- `player.status`: `player_presence.status`
- `height`: 1.0固定
- `color`: 現行固定値

client join packet内の `name / race / height / color` は互換モード用であり、認証モードの権威値にはしない。

## Position persistence

DB table: `summer_end_player_state`

WebSocketのmove packetがライブ位置の正本。DBはdurable snapshotだけ。

serverはplayer stateにdirty/revisionを持ち、通常moveではメモリ更新だけを行う。dirty stateは約15秒以上の間隔で保存する。保存中にさらにmoveが来た場合、revisionが変化していればdirtyを残す。

即時保存:

- map transition
- logout
- disconnect（ベストエフォート）

### Reconnect priority

clientの同一ページ内reconnectは `resume: true` と現在の `map/x/y/direction` を送る。serverはこれをDB snapshotより優先する。

fresh page/loginは `resume: false` なのでDB stateを復元する。

同一accountの別socketがすでにliveなら、new socketをactiveにしたうえで旧socketを閉じる。new socketがresume位置を持たない場合は旧live位置を引き継ぎ、DB巻き戻りを避ける。

## Presence

status:

- studying / 勉強中
- reading / 読書中
- busy / 取り込み中
- afk / AFK

OPTIONSの変更は `{type:"status"}` でserverへ送り、serverがDB保存後、同一マップへ `presence_update` を配信する。

heartbeat時には一定間隔で `last_seen_at` をtouchする。online/offlineそのものは固定statusとしてDB保存しない。

## Existing WebSocket behavior preserved

- 12秒 client heartbeat
- 25秒 protocol ping
- heartbeat ackの同一マップsnapshot
- 1/2/4/8秒 reconnect
- map scoped join/move/chat/leave
- map transition
- character animation
- player Y-sort

## Compatibility mode

以下が未設定なら共有バックエンドを無効化できる。

Client:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY` または `VITE_SUPABASE_ANON_KEY`

Server:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

両側未設定のローカル環境ではlegacy login + legacy WebSocket IDで従来ゲームを継続する。

## Security

- `SUPABASE_SERVICE_ROLE_KEY` はserver processだけ。
- `VITE_` prefixをservice roleに付けない。
- `.env` をGitへcommitしない。
- serverはaccess tokenからuser idを取得し、client指定user idを使わない。
- service role値をログへ出さない。

## Production activation

コード側はβ0.49で統合済み。Render等へは次の環境変数を安全なsecret/environment設定として登録する必要がある。

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Google OAuthを使う場合はSupabase Auth側でGoogle providerとproduction redirect URLも設定する。
