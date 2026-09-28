import { supabase, type PresenceStatus } from "./shared-backend";

// ステータスウインドウと装備ウインドウ（β0.61）。
// 人生クエストのデータ（Supabase の quest_* テーブル）を読むだけで、書き換えはしない。
// 装備した魔法書は今はこの端末の localStorage にだけ保存する。

type Tab = "status" | "equip";

export type StatusWindowOptions = {
  userId: string | null;
  playerName: string;
  presence: PresenceStatus;
  // 状態の変更。送れなかったら false を返す
  onPresence: (status: PresenceStatus) => boolean;
  tab?: Tab;
};

type Subject = { subject_id: string; name_ja: string; icon: string; preset_group: string | null };
type UserStatus = { status_id: string; preset_subject_id: string | null; name_ja: string | null; icon: string | null; sort_order: number; hidden: boolean };
type UserField = { field_id: string; status_id: string; name: string; sort_order: number };
type UserTopic = { topic_id: string; field_id: string; name: string; input_type: string; unit: string | null; sort_order: number; mastered_at: string | null };
type TopicValue = { topic_id: string | null; user_topic_id: string | null; value: number; recorded_at: string };
type NumberTopic = { topic_id: string; field_id: string; unit: string | null };

type LifeQuestData = {
  subjects: Map<string, Subject>;
  statuses: UserStatus[];
  userFields: UserField[];
  userTopics: UserTopic[];
  starsBySubject: Map<string, number>;
  presetNumberTopics: (NumberTopic & { subject_id: string })[];
  values: TopicValue[];
  mastered: Set<string>;
  lv: number;
};

export type EquippedBook = { topic_id: string; name: string };

const EQUIP_KEY = "summer-end-3pm-equipment";

const PRESENCE: [PresenceStatus, string][] = [
  ["online", "オンライン"], ["studying", "勉強中"], ["reading", "読書中"],
  ["working", "作業中"], ["busy", "取り込み中"], ["afk", "AFK"],
];

// 円・万円は「1,000,000 YEN」表記（人生クエストと同じ）
const YEN_UNITS: Record<string, number> = { "円": 1, "万円": 10000 };

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = "", text = "") {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text) e.textContent = text;
  return e;
}

export function loadEquipment(): Record<string, EquippedBook> {
  try {
    const raw = JSON.parse(localStorage.getItem(EQUIP_KEY) || "{}");
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

function saveEquipment(equipment: Record<string, EquippedBook>) {
  localStorage.setItem(EQUIP_KEY, JSON.stringify(equipment));
}

async function fetchAll<T>(query: (from: number, to: number) => PromiseLike<{ data: T[] | null; error: unknown }>): Promise<T[]> {
  const rows: T[] = [];
  for (let from = 0; ; from += 1000) {
    const { data, error } = await query(from, from + 999);
    if (error) throw error;
    rows.push(...(data || []));
    if (!data || data.length < 1000) return rows;
  }
}

let cache: { userId: string; data: LifeQuestData } | null = null;

async function loadLifeQuest(userId: string): Promise<LifeQuestData> {
  if (cache?.userId === userId) return cache.data;
  const sb = supabase!;
  const [subjects, statuses, userFields, userTopics, mastery, values, presetNumbers] = await Promise.all([
    fetchAll<Subject>((a, b) => sb.from("quest_subjects").select("subject_id,name_ja,icon,preset_group").eq("active", true).range(a, b)),
    fetchAll<UserStatus>((a, b) => sb.from("quest_user_statuses").select("status_id,preset_subject_id,name_ja,icon,sort_order,hidden").eq("user_id", userId).range(a, b)),
    fetchAll<UserField>((a, b) => sb.from("quest_user_fields").select("field_id,status_id,name,sort_order").eq("user_id", userId).range(a, b)),
    fetchAll<UserTopic>((a, b) => sb.from("quest_user_topics").select("topic_id,field_id,name,input_type,unit,sort_order,mastered_at").eq("user_id", userId).range(a, b)),
    fetchAll<{ topic_id: string }>((a, b) => sb.from("quest_topic_mastery").select("topic_id").eq("user_id", userId).range(a, b)),
    fetchAll<TopicValue>((a, b) => sb.from("quest_topic_values").select("topic_id,user_topic_id,value,recorded_at").eq("user_id", userId).order("recorded_at", { ascending: false }).range(a, b)),
    fetchAll<NumberTopic>((a, b) => sb.from("quest_topics").select("topic_id,field_id,unit").eq("active", true).eq("input_type", "number").range(a, b)),
  ]);

  // マスター済みトピック → 分野 → 学問 の順にたどって、学問ごとの★を数える
  const masteredIds = mastery.map((m) => m.topic_id);
  const masteredTopics: { topic_id: string; field_id: string }[] = [];
  for (let i = 0; i < masteredIds.length; i += 200) {
    const ids = masteredIds.slice(i, i + 200);
    const { data, error } = await sb.from("quest_topics").select("topic_id,field_id").in("topic_id", ids);
    if (error) throw error;
    masteredTopics.push(...(data || []));
  }
  const fieldIds = [...new Set([...masteredTopics, ...presetNumbers].map((t) => t.field_id))];
  const fieldSubject = new Map<string, string>();
  for (let i = 0; i < fieldIds.length; i += 200) {
    const { data, error } = await sb.from("quest_fields").select("field_id,subject_id").in("field_id", fieldIds.slice(i, i + 200));
    if (error) throw error;
    for (const f of data || []) fieldSubject.set(f.field_id, f.subject_id);
  }
  const starsBySubject = new Map<string, number>();
  for (const t of masteredTopics) {
    const subjectId = fieldSubject.get(t.field_id);
    if (subjectId) starsBySubject.set(subjectId, (starsBySubject.get(subjectId) || 0) + 1);
  }

  const data: LifeQuestData = {
    subjects: new Map(subjects.map((s) => [s.subject_id, s])),
    statuses: statuses.filter((s) => !s.hidden).sort((a, b) => a.sort_order - b.sort_order || a.status_id.localeCompare(b.status_id)),
    userFields,
    userTopics,
    starsBySubject,
    presetNumberTopics: presetNumbers.map((t) => ({ ...t, subject_id: fieldSubject.get(t.field_id) || "" })),
    values,
    mastered: new Set(masteredIds),
    lv: masteredIds.length + userTopics.filter((t) => t.mastered_at).length,
  };
  cache = { userId, data };
  return data;
}

function statusName(data: LifeQuestData, s: UserStatus) {
  return s.name_ja || (s.preset_subject_id ? data.subjects.get(s.preset_subject_id)?.name_ja : "") || "";
}

function statusIcon(data: LifeQuestData, s: UserStatus) {
  const preset = s.preset_subject_id ? data.subjects.get(s.preset_subject_id) : undefined;
  if (!s.icon && preset) {
    const img = el("img", "se-lq-pixicon");
    img.src = `/lq-icons/${preset.subject_id}.svg`; // 人生クエストの apps/life-quest/icons のコピー
    img.alt = "";
    img.onerror = () => img.replaceWith(el("span", "se-lq-icon", preset.icon || ""));
    return img;
  }
  return el("span", "se-lq-icon", s.icon || preset?.icon || "");
}

function ownTopics(data: LifeQuestData, s: UserStatus) {
  const fieldIds = new Set(data.userFields.filter((f) => f.status_id === s.status_id).map((f) => f.field_id));
  return data.userTopics.filter((t) => fieldIds.has(t.field_id));
}

// ★（マスターしたチェック項目の数）。入力項目だけのステータス（資産など）は最新の値
function statusBadge(data: LifeQuestData, s: UserStatus): { text: string; zero: boolean } {
  const own = ownTopics(data, s);
  const presetNumbers = data.presetNumberTopics.filter((t) => t.subject_id === s.preset_subject_id);
  const hasCheck = own.some((t) => t.input_type === "check") || (Boolean(s.preset_subject_id) && presetNumbers.length === 0);
  if (!hasCheck && (presetNumbers.length || own.length)) {
    for (const t of presetNumbers) {
      const v = data.values.find((row) => row.topic_id === t.topic_id);
      if (v) return { text: formatValue(v.value, t.unit), zero: false };
    }
    for (const t of own.filter((x) => x.input_type === "number")) {
      const v = data.values.find((row) => row.user_topic_id === t.topic_id);
      if (v) return { text: formatValue(v.value, t.unit), zero: false };
    }
    return { text: "—", zero: true };
  }
  const stars = (s.preset_subject_id ? data.starsBySubject.get(s.preset_subject_id) || 0 : 0) + own.filter((t) => t.mastered_at).length;
  return { text: `★${stars}`, zero: stars === 0 };
}

function formatValue(value: number, unit: string | null) {
  const n = Number(value);
  if (Number.isFinite(n) && unit && YEN_UNITS[unit]) return `${Math.round(n * YEN_UNITS[unit]).toLocaleString("en-US")} YEN`;
  const text = Number.isFinite(n) ? n.toLocaleString("ja-JP", { maximumFractionDigits: 6 }) : String(value);
  return unit ? `${text} ${unit}` : text;
}

// 魔法書をつけられるのは学問（29学問・英語）と自作ステータスのうちチェック項目があるもの
function canEquipBook(data: LifeQuestData, s: UserStatus) {
  if (s.preset_subject_id) {
    const preset = data.subjects.get(s.preset_subject_id);
    return preset?.preset_group === "29学問" || s.preset_subject_id === "english";
  }
  return ownTopics(data, s).some((t) => t.input_type === "check");
}

type BookChoice = { topic_id: string; name: string; field: string; mastered: boolean };

async function loadBookChoices(data: LifeQuestData, s: UserStatus): Promise<BookChoice[]> {
  const choices: BookChoice[] = [];
  if (s.preset_subject_id) {
    const sb = supabase!;
    const { data: fields, error } = await sb.from("quest_fields").select("field_id,name,sort_order").eq("subject_id", s.preset_subject_id).eq("active", true).order("sort_order");
    if (error) throw error;
    const fieldName = new Map((fields || []).map((f) => [f.field_id, f.name]));
    const fieldOrder = new Map((fields || []).map((f, i) => [f.field_id, i]));
    const ids = [...fieldName.keys()];
    const topics: { topic_id: string; field_id: string; name: string; recommended_order: number }[] = [];
    for (let i = 0; i < ids.length; i += 100) {
      const rows = await fetchAll<{ topic_id: string; field_id: string; name: string; recommended_order: number }>((a, b) =>
        sb.from("quest_topics").select("topic_id,field_id,name,recommended_order").eq("active", true).eq("input_type", "check").in("field_id", ids.slice(i, i + 100)).range(a, b));
      topics.push(...rows);
    }
    topics.sort((a, b) => (fieldOrder.get(a.field_id)! - fieldOrder.get(b.field_id)!) || a.recommended_order - b.recommended_order || a.topic_id.localeCompare(b.topic_id));
    for (const t of topics) choices.push({ topic_id: t.topic_id, name: t.name, field: fieldName.get(t.field_id) || "", mastered: data.mastered.has(t.topic_id) });
  }
  const fields = data.userFields.filter((f) => f.status_id === s.status_id).sort((a, b) => a.sort_order - b.sort_order);
  for (const f of fields) {
    for (const t of data.userTopics.filter((x) => x.field_id === f.field_id && x.input_type === "check").sort((a, b) => a.sort_order - b.sort_order)) {
      choices.push({ topic_id: t.topic_id, name: t.name, field: f.name, mastered: Boolean(t.mastered_at) });
    }
  }
  return choices;
}

export function openStatusWindow(opts: StatusWindowOptions) {
  cache = null; // 人生クエスト側の更新を拾うため、開くたびに読み直す
  let presence = opts.presence;
  const overlay = el("div", "se-overlay");
  Object.assign(overlay.style, { display: "flex", zIndex: "16000" });
  const card = el("div", "se-card se-status-card");
  const tabRow = el("div", "se-book-tabs");
  const body = el("div", "se-status-body");
  const actions = el("div", "se-actions");
  const closeBtn = el("button", "se-btn is-primary", "CLOSE");
  closeBtn.type = "button";
  const close = () => overlay.remove();
  closeBtn.addEventListener("click", close);
  actions.appendChild(closeBtn);
  card.append(tabRow, body, actions);
  overlay.appendChild(card);
  overlay.addEventListener("click", (ev) => { if (ev.target === overlay) close(); });
  document.body.appendChild(overlay);

  const tabs: [Tab, string][] = [["status", "ステータス"], ["equip", "装備"]];
  const tabButtons = tabs.map(([id, label]) => {
    const b = el("button", "se-btn", label);
    b.type = "button";
    b.addEventListener("click", () => show(id));
    tabRow.appendChild(b);
    return b;
  });

  const message = (text: string) => body.replaceChildren(el("div", "se-message", text));

  let current: Tab = opts.tab || "status";
  function show(tab: Tab) {
    current = tab;
    tabButtons.forEach((b, i) => b.classList.toggle("is-primary", tabs[i][0] === tab));
    if (tab === "status") renderStatus(); else renderEquip();
  }

  function presenceRow() {
    const row = el("div", "se-presence-row");
    for (const [value, label] of PRESENCE) {
      const b = el("button", "se-presence-btn");
      b.type = "button";
      b.title = label;
      const img = el("img");
      img.src = `/status/${value}.svg`;
      img.alt = "";
      b.append(img, el("span", "", label));
      b.classList.toggle("is-selected", value === presence);
      b.addEventListener("click", () => {
        if (value === presence || !opts.onPresence(value)) return;
        presence = value;
        row.querySelectorAll(".se-presence-btn").forEach((x) => x.classList.toggle("is-selected", x === b));
      });
      row.appendChild(b);
    }
    return row;
  }

  async function renderStatus() {
    if (!opts.userId || !supabase) {
      message("人生クエストのアカウントでログインすると、ステータスが表示される。");
      return;
    }
    message("読み込み中…");
    let data: LifeQuestData;
    try {
      data = await loadLifeQuest(opts.userId);
    } catch {
      if (current === "status") message("人生クエストのデータを読み込めなかった。");
      return;
    }
    if (current !== "status") return;
    const head = el("div", "se-status-head");
    head.append(el("div", "se-status-name", opts.playerName), el("div", "se-status-lv", `Lv ${data.lv}`));
    const list = el("div", "se-lq-list");
    if (data.statuses.length === 0) list.appendChild(el("div", "se-message", "人生クエストにステータスがまだない。"));
    for (const s of data.statuses) {
      const row = el("div", "se-lq-row");
      const badge = statusBadge(data, s);
      row.append(statusIcon(data, s), el("span", "se-lq-name", statusName(data, s)), el("span", `se-lq-stars${badge.zero ? " is-zero" : ""}`, badge.text));
      list.appendChild(row);
    }
    body.replaceChildren(head, el("div", "se-label", "状態"), presenceRow(), el("div", "se-label", "人生クエスト"), list);
  }

  async function renderEquip() {
    if (!opts.userId || !supabase) {
      message("人生クエストのアカウントでログインすると、魔法書を装備できる。");
      return;
    }
    message("読み込み中…");
    let data: LifeQuestData;
    try {
      data = await loadLifeQuest(opts.userId);
    } catch {
      if (current === "equip") message("人生クエストのデータを読み込めなかった。");
      return;
    }
    if (current !== "equip") return;
    const equipment = loadEquipment();
    const list = el("div", "se-lq-list");
    const bookStatuses = data.statuses.filter((s) => canEquipBook(data, s));
    if (bookStatuses.length === 0) list.appendChild(el("div", "se-message", "魔法書をつけられる学問がまだない。"));
    for (const s of bookStatuses) {
      const row = el("button", "se-lq-row se-equip-row");
      row.type = "button";
      const book = equipment[s.status_id];
      row.append(statusIcon(data, s), el("span", "se-lq-name", statusName(data, s)), el("span", `se-equip-book${book ? "" : " is-empty"}`, book ? book.name : "なし"));
      row.addEventListener("click", () => renderPicker(data, s));
      list.appendChild(row);
    }
    body.replaceChildren(
      el("div", "se-label", "魔法書（学問ごとに1冊）"), list,
      el("div", "se-label", "その他の装備"), el("div", "se-message", "まだ何も持っていない。"),
    );
  }

  async function renderPicker(data: LifeQuestData, s: UserStatus) {
    message("読み込み中…");
    let choices: BookChoice[];
    try {
      choices = await loadBookChoices(data, s);
    } catch {
      message("トピックを読み込めなかった。");
      return;
    }
    if (current !== "equip") return;
    const equipment = loadEquipment();
    const equipped = equipment[s.status_id]?.topic_id;
    const back = el("button", "se-btn", "もどる");
    back.type = "button";
    back.addEventListener("click", () => renderEquip());
    const list = el("div", "se-lq-list se-picker-list");
    if (equipped) {
      const remove = el("button", "se-lq-row se-equip-row", "はずす");
      remove.type = "button";
      remove.addEventListener("click", () => {
        delete equipment[s.status_id];
        saveEquipment(equipment);
        renderEquip();
      });
      list.appendChild(remove);
    }
    let lastField = "";
    for (const c of choices) {
      if (c.field !== lastField) {
        lastField = c.field;
        list.appendChild(el("div", "se-picker-field", c.field));
      }
      const row = el("button", `se-lq-row se-equip-row${c.topic_id === equipped ? " is-selected" : ""}`);
      row.type = "button";
      row.append(el("span", "se-lq-name", c.name), el("span", "se-lq-stars", c.mastered ? "★" : ""));
      row.addEventListener("click", () => {
        equipment[s.status_id] = { topic_id: c.topic_id, name: c.name };
        saveEquipment(equipment);
        renderEquip();
      });
      list.appendChild(row);
    }
    if (choices.length === 0) list.appendChild(el("div", "se-message", "トピックがない。"));
    body.replaceChildren(el("div", "se-label", `${statusName(data, s)}の魔法書を選ぶ`), list, back);
  }

  show(current);
}
