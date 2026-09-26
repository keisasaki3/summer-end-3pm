import fs from "node:fs";

const main=fs.readFileSync("client/src/main.ts","utf8");
const shared=fs.readFileSync("client/src/shared-backend.ts","utf8");
const server=fs.readFileSync("server/server.js","utf8");
const serverShared=fs.readFileSync("server/shared-backend.js","utf8");
const depth=fs.readFileSync("client/src/player-depth.ts","utf8");
const pkg=JSON.parse(fs.readFileSync("package.json","utf8"));

const checks={
  supabase_dependency:Boolean(pkg.dependencies?.["@supabase/supabase-js"]),
  google_oauth:shared.includes('provider: "google"'),
  email_password:shared.includes("signInWithPassword") && shared.includes("auth.signUp"),
  auth_token_join:main.includes("accessToken,") && server.includes("verifyAccessToken(msg.accessToken)"),
  stable_auth_id:server.includes("player.id = user.id"),
  server_profile_authority:server.includes("player.name = String(bootstrap.profile.display_name") && server.includes("player.race = bootstrap.profile.race_id"),
  race_required:serverShared.includes("RACE_REQUIRED"),
  statuses:["studying","reading","busy","afk"].every(x=>main.includes(x) && serverShared.includes(x)),
  state_table:serverShared.includes('from("summer_end_player_state")'),
  no_client_state_writes:!shared.includes('summer_end_player_state'),
  snapshot_15s:server.includes("PLAYER_SNAPSHOT_INTERVAL_MS = 15000"),
  reconnect_resume:main.includes("resume:Boolean(this.me)") && server.includes("const resumeFromClient = Boolean(msg.resume)"),
  duplicate_new_wins:server.includes("activeSockets.set(player.id, socket)") && server.includes('oldSocket.close(4000, "replaced by newer connection")'),
  client_heartbeat_12s:main.includes("window.setInterval(send,12000)"),
  server_ping_25s:server.includes("},25000)"),
  heartbeat_snapshot:server.includes('type:"heartbeat_ack"') && server.includes("players:visiblePlayers(player.map, player.id)"),
  reconnect_backoff:main.includes("1000*Math.pow(2,this.reconnectAttempts)") && main.includes(",8000"),
  all_maps:["yunagicho","komorebi","convenience"].every(x=>main.includes(x) && server.includes(x)),
  chat:/type\s*:\s*["']chat["']/.test(main) && /msg\.type\s*===\s*["']chat["']/.test(server),
  y_sort:depth.includes("players.sort((a, b)") && depth.includes("const dy = a.y - b.y") && depth.includes("a === localPlayer") && depth.includes("PLAYER_DEPTH_BASE + index * PLAYER_DEPTH_STEP"),
  service_role_server_only:serverShared.includes("SUPABASE_SERVICE_ROLE_KEY") && !main.includes("SUPABASE_SERVICE_ROLE_KEY") && !shared.includes("SUPABASE_SERVICE_ROLE_KEY"),
  fixed_height:server.includes("player.height = 1") && !main.includes('selectedHeight'),
  status_server_write:server.includes("setPresenceStatus(player.id, nextStatus)"),
  map_transition_save:server.includes("await persistPlayerState(player, true)"),
};
let failed=0;
for(const [name,ok] of Object.entries(checks)){
  console.log(`${ok?"PASS":"FAIL"} ${name}`);
  if(!ok)failed++;
}
if(failed)process.exit(1);
