const http = require("http");
const { WebSocketServer, WebSocket } = require("ws");
const fs = require("fs");
const path = require("path");
const sharedBackend = require("./shared-backend");

const PORT = Number(process.env.PORT || 8080);
const DEV = process.argv.includes("--dev");
const players = new Map();
const activeSockets = new Map();

const PLAYER_SNAPSHOT_INTERVAL_MS = 15000;
const PRESENCE_TOUCH_INTERVAL_MS = 30000;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".wav": "audio/wav",
  ".mp3": "audio/mpeg",
};

function sendJson(socket, data) {
  if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data));
}

function broadcastMap(map, data, except) {
  const text = JSON.stringify(data);
  for (const client of wss.clients) {
    if (client === except || client.readyState !== WebSocket.OPEN) continue;
    const pid = client.playerId;
    if (!pid || activeSockets.get(pid) !== client) continue;
    const target = players.get(pid);
    if (target?.map === map) client.send(text);
  }
}

function normalizeMap(value, fallback = "yunagicho") {
  return value === "komorebi" || value === "convenience" || value === "yunagicho"
    ? value
    : fallback;
}

function normalizeDirection(value, fallback = "down") {
  return value === "up" || value === "left" || value === "right" || value === "down"
    ? value
    : fallback;
}

function clampX(value) {
  return Math.max(16, Math.min(1520, Number(value)));
}

function clampY(value) {
  return Math.max(16, Math.min(848, Number(value)));
}

function hasFinitePosition(value) {
  return Number.isFinite(value?.x) && Number.isFinite(value?.y);
}

function serializePlayer(player) {
  return {
    id: player.id,
    x: player.x,
    y: player.y,
    color: player.color,
    name: player.name,
    height: player.height,
    map: player.map,
    race: player.race,
    direction: player.direction,
    status: player.status,
  };
}

function visiblePlayers(map, excludeId) {
  return [...players.values()]
    .filter((player) => player.id !== excludeId && player.map === map)
    .map(serializePlayer);
}

function markStateDirty(player) {
  if (!player.authenticated) return;
  player.stateRevision += 1;
  player.stateDirty = true;
}

async function persistPlayerState(player, force = false) {
  if (!sharedBackend.enabled || !player.authenticated) return true;
  const now = Date.now();
  if (!force) {
    if (!player.stateDirty) return true;
    if (now - player.lastSavedAt < PLAYER_SNAPSHOT_INTERVAL_MS) return true;
  }

  if (player.stateSavePromise) {
    if (!force) return true;
    await player.stateSavePromise;
    if (!player.stateDirty) return true;
  }

  const revision = player.stateRevision;
  const snapshot = {
    map: player.map,
    x: player.x,
    y: player.y,
    direction: player.direction,
  };

  const run = (async () => {
    try {
      await sharedBackend.saveSummerState(player.id, snapshot);
      player.lastSavedAt = Date.now();
      if (player.stateRevision === revision) player.stateDirty = false;
      return true;
    } catch (error) {
      console.error("[shared-backend] state save failed", player.id, error);
      return false;
    }
  })();
  player.stateSavePromise = run;
  try {
    const result = await run;
    if (force && result && player.stateDirty && player.stateRevision !== revision) {
      player.stateSavePromise = null;
      return persistPlayerState(player, true);
    }
    return result;
  } finally {
    if (player.stateSavePromise === run) player.stateSavePromise = null;
  }
}

function touchPlayerPresence(player) {
  if (!sharedBackend.enabled || !player.authenticated) return;
  const now = Date.now();
  if (now - player.lastPresenceTouchAt < PRESENCE_TOUCH_INTERVAL_MS) return;
  player.lastPresenceTouchAt = now;
  void sharedBackend.touchPresence(player.id, player.status).catch((error) => {
    console.error("[shared-backend] presence touch failed", player.id, error);
  });
}

function serveStatic(req, res) {
  if (DEV) {
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("午後三時、夏の果て。 WebSocket dev server");
    return;
  }

  const dist = path.join(__dirname, "..", "dist");
  let urlPath;
  try {
    urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  } catch {
    res.writeHead(400);
    res.end("Bad Request");
    return;
  }
  let filePath = path.join(dist, urlPath === "/" ? "index.html" : urlPath);

  // Prevent traversal outside dist.
  const normalizedDist = path.resolve(dist);
  filePath = path.resolve(filePath);
  if (filePath !== normalizedDist && !filePath.startsWith(normalizedDist + path.sep)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  fs.stat(filePath, (err, stat) => {
    if (!err && stat.isFile()) {
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, {
        "Content-Type": MIME[ext] || "application/octet-stream",
        "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=3600",
      });
      fs.createReadStream(filePath).pipe(res);
      return;
    }

    // SPA fallback.
    const indexPath = path.join(dist, "index.html");
    fs.readFile(indexPath, (indexErr, data) => {
      if (indexErr) {
        res.writeHead(503, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Build not found. Run: npm run build");
        return;
      }
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" });
      res.end(data);
    });
  });
}

const server = http.createServer(serveStatic);
const wss = new WebSocketServer({ server, maxPayload: 16 * 1024 });

wss.on("connection", (socket) => {
  socket.isAlive = true;
  socket.on("pong",()=>{ socket.isAlive = true; });
  // 不正フレーム等のソケット単位のエラーでサーバー全体を落とさない（closeは別途発火する）。
  socket.on("error",(error)=>{ console.error("[ws] socket error", error?.code || error?.message || error); });

  const connectionId = Math.random().toString(36).slice(2, 10);
  let joined = false;
  let joining = false;
  socket.playerId = connectionId;

  const player = {
    id: connectionId,
    x: 820 + Math.floor(Math.random() * 80),
    y: 520 + Math.floor(Math.random() * 80),
    color: 0x60a5fa,
    name: "WALKER",
    height: 1,
    map: "yunagicho",
    race: "teddy",
    direction: "down",
    status: "afk",
    authenticated: false,
    stateDirty: false,
    stateRevision: 0,
    lastSavedAt: Date.now(),
    lastPresenceTouchAt: 0,
    stateSavePromise: null,
  };

  socket.on("message", async (raw) => {
    let msg;
    try {
      msg = JSON.parse(String(raw));
    } catch {
      return;
    }

    if (msg.type === "join" && !joined && !joining) {
      joining = true;
      try {
        if (sharedBackend.enabled) {
          const user = await sharedBackend.verifyAccessToken(msg.accessToken);
          const bootstrap = await sharedBackend.loadBootstrap(user.id);
          const previousPlayer = players.get(user.id);

          player.id = user.id;
          player.authenticated = true;
          player.name = String(bootstrap.profile.display_name || "名無し").slice(0, 20);
          player.race = bootstrap.profile.race_id;
          player.height = 1;
          player.color = 0x60a5fa;
          player.status = sharedBackend.normalizeStatus(bootstrap.status);
          player.direction = "down";

          const resumeFromClient = Boolean(msg.resume) && Number.isFinite(msg.x) && Number.isFinite(msg.y);
          if (resumeFromClient) {
            player.map = normalizeMap(msg.map, "yunagicho");
            player.x = clampX(msg.x);
            player.y = clampY(msg.y);
            player.direction = normalizeDirection(msg.direction, "down");
            markStateDirty(player);
          } else if (previousPlayer && previousPlayer.authenticated) {
            // New socket wins duplicate-account races without rolling the player
            // back to an older DB snapshot.
            player.map = normalizeMap(previousPlayer.map, "yunagicho");
            player.x = clampX(previousPlayer.x);
            player.y = clampY(previousPlayer.y);
            player.direction = normalizeDirection(previousPlayer.direction, "down");
            markStateDirty(player);
          } else if (bootstrap.state && hasFinitePosition(bootstrap.state)) {
            player.map = normalizeMap(bootstrap.state.map_id, "yunagicho");
            player.x = clampX(bootstrap.state.x);
            player.y = clampY(bootstrap.state.y);
            player.direction = normalizeDirection(bootstrap.state.direction, "down");
          }

          const oldSocket = activeSockets.get(player.id);
          socket.playerId = player.id;
          activeSockets.set(player.id, socket);
          players.set(player.id, player);
          joined = true;

          if (oldSocket && oldSocket !== socket) {
            oldSocket.superseded = true;
            try { oldSocket.close(4000, "replaced by newer connection"); } catch {}
          }

          touchPlayerPresence(player);
        } else {
          const name = typeof msg.name === "string" ? msg.name.trim().slice(0, 20) : "WALKER";
          player.name = name || "WALKER";
          player.color = 0x60a5fa;
          player.height = 1;
          player.map = normalizeMap(msg.map, "yunagicho");
          if (Number.isFinite(msg.x)) player.x = clampX(msg.x);
          if (Number.isFinite(msg.y)) player.y = clampY(msg.y);
          player.direction = normalizeDirection(msg.direction, "down");
          player.status = sharedBackend.normalizeStatus(msg.status);
          player.race = msg.race === "ancient-robot" ? "ancient-robot" : msg.race === "rabbit-jk" ? "rabbit-jk" : "teddy";
          socket.playerId = player.id;
          activeSockets.set(player.id, socket);
          players.set(player.id, player);
          joined = true;
        }

        sendJson(socket, { type: "welcome", id: player.id, player: serializePlayer(player), authMode: sharedBackend.enabled ? "supabase" : "legacy" });
        sendJson(socket, { type: "snapshot", players: visiblePlayers(player.map, player.id) });
        broadcastMap(player.map,{ type: "join", player: serializePlayer(player) }, socket);
      } catch (error) {
        console.error("[shared-backend] join failed", error);
        sendJson(socket, {
          type: "auth_error",
          code: error?.code || "AUTH_FAILED",
          message: error?.message || "認証に失敗しました。",
        });
        try { socket.close(4001, "authentication failed"); } catch {}
      } finally {
        joining = false;
      }
      return;
    }

    if (!joined || activeSockets.get(player.id) !== socket) return;

    if (msg.type === "heartbeat") {
      touchPlayerPresence(player);
      sendJson(socket,{
        type:"heartbeat_ack",
        ts:Date.now(),
        map:player.map,
        players:visiblePlayers(player.map, player.id)
      });
      return;
    }

    if (msg.type === "logout") {
      await persistPlayerState(player, true);
      if (player.authenticated) {
        try { await sharedBackend.touchPresence(player.id, player.status); } catch (error) {
          console.error("[shared-backend] logout presence save failed", error);
        }
      }
      sendJson(socket,{type:"logout_ack"});
      setTimeout(()=>{ try { socket.close(1000,"logout"); } catch {} },25);
      return;
    }

    if (msg.type === "status") {
      const nextStatus = sharedBackend.normalizeStatus(msg.status);
      if (player.authenticated) {
        try {
          player.status = await sharedBackend.setPresenceStatus(player.id, nextStatus);
          player.lastPresenceTouchAt = Date.now();
        } catch (error) {
          console.error("[shared-backend] status update failed", error);
          return;
        }
      } else {
        player.status = nextStatus;
      }
      broadcastMap(player.map,{ type:"presence_update", id:player.id, status:player.status });
      return;
    }

    if (msg.type === "chat") {
      const text = typeof msg.text === "string" ? msg.text.trim().slice(0, 80) : "";
      if (!text) return;
      broadcastMap(player.map,{ type: "chat", id: player.id, text }, socket);
      return;
    }

    if (msg.type !== "move") return;
    if (!Number.isFinite(msg.x) || !Number.isFinite(msg.y)) return;

    const requestedMap = normalizeMap(msg.map, player.map);
    const oldMap = player.map;
    const nextDirection = normalizeDirection(msg.direction, player.direction);

    if (requestedMap !== oldMap) {
      broadcastMap(oldMap,{type:"leave",id:player.id},socket);
      player.map = requestedMap;
      player.x = clampX(msg.x);
      player.y = clampY(msg.y);
      player.direction = nextDirection;
      markStateDirty(player);
      sendJson(socket,{type:"map_snapshot",map:player.map,players:visiblePlayers(player.map,player.id)});
      broadcastMap(player.map,{type:"join",player:serializePlayer(player)},socket);
      // マップ移動は即時保存。DB待ちで他プレイヤーへの表示を遅らせない。
      void persistPlayerState(player, true);
      return;
    }

    player.x = clampX(msg.x);
    player.y = clampY(msg.y);
    player.direction = nextDirection;
    markStateDirty(player);
    broadcastMap(player.map,{ type: "move", id: player.id, x: player.x, y: player.y, map:player.map, direction:player.direction }, socket);
  });

  socket.on("close", () => {
    if (!joined) return;
    if (activeSockets.get(player.id) !== socket) return;
    activeSockets.delete(player.id);
    players.delete(player.id);
    broadcastMap(player.map,{ type: "leave", id: player.id });
    void persistPlayerState(player, true);
    if (player.authenticated) {
      void sharedBackend.touchPresence(player.id, player.status).catch((error) => {
        console.error("[shared-backend] disconnect presence save failed", error);
      });
    }
  });
});

const durableStateTimer = setInterval(()=>{
  for (const player of players.values()) {
    if (!player.authenticated || !player.stateDirty) continue;
    void persistPlayerState(player, false);
  }
},5000);

const websocketKeepAlive = setInterval(()=>{
  for(const client of wss.clients){
    if(client.isAlive===false){
      client.terminate();
      continue;
    }
    client.isAlive=false;
    try{ client.ping(); }catch{}
  }
},25000);

wss.on("close",()=>{
  clearInterval(websocketKeepAlive);
  clearInterval(durableStateTimer);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log("");
  console.log("午後三時、夏の果て。 β 0.55");
  console.log(`Server: http://localhost:${PORT}`);
  console.log(`Mode: ${DEV ? "development websocket-only" : "production single-URL"}`);
  console.log(`Shared backend: ${sharedBackend.enabled ? "Supabase" : "legacy compatibility"}`);
  if (!DEV) {
    console.log("Game + WebSocket are served from the same port.");
  }
  console.log("");
});
