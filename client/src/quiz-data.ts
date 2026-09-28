// 学問クイズデータ（data/questions/<学問>.json）の読み込み。
// questions 配列に問題があるトピックだけ出題できる（knowledge型は用語・演習問題、
// calc型は scripts/math_problems/ で生成した具体的な計算問題）。

export type QuestionFormat = "4択" | "○×" | "並べ替え" | "数字入力";

export type RawKnowledgeQuestion = {
  id: number;
  format: QuestionFormat;
  prompt: string;
  options?: string[];
  answer: number | boolean | string | string[];
  accept?: string[];
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
  questions?: RawKnowledgeQuestion[];
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

// JSONには無いが、ゲームコード側に生成関数があるトピック
export const PLAYABLE_CALC_TOPIC_IDS = new Set<string>([
  "math-number-calculation-017", // 分数の加法・減法
]);

export async function getPlayableTopicIds(subjectNameJa: string): Promise<Set<string>> {
  const topics = await loadSubjectTopics(subjectNameJa);
  const ids = new Set<string>(PLAYABLE_CALC_TOPIC_IDS);
  for (const t of topics) if (t.questions?.length) ids.add(t.topic_id);
  return ids;
}

export async function isPlayableTopic(subjectNameJa: string, topicId: string): Promise<boolean> {
  if (PLAYABLE_CALC_TOPIC_IDS.has(topicId)) return true;
  const topics = await loadSubjectTopics(subjectNameJa);
  return Boolean(topics.find((x) => x.topic_id === topicId)?.questions?.length);
}
