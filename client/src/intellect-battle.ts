// 知性バトル（最小版）: 問題づくり・問題図鑑・戦闘画面。
// 最小版は数学「分数の加法・減法」1トピックのみ。問題は型から毎回ランダムに作る。

export type Question = {
  id: string;
  topic: string;
  prompt: string;
  choices: string[];
  answerIndex: number;
  explain: string;
};

type BookEntry = {
  topic: string;
  prompt: string;
  answer: string;
  explain: string;
  solved: number;
  wrong: number;
  weak: boolean;
  lastSeen: number;
};

const BOOK_KEY = "summer-end-3pm-question-book";
const MAX_HEARTS = 3;

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

function loadBook(): Record<string,BookEntry> {
  try { return JSON.parse(localStorage.getItem(BOOK_KEY) || "{}") || {}; } catch { return {}; }
}
function saveBook(book:Record<string,BookEntry>) {
  try { localStorage.setItem(BOOK_KEY, JSON.stringify(book)); } catch { /* 保存できなくても戦闘は続ける */ }
}

function record(q:Question, result:"solved"|"wrong"|"unknown") {
  const book=loadBook();
  const e=book[q.id] ?? { topic:q.topic, prompt:q.prompt, answer:q.choices[q.answerIndex], explain:q.explain, solved:0, wrong:0, weak:false, lastSeen:0 };
  if(result==="solved"){ e.solved++; e.weak=false; }
  else { e.wrong++; e.weak=true; }
  e.lastSeen=Date.now();
  book[q.id]=e;
  saveBook(book);
}

// 苦手枠: 間違えた・わからんだった問題から1つ（選択肢は作り直す）
function pickWeakQuestion(excludeId:string): Question | undefined {
  const book=loadBook();
  const weak=Object.entries(book).filter(([id,e])=>e.weak && id!==excludeId);
  if(weak.length===0) return undefined;
  const [id,e]=weak[rand(0,weak.length-1)];
  const others=Object.values(book).map(x=>x.answer).filter(a=>a!==e.answer);
  const {choices,answerIndex}=buildChoices(e.answer,others.sort(()=>Math.random()-.5));
  return { id, topic:e.topic, prompt:e.prompt, choices, answerIndex, explain:e.explain };
}

type Enemy = { name:string; question:Question; weak:boolean };

function el<K extends keyof HTMLElementTagNameMap>(tag:K, className="", text="") {
  const e=document.createElement(tag);
  if(className) e.className=className;
  if(text) e.textContent=text;
  return e;
}

// 戦闘画面。onEnd("win") で勝利、onEnd("lose") でハートが0になった。
export function openBattle(enemyName:string, onEnd:(result:"win"|"lose")=>void) {
  const first=makeFractionQuestion();
  const enemies:Enemy[]=[{ name:enemyName, question:first, weak:false }];
  const weakQ=pickWeakQuestion(first.id);
  if(weakQ) enemies.push({ name:`苦手な${enemyName}`, question:weakQ, weak:true });
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
  const renderEnemies=()=>{ enemyRow.textContent=enemies.map(e=>e.name).join("　"); };

  let afterNext:()=>void=()=>{};
  const showNext=(fn:()=>void)=>{ afterNext=fn; nextBtn.style.display=""; unknownBtn.style.display="none"; };
  nextBtn.addEventListener("click",()=>afterNext());

  const ask=()=>{
    const enemy=enemies[0];
    locked=false;
    head.textContent=enemy.weak ? `${enemy.name}も現れた！` : `${enemy.name}が現れた！`;
    renderHearts(); renderEnemies();
    prompt.textContent=enemy.question.prompt;
    message.textContent="";
    nextBtn.style.display="none"; unknownBtn.style.display="";
    choiceBox.replaceChildren(...enemy.question.choices.map((c,i)=>{
      const b=el("button","se-btn",c);
      b.type="button";
      b.addEventListener("click",()=>answer(i));
      return b;
    }));
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

  const defeat=(text:string)=>{
    const enemy=enemies.shift()!;
    message.textContent=`${text}${enemy.name}をたおした！`;
    renderEnemies();
    showNext(()=>enemies.length>0 ? ask() : close("win"));
  };

  const answer=(i:number)=>{
    if(locked) return;
    const enemy=enemies[0];
    const q=enemy.question;
    lockChoices(q.answerIndex,i);
    if(i===q.answerIndex){
      record(q,"solved");
      defeat("正解！ ");
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
    if(!enemy.weak) enemy.question=makeFractionQuestion();
    showNext(ask);
  };

  unknownBtn.addEventListener("click",()=>{
    if(locked) return;
    const q=enemies[0].question;
    lockChoices(q.answerIndex,-1);
    record(q,"unknown");
    message.textContent=`正解は ${q.choices[q.answerIndex]}。${q.explain} `;
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
  const head=el("div","se-heading","問題図鑑");
  const list=el("div","se-book-list");
  if(entries.length===0) list.appendChild(el("div","se-message","まだ問題に出会っていない。"));
  for(const e of entries){
    const row=el("div","se-book-row");
    row.append(
      el("div","se-book-prompt",`${e.weak ? "【苦手】" : ""}${e.prompt}`),
      el("div","se-book-answer",`答え ${e.answer}　解いた ${e.solved}回　間違えた ${e.wrong}回`),
      el("div","se-book-explain",e.explain)
    );
    list.appendChild(row);
  }
  const actions=el("div","se-actions");
  const closeBtn=el("button","se-btn is-primary","CLOSE");
  closeBtn.type="button";
  closeBtn.addEventListener("click",()=>overlay.remove());
  actions.appendChild(closeBtn);
  card.append(head,list,actions);
  overlay.appendChild(card);
  overlay.addEventListener("click",(ev)=>{ if(ev.target===overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}
