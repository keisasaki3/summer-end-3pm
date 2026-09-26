# 午後三時、夏の果。 — Implementation Handoff

更新: 2026-09-26 / β 0.50

## Read first

1. `SPEC.md`
2. `CHARACTER_SPRITE_SPEC.md`
3. `docs/SHARED_BACKEND.md`
4. Shared World Core: `keisasaki3/keisasaki3.github.io/shared-world-core/`

共通DB/Authの仕様はShared World Core側を優先する。

## Runtime architecture

- Phaser 3 / TypeScript / Vite client
- Node.js + raw `ws` server
- Supabase Auth + Postgres for shared identity and durable state
- realtime movement authority remains WebSocket server

## Critical invariants

- service role key never enters client/Vite
- authenticated player id comes from verified access token
- client name/race are not authoritative in auth mode
- no per-player avatar customization; race fully determines appearance
- do not write coordinates to Supabase per frame/move packet
- reconnect with an existing local player must prefer client live location over old DB snapshot
- keep 12s heartbeat, 25s ping, authoritative heartbeat snapshot, 1/2/4/8 reconnect
- duplicate account: newest socket wins
- preserve 3 current maps, chat and Y-sort
- quiz remains disabled

## Files

- `client/src/main.ts` — gameplay + auth/profile UI + WS client
- `client/src/shared-backend.ts` — browser Supabase helper
- `client/src/player-depth.ts` — feet-Y depth sorting
- `server/server.js` — realtime server + persistence scheduling
- `server/shared-backend.js` — server-only Supabase access
- `.env.example` — variable names only

## Durable state policy

- immediate: map transition / logout
- best effort: disconnect
- normal movement: ~15s throttled snapshot
- live authoritative: server memory / WebSocket

## Validation before release

Run:

```bash
npm install
npm run validate:sprites
npm run build
node --check server/server.js
node --check server/shared-backend.js
```

Then verify no service-role string/value exists under `client/` or generated `dist/`.

Test two authenticated browsers, reconnect, heartbeat longevity, map transition, chat, status and saved-position restore.
