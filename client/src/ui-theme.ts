import "./ui-themes.css";

// UIデザイン（β0.58）。OPTIONSから選択し、localStorageに保存する。初期値はA（便箋）。
export type UiThemeId = "A" | "D" | "E" | "I" | "L" | "N" | "P" | "R";

export type UiTheme = {
  id: UiThemeId;
  label: string;
  font: string;
  nameFg: string;
  nameBg: string;
  tagFill: string;
  tagStroke: string;
  bubbleFg: string;
  bubbleBg: number;
  bubbleStroke: number;
  bubbleRadius: number;
};

export const UI_THEMES: UiTheme[] = [
  { id:"A", label:"便箋", font:'"Klee One",serif', nameFg:"#3b2a22", nameBg:"#f6efe2ee", tagFill:"#fffaf0", tagStroke:"#8a5a44", bubbleFg:"#3b2a22", bubbleBg:0xf6efe2, bubbleStroke:0x6b4a3a, bubbleRadius:2 },
  { id:"D", label:"ホーロー看板", font:'"Yusei Magic",sans-serif', nameFg:"#1f3a5f", nameBg:"#ffffffee", tagFill:"#ffffff", tagStroke:"#1f3a5f", bubbleFg:"#1f3a5f", bubbleBg:0xf4efe3, bubbleStroke:0x1f3a5f, bubbleRadius:12 },
  { id:"E", label:"障子・木枠", font:'"Shippori Mincho",serif', nameFg:"#f3ead8", nameBg:"#6b4a2fee", tagFill:"#fbf3e0", tagStroke:"#6b4a2f", bubbleFg:"#3b2a1e", bubbleBg:0xf3ead8, bubbleStroke:0x6b4a2f, bubbleRadius:2 },
  { id:"I", label:"新聞・活版", font:'"Shippori Mincho",serif', nameFg:"#f2efe6", nameBg:"#111111ee", tagFill:"#f2efe6", tagStroke:"#1a1a1a", bubbleFg:"#111111", bubbleBg:0xf2efe6, bubbleStroke:0x111111, bubbleRadius:0 },
  { id:"L", label:"絵本", font:'"Hachi Maru Pop",sans-serif', nameFg:"#6a4a5a", nameBg:"#ffffffee", tagFill:"#ffffff", tagStroke:"#e58aa3", bubbleFg:"#6a4a5a", bubbleBg:0xfff6e8, bubbleStroke:0xf2a7b8, bubbleRadius:14 },
  { id:"N", label:"カセット80s", font:'"Zen Maru Gothic",sans-serif', nameFg:"#f1e4c8", nameBg:"#3a2a1eee", tagFill:"#f6e8c8", tagStroke:"#7a4a22", bubbleFg:"#3a2a1e", bubbleBg:0xf1e4c8, bubbleStroke:0xe7892f, bubbleRadius:6 },
  { id:"P", label:"夜空・星", font:'"Kaisei Decol",serif', nameFg:"#e8c96a", nameBg:"#141a3aee", tagFill:"#f5e6a8", tagStroke:"#141a3a", bubbleFg:"#f5ecd2", bubbleBg:0x141a3a, bubbleStroke:0xc9a94f, bubbleRadius:3 },
  { id:"R", label:"風鈴", font:'"Zen Kurenaido",sans-serif', nameFg:"#1f3f7a", nameBg:"#ffffffdd", tagFill:"#ffffff", tagStroke:"#2f5fa8", bubbleFg:"#1f3f7a", bubbleBg:0xffffff, bubbleStroke:0x1f3f7a, bubbleRadius:12 }
];

const STORAGE_KEY = "summer-end-3pm-ui-theme";
const DEFAULT_THEME: UiThemeId = "A";

export function getUiTheme(): UiTheme {
  let stored = "";
  try { stored = localStorage.getItem(STORAGE_KEY) || ""; } catch {}
  return UI_THEMES.find((t) => t.id === stored) ?? UI_THEMES.find((t) => t.id === DEFAULT_THEME)!;
}

export function applyUiTheme(id: UiThemeId): UiTheme {
  const theme = UI_THEMES.find((t) => t.id === id) ?? UI_THEMES[0];
  document.documentElement.dataset.theme = theme.id;
  try { localStorage.setItem(STORAGE_KEY, theme.id); } catch {}
  return theme;
}

// 起動時に保存済みのデザインを反映する。
document.documentElement.dataset.theme = getUiTheme().id;
