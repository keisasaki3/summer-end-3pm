# 午後三時、夏の果。 — Shared Backend Integration

更新日: 2026-09-26

## 目的

人生クエストと同一のSupabase Auth / Shared World Coreを利用し、同じ利用者を同じプレイヤーとして扱う。

## 共通データ

- auth.users.id
- profiles.display_name
- profiles.race_id
- races master
- player_presence

キャラクター外見カスタマイズは持たない。race_idだけで見た目が決まる。

現行race-id:

- `teddy`
- `ancient-robot`
- `rabbit-jk`

## 夏の果固有データ

`summer_end_player_state`

- user_id
- map_id
- x
- y
- direction
- updated_at

このテーブルは再ログイン・再接続用の永続スナップショットであり、リアルタイム移動のauthoritative stateにはしない。

## Realtime architecture

既存WebSocket serverをリアルタイム位置のauthoritative sourceとして維持する。

DBへ毎フレーム位置を書き込まない。

推奨保存:

- map transition
- graceful disconnect / logout
- 15秒程度のthrottled snapshot

既存heartbeat / ping / reconnect機構は維持する。

再接続時:

1. Supabase sessionからuser_idを取得
2. 永続 `summer_end_player_state` を取得
3. WebSocketへuser_id / map / x / y / raceを送る
4. server側で現在接続中stateを再構築

## Presence status

共通表示ステータス:

- `studying` = 勉強中
- `reading` = 読書中
- `busy` = 取り込み中
- `afk` = AFK

`online/offline` はstatus値ではなく、WebSocket接続状態と `last_seen_at` から判定する。

## Player identity

現在のランダム/一時プレイヤー識別が存在する場合、認証導入後は `auth.users.id` を永続識別子にする。

表示名・raceはクライアント任意値を信頼せず、可能な範囲でSupabase profileを正本にする。

## Security

- client: Supabase anon/publishable key
- server: Supabase service role key
- service role keyをclient bundleへ入れない
- clientから他人の永続座標を直接SELECTさせない
- 他プレイヤー位置は既存WebSocket presence snapshot経由で表示する

## Canonical shared schema

共通DBの正本:

`keisasaki3/keisasaki3.github.io/shared-world-core/`

特に:

- `docs/AUTH.md`
- `docs/DATABASE.md`
- `supabase/migrations/001_initial_schema.sql`
- `supabase/seed.sql`

## Implementation phases

### Phase 1

- Supabase client/server設定
- login UI
- profile取得
- race選択

### Phase 2

- WebSocket identityをuser_idへ統合
- persistent position load/save
- reconnect復帰

### Phase 3

- shared presence status表示
- 人生クエストとの共通display_name/race動作確認

## Documentation rule

実装時は `SPEC.md` と本書を同時に更新する。
