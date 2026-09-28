// 学問クイズデータ（data/questions/<学問>.json）の読み込み。
// トピックの type が "knowledge" のものだけ、実際の問題（questions配列）を持っていて出題できる。
// type が "calc" のものはまだパターン仕様だけで、実行コードのある一部トピック（下の PLAYABLE_CALC_TOPIC_IDS）を除き出題できない。

export type QuestionFormat = "4択" | "○×" | "並べ替え" | "数字入力";

export type RawKnowledgeQuestion = {
  id: number;
  format: QuestionFormat;
  prompt: string;
  options?: string[];
  answer: number | boolean | string | string[];
  explain: string;
};

export type KnowledgeTopic = {
  topic_id: string;
  field: string;
  topic: string;
  tag: string;
  type: "knowledge";
  summary: string;
  questions: RawKnowledgeQuestion[];
};

export type CalcTopic = {
  topic_id: string;
  field: string;
  topic: string;
  tag: string;
  type: "calc";
  summary: string;
  types: unknown[];
};

export type SubjectTopic = KnowledgeTopic | CalcTopic;

type SubjectFile = { subject: string; note?: string; topics: SubjectTopic[] };

// Vite: 各 data/questions/*.json をコード分割された動的 import として登録。実際に使う学問のファイルだけが読み込まれる。
const loaders = import.meta.glob<SubjectFile>("../../data/questions/*.json");

function fileKeyFor(subjectNameJa: string) {
  return `../../data/questions/${subjectNameJa}.json`;
}

// 実際にクイズデータファイルがある学問名（例：["数学"]）。装備画面でどの学問を選べるようにするかに使う。
export function getImplementedSubjectNames(): string[] {
  return Object.keys(loaders).map((key) => {
    const m = /\/([^/]+)\.json$/.exec(key);
    return m ? m[1] : key;
  });
}

const cache = new Map<string, Promise<SubjectTopic[]>>();

export function loadSubjectTopics(subjectNameJa: string): Promise<SubjectTopic[]> {
  const key = fileKeyFor(subjectNameJa);
  const loader = loaders[key];
  if (!loader) return Promise.resolve([]);
  let p = cache.get(key);
  if (!p) {
    p = loader().then((mod) => (mod as SubjectFile).topics);
    cache.set(key, p);
  }
  return p;
}

// まだ生成コードを書いていない calc 型トピックのうち、既存のゲームコードで出題できるものだけをここに登録する。
// キーはトピックID、値はそのトピック専用の問題生成関数（intellect-battle.ts 側で登録する）。
export const PLAYABLE_CALC_TOPIC_IDS = new Set<string>([
  "math-number-calculation-017", // 分数の加法・減法（既存のフォールバック生成コード）
]);

export async function getPlayableTopicIds(subjectNameJa: string): Promise<Set<string>> {
  const topics = await loadSubjectTopics(subjectNameJa);
  const ids = new Set<string>();
  for (const t of topics) {
    if (t.type === "knowledge" && t.questions.length > 0) ids.add(t.topic_id);
    else if (PLAYABLE_CALC_TOPIC_IDS.has(t.topic_id)) ids.add(t.topic_id);
  }
  for (const id of PLAYABLE_CALC_TOPIC_IDS) ids.add(id); // 分数の加法・減法のようにJSON側に無いものも含める
  return ids;
}

export async function isPlayableTopic(subjectNameJa: string, topicId: string): Promise<boolean> {
  if (PLAYABLE_CALC_TOPIC_IDS.has(topicId)) return true;
  const topics = await loadSubjectTopics(subjectNameJa);
  const t = topics.find((x) => x.topic_id === topicId);
  return Boolean(t && t.type === "knowledge" && t.questions.length > 0);
}
