import { createClient, type Session, type SupabaseClient, type User } from "@supabase/supabase-js";

export type PresenceStatus = "studying" | "reading" | "busy" | "afk";

export type SharedProfile = {
  user_id: string;
  display_name: string;
  race_id: string | null;
};

export type RaceMaster = {
  race_id: string;
  name_ja: string;
  name_en: string;
  sprite_key: string;
  visual_scale: number;
  move_speed: number;
  sort_order: number;
  active: boolean;
};

const supabaseUrl = String(import.meta.env.VITE_SUPABASE_URL ?? "").trim();
const publishableKey = String(
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ??
  import.meta.env.VITE_SUPABASE_ANON_KEY ??
  ""
).trim();

export const sharedBackendEnabled = Boolean(supabaseUrl && publishableKey);

export const supabase: SupabaseClient | null = sharedBackendEnabled
  ? createClient(supabaseUrl, publishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

function requireClient(): SupabaseClient {
  if (!supabase) throw new Error("Supabase client is not configured.");
  return supabase;
}

export async function getCurrentSession(): Promise<Session | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session;
}

export async function getCurrentUser(): Promise<User | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.auth.getUser();
  if (error) throw error;
  return data.user;
}

export async function loadRaceMasters(): Promise<RaceMaster[]> {
  const client = requireClient();
  const { data, error } = await client
    .from("races")
    .select("race_id,name_ja,name_en,sprite_key,visual_scale,move_speed,sort_order,active")
    .eq("active", true)
    .order("sort_order", { ascending: true });
  if (error) throw error;
  return (data ?? []).map((row: any) => ({
    ...row,
    visual_scale: Number(row.visual_scale),
    move_speed: Number(row.move_speed),
    sort_order: Number(row.sort_order),
  })) as RaceMaster[];
}

export async function loadProfile(userId: string): Promise<SharedProfile | null> {
  const client = requireClient();
  const { data, error } = await client
    .from("profiles")
    .select("user_id,display_name,race_id")
    .eq("user_id", userId)
    .maybeSingle();
  if (error) throw error;
  return (data as SharedProfile | null) ?? null;
}

export async function ensureProfile(user: User): Promise<SharedProfile> {
  const client = requireClient();

  for (let attempt = 0; attempt < 4; attempt += 1) {
    const existing = await loadProfile(user.id);
    if (existing) return existing;
    await new Promise((resolve) => window.setTimeout(resolve, 250));
  }

  const metadataName = [user.user_metadata?.name, user.user_metadata?.full_name]
    .find((value) => typeof value === "string" && value.trim()) as string | undefined;
  const displayName = (metadataName?.trim() || "名無し").slice(0, 20);

  const { data, error } = await client
    .from("profiles")
    .upsert({ user_id: user.id, display_name: displayName }, { onConflict: "user_id" })
    .select("user_id,display_name,race_id")
    .single();
  if (error) throw error;
  return data as SharedProfile;
}

export async function saveProfile(
  userId: string,
  displayName: string,
  raceId: string,
): Promise<SharedProfile> {
  const client = requireClient();
  const cleanName = displayName.trim().slice(0, 20);
  if (!cleanName) throw new Error("表示名を入力してください。");

  const { data, error } = await client
    .from("profiles")
    .update({ display_name: cleanName, race_id: raceId })
    .eq("user_id", userId)
    .select("user_id,display_name,race_id")
    .single();
  if (error) throw error;
  return data as SharedProfile;
}

export async function loadPresenceStatus(userId: string): Promise<PresenceStatus> {
  const client = requireClient();
  const { data, error } = await client
    .from("player_presence")
    .select("status")
    .eq("user_id", userId)
    .maybeSingle();
  if (error) throw error;
  const status = data?.status;
  return status === "studying" || status === "reading" || status === "busy" || status === "afk"
    ? status
    : "afk";
}

export async function savePresenceStatus(userId: string, status: PresenceStatus): Promise<void> {
  const client = requireClient();
  const now = new Date().toISOString();
  const { error } = await client
    .from("player_presence")
    .upsert(
      {
        user_id: userId,
        status,
        status_changed_at: now,
        last_seen_at: now,
      },
      { onConflict: "user_id" },
    );
  if (error) throw error;
}

export async function signInWithGoogle(): Promise<void> {
  const client = requireClient();
  const { error } = await client.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
  });
  if (error) throw error;
}

export async function signInWithEmail(email: string, password: string): Promise<Session | null> {
  const client = requireClient();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data.session;
}

export async function signUpWithEmail(email: string, password: string): Promise<Session | null> {
  const client = requireClient();
  const { data, error } = await client.auth.signUp({
    email,
    password,
    options: { emailRedirectTo: window.location.origin },
  });
  if (error) throw error;
  return data.session;
}

export async function signOutShared(): Promise<void> {
  if (!supabase) return;
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}
