const { createClient } = require("@supabase/supabase-js");

const supabaseUrl = String(process.env.SUPABASE_URL || "").trim();
const serviceRoleKey = String(process.env.SUPABASE_SERVICE_ROLE_KEY || "").trim();

const enabled = Boolean(supabaseUrl && serviceRoleKey);
const client = enabled
  ? createClient(supabaseUrl, serviceRoleKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    })
  : null;

const ALLOWED_STATUS = new Set(["online", "studying", "reading", "busy", "afk"]);

function normalizeStatus(value) {
  return ALLOWED_STATUS.has(value) ? value : "online";
}

function backendError(code, message, cause) {
  const error = new Error(message);
  error.code = code;
  if (cause) error.cause = cause;
  return error;
}

function requireClient() {
  if (!client) throw backendError("BACKEND_DISABLED", "Shared backend is not configured on the server.");
  return client;
}

async function verifyAccessToken(accessToken) {
  if (!enabled) return null;
  if (typeof accessToken !== "string" || !accessToken.trim()) {
    throw backendError("TOKEN_REQUIRED", "ログイン情報がありません。もう一度ログインしてください。");
  }
  const admin = requireClient();
  const { data, error } = await admin.auth.getUser(accessToken.trim());
  if (error || !data?.user) {
    throw backendError("TOKEN_INVALID", "ログイン情報を確認できませんでした。もう一度ログインしてください。", error);
  }
  return data.user;
}

async function loadBootstrap(userId) {
  const admin = requireClient();
  const [{ data: profile, error: profileError }, { data: presence, error: presenceError }, { data: state, error: stateError }] = await Promise.all([
    admin.from("profiles").select("user_id,display_name,race_id").eq("user_id", userId).maybeSingle(),
    admin.from("player_presence").select("status,last_seen_at").eq("user_id", userId).maybeSingle(),
    admin.from("summer_end_player_state").select("map_id,x,y,direction,updated_at").eq("user_id", userId).maybeSingle(),
  ]);

  if (profileError) throw backendError("PROFILE_READ_FAILED", "共通プロフィールを読み込めませんでした。", profileError);
  if (!profile) throw backendError("PROFILE_MISSING", "共通プロフィールがありません。再ログインしてください。");
  if (!profile.race_id) throw backendError("RACE_REQUIRED", "種族が未設定です。ログイン画面で種族を選択してください。");
  if (presenceError) throw backendError("PRESENCE_READ_FAILED", "ステータスを読み込めませんでした。", presenceError);
  if (stateError) throw backendError("STATE_READ_FAILED", "保存位置を読み込めませんでした。", stateError);

  const { data: race, error: raceError } = await admin
    .from("races")
    .select("race_id,sprite_key,visual_scale,move_speed,active")
    .eq("race_id", profile.race_id)
    .eq("active", true)
    .maybeSingle();
  if (raceError) throw backendError("RACE_READ_FAILED", "種族情報を読み込めませんでした。", raceError);
  if (!race) throw backendError("RACE_UNAVAILABLE", "設定されている種族は現在利用できません。");

  return {
    profile,
    race,
    status: normalizeStatus(presence?.status),
    state: state || null,
  };
}

async function setPresenceStatus(userId, status) {
  const admin = requireClient();
  const normalized = normalizeStatus(status);
  const now = new Date().toISOString();
  const { error } = await admin.from("player_presence").upsert({
    user_id: userId,
    status: normalized,
    status_changed_at: now,
    last_seen_at: now,
  }, { onConflict: "user_id" });
  if (error) throw backendError("PRESENCE_WRITE_FAILED", "ステータスを保存できませんでした。", error);
  return normalized;
}

async function touchPresence(userId, fallbackStatus = "online") {
  const admin = requireClient();
  const now = new Date().toISOString();
  const { data, error } = await admin
    .from("player_presence")
    .update({ last_seen_at: now })
    .eq("user_id", userId)
    .select("user_id")
    .maybeSingle();
  if (error) throw backendError("PRESENCE_TOUCH_FAILED", "presence last_seen_at update failed", error);
  if (data) return;
  const { error: insertError } = await admin.from("player_presence").insert({
    user_id: userId,
    status: normalizeStatus(fallbackStatus),
    last_seen_at: now,
  });
  if (insertError) throw backendError("PRESENCE_TOUCH_FAILED", "presence row creation failed", insertError);
}

async function saveSummerState(userId, state) {
  const admin = requireClient();
  const { error } = await admin.from("summer_end_player_state").upsert({
    user_id: userId,
    map_id: state.map,
    x: state.x,
    y: state.y,
    direction: state.direction,
  }, { onConflict: "user_id" });
  if (error) throw backendError("STATE_WRITE_FAILED", "保存位置を更新できませんでした。", error);
}

module.exports = {
  enabled,
  normalizeStatus,
  verifyAccessToken,
  loadBootstrap,
  setPresenceStatus,
  touchPresence,
  saveSummerState,
};
