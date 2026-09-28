// 知性バトル: 問題づくり・問題図鑑・戦闘画面。
// 装備した魔法書（学問＋トピック）に実際のクイズデータ（quiz-data.ts）があればそこから出題し、
// 無ければ数学「分数の加法・減法」（唯一のハードコード生成コード）にフォールバックする。
// 「ちゃんと実装したトピックだけ遊ばせる」方針（Keita 2026-09-28）により、
// 装備画面（status-window.ts）側でも quiz-data.ts の出題可能判定を使って選べるトピックを絞っている。

import { getPlayableTopicIds, loadSubjectTopics, type KnowledgeTopic, type RawKnowledgeQuestion } from "./quiz-data";

export type Question = {
  id: string;
  topic: string;
  prompt: string;
  choices: string[];
  answerIndex: number;
  explain: string;
  // 数字入力・並べ替え型の問題は選択肢ではなく文字入力で答える
  inputMode?: "text";
  expectedAnswer?: string;
};

export type EquippedTopic = { subject: string; topicId: string; topicName: string };

type BookEntry = {
  topic: string;
  prompt: string;
  answer: string;
  explain: string;
  solved: number;
  wrong: number;
  weak: boolean;
  lastSeen: number;
  inputMode?: "text";
};

const BOOK_KEY = "summer-end-3pm-question-book";
export const MAX_HEARTS = 3;

const gcd = (a:number,b:number):number => b===0 ? Math.abs(a) : gcd(b,a%b);
const rand = (min:number,max:number) => min+Math.floor(Math.random()*(max-min+1));

function fracText(n:number,d:number,mixed=false) {
  const g=gcd(n,d); n/=g; d/=g;
  if(d===1) return String(n);
  if(mixed && n>d) return `${Math.floor(n/d)} ${n%d}/${d}`;
  return `${n}/${d}`;
}

function buildChoices(answer:string, candidates:string[]) {
  const set=new Set<string>([answer]);
  for(const c of candidates) if(set.size<4 && c && c!==answer && !c.startsWith("0") && !c.includes("-")) set.add(c);
  let guard=0;
  while(set.size<4 && guard++<50) set.add(`${rand(1,11)}/${rand(2,12)}`);
  const choices=[...set].sort(()=>Math.random()-.5);
  return { choices, answerIndex: choices.indexOf(answer) };
}

// 分数の加法・減法（入門）の型: A 同じ分母 / B 違う分母の足し算 / C 違う分母の引き算 / D 帯分数の引き算
export function makeFractionQuestion(): Question {
  const topic="分数の加法・減法";
  const type=["A","B","C","D"][rand(0,3)];
  if(type==="A"){
    const d=rand(5,12), a=rand(1,d-2), b=rand(1,d-1-a);
    const answer=fracText(a+b,d);
    const {choices,answerIndex}=buildChoices(answer,[`${a+b}/${d*2}`,fracText(a+b+1,d),fracText(Math.abs(a+b-1),d)]);
    return { id:`frac:${a}/${d}+${b}/${d}`, topic, prompt:`${a}/${d} ＋ ${b}/${d} ＝ ?`, choices, answerIndex,
      explain:`分母はそのまま、分子を足して ${a+b}/${d}${answer!==`${a+b}/${d}` ? `。約分して ${answer}` : ""}。` };
  }
  if(type==="B" || type==="C"){
    let b=rand(2,9), d=rand(2,9);
    while(d===b) d=rand(2,9);
    let a=rand(1,b-1), c=rand(1,d-1);
    while(a*d===c*b || gcd(a,b)!==1 || gcd(c,d)!==1){ a=rand(1,b-1); c=rand(1,d-1); }
    if(type==="C" && a*d<c*b){ [a,b,c,d]=[c,d,a,b]; }
    const L=b*d/gcd(b,d), an=a*(L/b), cn=c*(L/d);
    const n=type==="B" ? an+cn : an-cn;
    const op=type==="B" ? "＋" : "−";
    const answer=fracText(n,L);
    const naive=type==="B" ? fracText(a+c,b+d) : (a>c && b!==d ? fracText(a-c,Math.abs(b-d)||1) : "");
    const {choices,answerIndex}=buildChoices(answer,[naive,fracText(n+1,L),`${n}/${b*d===L ? L*2 : b*d}`,fracText(n+2,L)]);
    return { id:`frac:${a}/${b}${type==="B"?"+":"-"}${c}/${d}`, topic, prompt:`${a}/${b} ${op} ${c}/${d} ＝ ?`, choices, answerIndex,
      explain:`分母を${L}にそろえると ${an}/${L} ${op} ${cn}/${L} ＝ ${n}/${L}${answer!==`${n}/${L}` ? `。約分して ${answer}` : ""}。` };
  }
  // D: 帯分数の引き算（答えは正、1より大きければ帯分数で表示）
  let w1=rand(2,4), w2=rand(1,w1-1);
  let b=rand(2,6), d=rand(2,6);
  let a=rand(1,b-1), c=rand(1,d-1);
  while(gcd(a,b)!==1) a=rand(1,b-1);
  while(gcd(c,d)!==1) c=rand(1,d-1);
  const n1=w1*b+a, n2=w2*d+c;
  if(n1*d<=n2*b){ w1+=1; }
  const N1=w1*b+a, L=b*d/gcd(b,d), x=N1*(L/b), y=n2*(L/d), n=x-y;
  const answer=fracText(n,L,true);
  const {choices,answerIndex}=buildChoices(answer,[fracText(n+L,L,true),fracText(Math.abs(n-L)||1,L,true),fracText(n+1,L,true),fracText((w1-w2)*L+Math.abs(a*(L/b)-c*(L/d)),L,true)]);
  return { id:`frac:${w1} ${a}/${b}-${w2} ${c}/${d}`, topic, prompt:`${w1} ${a}/${b} − ${w2} ${c}/${d} ＝ ?`, choices, answerIndex,
    explain:`仮分数にすると ${N1}/${b} − ${n2}/${d} ＝ ${x}/${L} − ${y}/${L} ＝ ${n}/${L}。答えは ${answer}。` };
}

// quiz-data.ts の生データ（knowledge型）を実際のQuestionに変換する。
// 4択は選択肢の並びをシャッフルして正解位置を固定化しない。○×もランダムに並べる。
// 数字入力・並べ替えは選択肢ではなく文字入力で答える形にする。
function normalizeKnowledgeQuestion(topic: KnowledgeTopic, raw: RawKnowledgeQuestion): Question {
  const id = `${topic.topic_id}:${raw.id}`;
  if (raw.format === "4択" && Array.isArray(raw.options)) {
    const options = raw.options;
    const correctIndex = raw.answer as number;
    const order = options.map((_, i) => i).sort(() => Math.random() - .5);
    const choices = order.map((i) => options[i]);
    const answerIndex = order.indexOf(correctIndex);
    return { id, topic: topic.topic, prompt: raw.prompt, choices, answerIndex, explain: raw.explain };
  }
  if (raw.format === "○×") {
    const isTrue = raw.answer as boolean;
    const choices = Math.random() < 0.5 ? ["○", "×"] : ["×", "○"];
    const answerIndex = choices.indexOf(isTrue ? "○" : "×");
    return { id, topic: topic.topic, prompt: raw.prompt, choices, answerIndex, explain: raw.explain };
  }
  // 数字入力・並べ替え
  const expected = Array.isArray(raw.answer) ? raw.answer.join(",") : String(raw.answer);
  return { id, topic: topic.topic, prompt: raw.prompt, choices: [], answerIndex: -1, explain: raw.explain,
    inputMode: "text", expectedAnswer: expected };
}

// 装備中のトピックから問題を1つ作る。実データが無い／読み込めない場合は undefined を返す（呼び出し側でフォールバック）。
export async function makeQuestionForEquippedTopic(equipped: EquippedTopic): Promise<Question | undefined> {
  if (equipped.topicId === "math-number-calculation-017") return makeFractionQuestion();
  const topics = await loadSubjectTopics(equipped.subject);
  const topic = topics.find((t) => t.topic_id === equipped.topicId);
  if (!topic || topic.type !== "knowledge" || topic.questions.length === 0) return undefined;
  const raw = topic.questions[rand(0, topic.questions.length - 1)];
  return normalizeKnowledgeQuestion(topic, raw);
}

export { getPlayableTopicIds };

function loadBook(): Record<string,BookEntry> {
  try { return JSON.parse(localStorage.getItem(BOOK_KEY) || "{}") || {}; } catch { return {}; }
}
function saveBook(book:Record<string,BookEntry>) {
  try { localStorage.setItem(BOOK_KEY, JSON.stringify(book)); } catch { /* 保存できなくても戦闘は続ける */ }
}

function record(q:Question, result:"solved"|"wrong"|"unknown") {
  const book=loadBook();
  const answerText = q.inputMode==="text" ? (q.expectedAnswer ?? "") : q.choices[q.answerIndex];
  const e=book[q.id] ?? { topic:q.topic, prompt:q.prompt, answer:answerText, explain:q.explain, solved:0, wrong:0, weak:false, lastSeen:0, inputMode:q.inputMode };
  e.inputMode=q.inputMode;
  if(result==="solved"){ e.solved++; e.weak=false; }
  else { e.wrong++; e.weak=true; }
  e.lastSeen=Date.now();
  book[q.id]=e;
  saveBook(book);
}

// 苦手枠: 間違えた・わからんだった問題から1つ（4択・○×型は選択肢を作り直す。数字入力型はそのまま再出題）
function pickWeakQuestion(excludeId:string): Question | undefined {
  const book=loadBook();
  const weak=Object.entries(book).filter(([id,e])=>e.weak && id!==excludeId);
  if(weak.length===0) return undefined;
  const [id,e]=weak[rand(0,weak.length-1)];
  if(e.inputMode==="text"){
    return { id, topic:e.topic, prompt:e.prompt, choices:[], answerIndex:-1, explain:e.explain, inputMode:"text", expectedAnswer:e.answer };
  }
  const others=Object.values(book).map(x=>x.answer).filter(a=>a!==e.answer);
  const {choices,answerIndex}=buildChoices(e.answer,others.sort(()=>Math.random()-.5));
  return { id, topic:e.topic, prompt:e.prompt, choices, answerIndex, explain:e.explain };
}

// キメラのハート（β0.62 は全員2つ。正解1回でハート1つ減る）
const ENEMY_HEARTS=2;

type Enemy = { name:string; question:Question; weak:boolean; hearts:number };

function el<K extends keyof HTMLElementTagNameMap>(tag:K, className="", text="") {
  const e=document.createElement(tag);
  if(className) e.className=className;
  if(text) e.textContent=text;
  return e;
}

// 戦闘画面。onEnd("win") で勝利、onEnd("lose") でハートが0になった。
// equipped が渡されて実際に出題可能なら装備中トピックから出題し、無ければ分数の加法・減法にフォールバックする。
export async function openBattle(enemyName:string, onEnd:(result:"win"|"lose")=>void, equipped?:EquippedTopic) {
  const nextQuestion=async ():Promise<Question> => {
    if(equipped){
      const q=await makeQuestionForEquippedTopic(equipped);
      if(q) return q;
    }
    return makeFractionQuestion();
  };

  const first=await nextQuestion();
  const enemies:Enemy[]=[{ name:enemyName, question:first, weak:false, hearts:ENEMY_HEARTS }];
  const weakQ=pickWeakQuestion(first.id);
  if(weakQ) enemies.push({ name:`苦手な${enemyName}`, question:weakQ, weak:true, hearts:ENEMY_HEARTS });
  let hearts=MAX_HEARTS;
  let locked=false;

  const overlay=el("div","se-overlay se-battle");
  Object.assign(overlay.style,{display:"flex",zIndex:"16000"});
  const card=el("div","se-card");
  card.style.maxWidth="420px";
  const head=el("div","se-heading");
  const heartRow=el("div","se-battle-hearts");
  const book=el("div","se-battle-enemies",`魔法書：${first.topic}`);
  const enemyRow=el("div","se-battle-enemies");
  const prompt=el("div","se-battle-prompt");
  const choiceBox=el("div","se-battle-choices");
  const message=el("div","se-message se-battle-message");
  const actions=el("div","se-actions");
  const unknownBtn=el("button","se-btn","わからん");
  unknownBtn.type="button";
  const nextBtn=el("button","se-btn is-primary","つぎへ");
  nextBtn.type="button";
  actions.append(unknownBtn,nextBtn);
  card.append(head,book,heartRow,enemyRow,prompt,choiceBox,message,actions);
  overlay.appendChild(card);
  document.body.appendChild(overlay);

  const close=(result:"win"|"lose")=>{ overlay.remove(); onEnd(result); };
  const renderHearts=()=>{ heartRow.textContent="♥".repeat(hearts)+"♡".repeat(MAX_HEARTS-hearts); };
  const renderEnemies=()=>{ enemyRow.textContent=enemies.map(e=>`${e.name} ${"♥".repeat(e.hearts)}`).join("　"); };

  let afterNext:()=>void=()=>{};
  const showNext=(fn:()=>void)=>{ afterNext=fn; nextBtn.style.display=""; unknownBtn.style.display="none"; };
  nextBtn.addEventListener("click",()=>afterNext());

  const ask=()=>{
    const enemy=enemies[0];
    locked=false;
    head.textContent=enemy.weak ? `${enemy.name}も現れた！` : `${enemy.name}が現れた！`;
    book.textContent=`魔法書：${enemy.question.topic}`;
    renderHearts(); renderEnemies();
    prompt.textContent=enemy.question.prompt;
    message.textContent="";
    nextBtn.style.display="none"; unknownBtn.style.display="";
    if(enemy.question.inputMode==="text"){
      const input=el("input","se-battle-input");
      input.type="text";
      input.autocomplete="off";
      const submit=el("button","se-btn is-primary","こたえる");
      submit.type="button";
      const row=el("div","se-battle-input-row");
      row.append(input,submit);
      choiceBox.replaceChildren(row);
      const submitFn=()=>{ if(!locked) answerText(input.value); };
      submit.addEventListener("click",submitFn);
      input.addEventListener("keydown",(ev)=>{ if(ev.key==="Enter") submitFn(); });
      setTimeout(()=>input.focus(),0);
    } else {
      choiceBox.replaceChildren(...enemy.question.choices.map((c,i)=>{
        const b=el("button","se-btn",c);
        b.type="button";
        b.addEventListener("click",()=>answer(i));
        return b;
      }));
    }
  };

  const lockChoices=(correct:number,picked:number)=>{
    locked=true;
    [...choiceBox.children].forEach((b,i)=>{
      const btn=b as HTMLButtonElement;
      btn.disabled=true;
      if(i===correct) btn.classList.add("is-primary");
      else if(i===picked) btn.style.textDecoration="line-through";
    });
  };

  const lockInput=()=>{
    locked=true;
    const row=choiceBox.firstElementChild;
    row?.querySelectorAll("input,button").forEach((el)=>((el as HTMLInputElement|HTMLButtonElement).disabled=true));
  };

  const defeat=(text:string)=>{
    const enemy=enemies.shift()!;
    message.textContent=`${text}${enemy.name}をたおした！`;
    renderEnemies();
    showNext(()=>enemies.length>0 ? ask() : close("win"));
  };

  const resolveResult=async (correct:boolean)=>{
    const enemy=enemies[0];
    const q=enemy.question;
    if(correct){
      record(q,"solved");
      enemy.hearts--;
      if(enemy.hearts<=0){ defeat("正解！ "); return; }
      renderEnemies();
      message.textContent=`正解！ ${enemy.name}のハートが1つ減った。`;
      enemy.question=await nextQuestion();
      showNext(ask);
      return;
    }
    record(q,"wrong");
    hearts--;
    renderHearts();
    message.textContent="ちがう！ ハートが1つ減った。";
    if(hearts<=0){
      message.textContent+=" 力尽きた…町に戻される。";
      showNext(()=>close("lose"));
      return;
    }
    // 次の問題（通常の敵は作り直し、苦手枠は同じ問題）
    if(!enemy.weak) enemy.question=await nextQuestion();
    showNext(ask);
  };

  const answer=(i:number)=>{
    if(locked) return;
    const q=enemies[0].question;
    lockChoices(q.answerIndex,i);
    void resolveResult(i===q.answerIndex);
  };

  const answerText=(value:string)=>{
    if(locked) return;
    const q=enemies[0].question;
    const correct=value.trim()===String(q.expectedAnswer ?? "").trim();
    lockInput();
    if(!correct) message.textContent=`正解は ${q.expectedAnswer}。`;
    void resolveResult(correct);
  };

  unknownBtn.addEventListener("click",()=>{
    if(locked) return;
    const q=enemies[0].question;
    const answerLabel=q.inputMode==="text" ? (q.expectedAnswer ?? "") : q.choices[q.answerIndex];
    if(q.inputMode==="text") lockInput(); else lockChoices(q.answerIndex,-1);
    record(q,"unknown");
    message.textContent=`正解は ${answerLabel}。${q.explain} `;
    const enemy=enemies.shift()!;
    message.textContent+=`${enemy.name}をたおした！`;
    renderEnemies();
    showNext(()=>enemies.length>0 ? ask() : close("win"));
  });

  ask();
}

// 問題図鑑（出会った問題、解いた回数・間違えた回数）
export function openQuestionBook() {
  const book=loadBook();
  const entries=Object.values(book).sort((a,b)=>b.lastSeen-a.lastSeen);
  const overlay=el("div","se-overlay");
  Object.assign(overlay.style,{display:"flex",zIndex:"16000"});
  const card=el("div","se-card");
  card.style.maxWidth="440px";
  const head=el("div","se-heading","図鑑");
  // 図鑑の分類。今は学問クイズだけ中身がある（早押しクイズ・パズル・謎解きは今後）
  const tabs=["学問クイズ","早押しクイズ","パズル","謎解き"];
  const tabRow=el("div","se-book-tabs");
  const list=el("div","se-book-list");
  const show=(tab:string)=>{
    [...tabRow.children].forEach(b=>(b as HTMLElement).classList.toggle("is-primary",(b as HTMLElement).textContent===tab));
    const rows=tab==="学問クイズ" ? entries : [];
    if(rows.length===0){ list.replaceChildren(el("div","se-message","まだ出会っていない。")); return; }
    list.replaceChildren(...rows.map(e=>{
      const row=el("div","se-book-row");
      row.append(
        el("div","se-book-prompt",`${e.weak ? "【苦手】" : ""}${e.prompt}`),
        el("div","se-book-answer",`答え ${e.answer}　解いた ${e.solved}回　間違えた ${e.wrong}回`),
        el("div","se-book-explain",e.explain)
      );
      return row;
    }));
  };
  for(const t of tabs){
    const b=el("button","se-btn",t);
    b.type="button";
    b.addEventListener("click",()=>show(t));
    tabRow.appendChild(b);
  }
  show(tabs[0]);
  const actions=el("div","se-actions");
  const closeBtn=el("button","se-btn is-primary","CLOSE");
  closeBtn.type="button";
  closeBtn.addEventListener("click",()=>overlay.remove());
  actions.appendChild(closeBtn);
  card.append(head,tabRow,list,actions);
  overlay.appendChild(card);
  overlay.addEventListener("click",(ev)=>{ if(ev.target===overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}
