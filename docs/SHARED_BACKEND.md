# 午後三時、夏の果。 — Shared Backend Integration

更新日: 2026-09-26
実装バージョン: β0.49

## Source of Truth
共通仕様の正本:

`keisasaki3/keisasaki3.github.io/shared-world-core/`

特に:
- `docs/ARCHITECTURE.md`
- `docs/AUTH.md`
- `docs/DATABASE.md`
- `supabase/migrations/001_initial_schema.sql`
- `supabase/seed.sql`

本書は「午後三時、夏の果。」側でその共通仕様をどう利用するかを記載する。

## 実装状態
β0.49でアプリ側integrationを実装済み。

実装済み:
- Supabase JS client
- Google OAuth
- Email / Password sign-in + sign-up
- `profiles.display_name` 読込/保存
- `profiles.race_id` 読込/保存
- race未設定時の種族選択
- `races` master読込
- `player_presence.status` 読込/変更/表示
- WebSocket join時のaccess token送信
- server側 `auth.getUser(accessToken)` 検証
- verified `auth.users.id` をWebSocket player idに採用
- server側でprofile/raceを再取得しclient任意name/raceを信用しない
- `summer_end_player_state` load/save
- map / x / y / direction復元
- 15秒throttled durable save
- map transition即時save
- disconnect/logout save
- 12秒heartbeat / 25秒ping / presence snapshot / 1-2-4-8秒reconnect維持
- service role keyをserver envのみに限定

外部環境待ち:
- 共通Supabase projectの実project ref / keys
- migration/seed適用
- Google provider設定
- Render env設定
- 実アカウントを用いたE2E検証

## Authentication flow
1. Browserは `VITE_SUPABASE_URL` + publishable keyでSupabase clientを生成
2. 未ログインならGoogleまたはEmail/PasswordログインUIを表示
3. session確立後、`auth.users.id` を取得
4. `profiles` と `races` を読み込む
5. race_idがnullなら種族選択を要求
6. `player_presence` を読み込む
7. ゲーム開始時、WebSocket joinへ `accessToken` を渡す
8. serverはservice role clientの `auth.getUser(accessToken)` で検証
9. serverが得たuser.idをplayer idとし、clientからuser_idは受け取らない

Supabase Authのprofile auto-create triggerが遅延した場合に備え、clientは数回待機後、自分自身のprofileだけRLS下でupsertできるfallbackを持つ。

## Profile / race
共通データ:
- `auth.users.id`
- `profiles.display_name`
- `profiles.race_id`
- `races`

認証モードではserverがjoin時にprofile/raceをDBから再取得する。
client join payload内のlegacy name/race値は認証モードではauthoritativeではない。

外見はrace_idだけで決まる。
認証モードではheightを1.0固定にし、旧UIの個別身長カスタマイズを使用しない。

## Presence status
対応値:
- `studying` = 勉強中
- `reading` = 読書中
- `busy` = 取り込み中
- `afk` = AFK

処理:
- login時にclientが自分のstatusを読む
- WebSocket player snapshotにstatusを含める
- キャラクター名札にstatusを表示
- OPTIONSから変更可能
- status変更はWebSocket serverがservice roleで保存し、同一mapへ即時broadcast
- heartbeat時は30秒以上空いた場合だけ `last_seen_at` を更新

`online/offline` はstatus値として保存しない。

## Durable Summer End state
テーブル:
`summer_end_player_state`

保存:
- realtime moveごとにはDB writeしない
- moveでserver memory stateだけ更新しdirty flagを立てる
- 5秒timerでdirty playerを確認し、前回saveから15秒以上ならupsert
- map transitionは即時upsert
- current socketのdisconnect/logoutは即時upsert

保存列:
- `user_id`
- `map_id`
- `x`
- `y`
- `direction`

復元:
- page reload / fresh login: DB stateをserverがload
- WebSocket reconnect: browser内にplayer objectが残っている場合はjoinに `resume=true` と現在位置を送り、serverは同じverified userのcurrent client positionを優先

これにより15秒throttleによる位置巻き戻りを避ける。

## Realtime architecture
リアルタイム位置のauthoritative sourceは引き続きNode/ws server。

維持されるもの:
- 12秒client heartbeat
- heartbeat ack内map snapshot
- 25秒server ping/pong
- 1/2/4/8秒reconnect
- map-scoped join/move/chat/leave
- client-authoritative movement + server memory presence

Supabaseはidentity/shared profile/shared status/durable snapshotを担当し、毎frame realtime movementは担当しない。

## Duplicate login
`auth.users.id` が永続WebSocket idになるため、同一accountの重複接続は1 connectionに制限する。
新しいsocketが認証されたら古いsocketをcloseし、新しいsocketをcurrent connectionとして採用する。
古いsocketのclose handlerは新しいplayer stateを削除・上書きしない。

## Security
Client bundleに許可:
- `VITE_SUPABASE_URL`
- publishable/anon key

Server only:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

禁止:
- `SUPABASE_SERVICE_ROLE_KEY` を `VITE_` prefixへ入れる
- source codeへsecret直書き
- clientがuser_idを自己申告してserverが信用する設計
- 他人の `summer_end_player_state` をclientが直接読む設計

## Environment variables
`.env.example` 参照。

Renderではbuild-time VITE変数とserver runtime変数を同一Web Serviceへ設定する。

## Compatibility mode
Supabase project未設定の開発/移行期間に既存ゲームを停止させないため、4変数が未設定ならlegacy compatibility modeへfallbackする。

legacy mode:
- random session id
- 既存WebSocket / heartbeat / map移動は動作
- client-supplied user_idはそもそも受け付けない
- shared profile/state persistenceは無効

本番のShared World Core要件を満たすのはSupabase env設定済みmodeのみ。

## Verification status
静的/ビルドで確認するもの:
- server JS syntax
- client TS transpile
- sprite validation
- Vite build
- built client bundleに `SUPABASE_SERVICE_ROLE_KEY` 文字列/secret値がないこと
- existing heartbeat/ping/reconnect codeが残ること

実Supabase projectが必要なE2E:
- 同一accountで同じprofile
- 別browserで同じdisplay_name/race
- map/x/y/direction復元
- 2 user同時接続
- heartbeat継続後も他player表示維持
- reconnect復帰

現時点のconnectorでは利用可能なSupabase projectが0件のため、上記E2Eはproject provision後に実施する。
