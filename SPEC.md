# 午後三時、夏の果。 仕様書

## 正式ゲーム名
- 日本語正式名：**午後三時、夏の果。**
- 末尾の句点「。」までを正式名称に含む
- GitHub / Render の技術識別子：`summer-end-3pm`

## プロダクト
2Dオンライン空間。「世界を攻略するのではなく、世界に滞在する」。
戦闘を中心にせず、歩くこと・空間・他プレイヤーの気配を中心にする。

## 技術
- Phaser 3
- TypeScript
- Vite
- Node.js
- ws
- Supabase Auth / PostgreSQL（Shared World Core）
- Browser first

## 現行マップ
- 夕凪町
- 木漏れ日神社
- コンビニ

## プレイヤー種族
### テディぐま
- race-id: `teddy`
- move_speed: 168
- visual_scale: 1.0

### いにしえロボット
- race-id: `ancient-robot`
- move_speed: 176
- visual_scale: 1.0

### うさぎjk
- race-id: `rabbit-jk`
- move_speed: 168
- visual_scale: 1.0

種族マスタの正本はShared World Coreの `races`。クライアントはログイン時に `races` を読み込み、`sprite_key / visual_scale / move_speed` を使用する。
現行のスプライト規格は `CHARACTER_SPRITE_SPEC.md` を参照。

## キャラクター外見
- 共通人格の外見は `profiles.race_id` のみで決定する
- 同じrace-idは全プレイヤー同じ外見
- 個別の身長・髪・服・色などのアバターカスタマイズ値は持たない
- 認証モードではWebSocket serverが `height=1` / 固定色として扱い、client任意値を外見の正本にしない
- 重なり描画は足元Y座標でY-sortし、画面下側のキャラクターを前面に描画する

## キャラクターアセット運用
- 正式シート: `public/sprites/sheets/<race-id>.png`
- 原本: `public/sprites/source/<race-id>-original.png`
- ランタイム: `public/sprites/runtime/<race-id>/<direction>-<frame>.png`
- `npm run validate:sprites` で自動検品
- `npm run build` は検品成功後のみ実行

## 実装運用
1. GitHub上の仕様書を読む
2. TODOを読む
3. TODOに基づいて実装する
4. 実装・検証する
5. 完了したTODOを削除する
6. 実装後の状態に合わせて仕様書を更新する
7. `update.zip` と完全版ZIPを出力する

2026-09-26以降、GitHub上の仕様書をSource of Truthとする。ChatGPT上の会話は設計履歴であり、確定仕様と矛盾する場合はGitを優先する。

## 共通アカウント / Shared World Core
人生クエストと同じSupabase project / Shared World Coreを利用する。
共通仕様の正本は `keisasaki3/keisasaki3.github.io/shared-world-core/`。

### Authentication
- Google OAuth
- Email + Password
- `auth.users.id` を永続プレイヤーIDとして使用
- clientは任意の `user_id` をWebSocketへ送信しない
- WebSocket接続時にclientはSupabase access tokenを送信する
- serverは `SUPABASE_SERVICE_ROLE_KEY` を用いてaccess tokenを検証し、検証済み `auth.users.id` からplayer idを決定する
- service role keyはserver専用。client bundleへ含めない

### Shared profile
- `profiles.display_name` = 共通表示名
- `profiles.race_id` = 共通種族
- race_id未設定時はゲーム参加前に種族選択を要求
- profile/raceはserver側でもDBから再取得し、WebSocket join payloadのname/raceを認証モードでは信用しない

### Shared presence
`player_presence.status`:
- `studying` / 勉強中
- `reading` / 読書中
- `busy` / 取り込み中
- `afk` / AFK

ステータスはキャラクター名札とOPTIONSに反映する。
serverはjoin/status変更時に保存し、heartbeat中は `last_seen_at` を間引いて更新する。

## 夏の果固有の永続状態
`summer_end_player_state`:
- `user_id`
- `map_id`
- `x`
- `y`
- `direction`
- `updated_at`

リアルタイム位置のauthoritative sourceは既存WebSocket serverのまま維持する。
Supabaseへ毎フレーム座標を書き込まない。

保存タイミング:
- 15秒程度のthrottled snapshot
- map transition
- 現在のauthenticated socketのdisconnect/logout

復元:
- ページ再読込/再ログインではDBの保存位置から復帰
- 一時的なWebSocket切断からの1/2/4/8秒reconnectではclient内の現在位置を優先して復帰し、DBの最大15秒古いsnapshotへの巻き戻りを防ぐ
- `direction` も保存/復元する

## オンライン接続 / Presence snapshot
既存機構を維持する。
- client: 12秒ごとのapplication heartbeat
- heartbeat response: 同一mapのauthoritative player snapshot
- server: 25秒ごとのWebSocket ping/pong
- reconnect: 1 / 2 / 4 / 8秒 backoff
- map-aware join/move/chat/leave
- heartbeat snapshotで取りこぼしたjoin/leaveを自己修復
- authenticated modeでは `auth.users.id` がWebSocket player id
- 同一accountの重複接続は新しいsocketを優先し、古いsocketを閉じる

## Supabase設定
Client build-time:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`（legacy anon keyの場合は `VITE_SUPABASE_ANON_KEY` も対応）

Server runtime:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

secret値はGitへcommitしない。`.env.example` は変数名のみを管理する。

4変数が未設定の場合は、既存ゲームを壊さないためlegacy compatibility modeで起動する。このモードではrandom session idを使用し、client-supplied user_idは受け付けない。共通バックエンドの本番要件を満たすのは4変数が設定されたSupabase modeのみ。

## クイズ
- 教養クイズ機能は現在一時停止中
- serverは出題timerを起動しない
- clientはクイズUIを生成しない

## マップ音響
- 旧BGM `Late Summer at the Pier` は削除済み
- 現在は全マップ無音
- 各mapは `audio.bgmKey` と `audio.ambienceKeys` を持つ
- 今後の環境音実装は `ambienceKeys` を使用する

## TODO
### Production activation
- 共通Supabase projectへ `shared-world-core/supabase/migrations/001_initial_schema.sql` と `seed.sql` を適用
- Google provider / redirect URLをSupabase側で設定
- Renderへ4つのSupabase環境変数を設定
- 実Supabase環境でcross-browser / persistence / multi-user E2E検証を完了する

コード実装自体はβ0.49で完了。上記は外部Supabase projectが用意された後のactivation/実環境検証項目。
