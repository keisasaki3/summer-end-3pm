# Shared Backend Implementation Handoff

更新日: 2026-09-26

## Status
Shared World Core client/server integrationはβ0.49で実装済み。
次の担当者は新規実装ではなく、共通Supabase projectのactivationと実環境E2Eから開始する。

## Source of Truth
1. `SPEC.md`
2. `CHARACTER_SPRITE_SPEC.md`
3. `docs/SHARED_BACKEND.md`
4. `keisasaki3/keisasaki3.github.io/shared-world-core/`
   - `docs/ARCHITECTURE.md`
   - `docs/AUTH.md`
   - `docs/DATABASE.md`
   - `supabase/migrations/001_initial_schema.sql`
   - `supabase/seed.sql`

## Implemented files
- `client/src/shared-backend.ts`: Supabase browser client / auth / profile / races / presence
- `client/src/main.ts`: auth onboarding, shared profile, token-bearing WS join, status UI, direction sync
- `server/server.js`: access-token verification, profile/race authority, durable state persistence, shared presence
- `.env.example`: required env names

## Activation checklist
1. Shared Supabase projectを用意/接続
2. canonical migration `001_initial_schema.sql` を適用
3. `seed.sql` を適用
4. Google providerを有効化
5. Render URLをAuth redirect allow-listへ追加
6. Renderへ以下を設定
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_PUBLISHABLE_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
7. main branchを再deploy
8. E2E verificationを実施

## Non-regression requirements
変更時に以下を壊さない。
- 12秒heartbeat
- 25秒ping/pong
- heartbeat presence snapshot
- 1/2/4/8秒reconnect
- map transitions
- character rendering / Y-sort
- WebSocket realtime position authority
- sprite validation/build

DBへ毎frame positionを書かない。
service role keyをclientへ入れない。
