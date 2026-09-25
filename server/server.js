const http = require("http");
const { WebSocketServer, WebSocket } = require("ws");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT || 8080);
const DEV = process.argv.includes("--dev");
const players = new Map();

const QUIZ_ENABLED = false;
const QUIZ_INTERVAL_MS = 180000;
const QUIZ_DURATION_MS = 20000;
let quizSeq = 0;
let activeQuiz = null;
let lastQuizIndex = -1;
const quizAnswered = new Set();
const QUIZZES = [
  {"q": "ウェストファリア条約が結ばれた年は？", "o": ["1648年", "1618年", "1688年", "1713年"], "a": 0},
  {"q": "『純粋理性批判』の著者は？", "o": ["ヘーゲル", "カント", "スピノザ", "ライプニッツ"], "a": 1},
  {"q": "限界効用逓減とは何が逓減することを指す？", "o": ["追加1単位の消費から得る効用", "総効用", "市場価格", "生産量"], "a": 0},
  {"q": "真核細胞でATP産生の中心となる細胞小器官は？", "o": ["ゴルジ体", "リソソーム", "ミトコンドリア", "中心体"], "a": 2},
  {"q": "ハッブル＝ルメートルの法則が示す基本的関係は？", "o": ["銀河の後退速度と距離", "恒星の質量と寿命", "惑星の周期と半径", "光度と表面温度"], "a": 0},
  {"q": "標準偏差は何の平方根か？", "o": ["平均値", "中央値", "分散", "共分散"], "a": 2},
  {"q": "DNA複製で二本鎖をほどく酵素は？", "o": ["リガーゼ", "ヘリカーゼ", "ポリメラーゼ", "プライマーゼ"], "a": 1},
  {"q": "プレートテクトニクスで海洋地殻が新しく形成される代表的場所は？", "o": ["海溝", "中央海嶺", "大陸棚", "ホットスポットのみ"], "a": 1},
  {"q": "『資本論』第1巻を刊行した人物は？", "o": ["マックス・ウェーバー", "カール・マルクス", "デヴィッド・リカード", "J.S.ミル"], "a": 1},
  {"q": "ローマ帝国が東西に恒久的に分割された395年の皇帝は？", "o": ["コンスタンティヌス1世", "テオドシウス1世", "ユスティニアヌス1世", "ディオクレティアヌス"], "a": 1},
  {"q": "ニュートン力学で力のSI単位Nを基本単位で表すと？", "o": ["kg·m/s", "kg·m/s²", "kg·m²/s²", "kg/s²"], "a": 1},
  {"q": "pHが1低下すると水素イオン活量は概ね何倍になる？", "o": ["2倍", "5倍", "10倍", "100倍"], "a": 2},
  {"q": "比較優位の概念を体系的に示した古典派経済学者は？", "o": ["アダム・スミス", "デヴィッド・リカード", "ケインズ", "マーシャル"], "a": 1},
  {"q": "『存在と時間』の著者は？", "o": ["ハイデガー", "サルトル", "フッサール", "デリダ"], "a": 0},
  {"q": "光合成のカルビン回路が行われる葉緑体の部位は？", "o": ["チラコイド膜", "ストロマ", "外膜", "グラナ内腔"], "a": 1},
  {"q": "地球のマントルと外核の境界は？", "o": ["モホロビチッチ不連続面", "グーテンベルク不連続面", "コンラッド不連続面", "レーマン不連続面"], "a": 1},
  {"q": "モンテスキューが三権分立を論じた著作は？", "o": ["社会契約論", "法の精神", "統治二論", "リヴァイアサン"], "a": 1},
  {"q": "正規分布で平均値から±1標準偏差内に入る確率は約何％？", "o": ["50%", "68%", "95%", "99.7%"], "a": 1},
  {"q": "量子力学の不確定性原理と最も結びつく人物は？", "o": ["ボーア", "ハイゼンベルク", "ディラック", "パウリ"], "a": 1},
  {"q": "『神曲』を書いた詩人は？", "o": ["ペトラルカ", "ダンテ", "ボッカッチョ", "アリオスト"], "a": 1},
  {"q": "言語学でシニフィアンとシニフィエの区別を示した人物は？", "o": ["チョムスキー", "ソシュール", "ヤコブソン", "ブルームフィールド"], "a": 1},
  {"q": "細胞周期でDNA複製が行われる時期は？", "o": ["G1期", "S期", "G2期", "M期"], "a": 1},
  {"q": "国際単位系で電気抵抗の単位は？", "o": ["テスラ", "オーム", "ファラド", "ウェーバ"], "a": 1},
  {"q": "ケッペンの気候区分でAfが表す気候は？", "o": ["熱帯雨林気候", "サバナ気候", "地中海性気候", "西岸海洋性気候"], "a": 0},
  {"q": "日本国憲法で内閣総理大臣を指名する機関は？", "o": ["最高裁判所", "国会", "内閣", "天皇"], "a": 1},
  {"q": "『プロテスタンティズムの倫理と資本主義の精神』の著者は？", "o": ["デュルケーム", "ウェーバー", "ジンメル", "パーソンズ"], "a": 1},
  {"q": "恒星のスペクトル型を高温から低温へ並べたものは？", "o": ["O-B-A-F-G-K-M", "A-B-F-G-K-M-O", "M-K-G-F-A-B-O", "O-A-B-G-F-K-M"], "a": 0},
  {"q": "酸化還元反応で酸化とは何を失うことか？", "o": ["陽子", "中性子", "電子", "原子核"], "a": 2},
  {"q": "ベイズの定理で事前確率をデータ観測後に更新した確率は？", "o": ["周辺確率", "事後確率", "尤度", "有意水準"], "a": 1},
  {"q": "『方法序説』で「我思う、ゆえに我あり」を提示した哲学者は？", "o": ["デカルト", "ロック", "ヒューム", "ベーコン"], "a": 0},
  {"q": "建築の三原則「用・強・美」の源流となる古代ローマの建築家は？", "o": ["ウィトルウィウス", "ブルネレスキ", "パッラーディオ", "アルベルティ"], "a": 0},
  {"q": "RNAでDNAのチミンに対応する塩基は？", "o": ["シトシン", "ウラシル", "グアニン", "アデニン"], "a": 1},
  {"q": "地球の自転によるコリオリ力で北半球の運動物体は進行方向のどちらへ偏向する？", "o": ["左", "右", "赤道側のみ", "偏向しない"], "a": 1},
  {"q": "ゲーム理論の「囚人のジレンマ」が示す典型的問題は？", "o": ["個人合理性と集団最適の不一致", "完全情報下で均衡が存在しないこと", "効用を比較できないこと", "市場価格が必ずゼロになること"], "a": 0},
  {"q": "『一般理論』で有効需要を重視した経済学者は？", "o": ["ケインズ", "ハイエク", "フリードマン", "ワルラス"], "a": 0},
  {"q": "フランス革命でバスティーユ襲撃が起きた年は？", "o": ["1776年", "1789年", "1793年", "1815年"], "a": 1},
  {"q": "論理学で「PならばQ」と「Qでない」から導けるのは？", "o": ["P", "Pでない", "Q", "PかつQ"], "a": 1},
  {"q": "エントロピー増大則は熱力学第何法則？", "o": ["第0法則", "第1法則", "第2法則", "第3法則"], "a": 2},
  {"q": "生態学で一次生産者に該当するものは？", "o": ["植物", "草食動物", "肉食動物", "分解者のみ"], "a": 0},
  {"q": "『国富論』の著者は？", "o": ["アダム・スミス", "リカード", "マルサス", "ケネー"], "a": 0},
  {"q": "認知心理学でワーキングメモリモデルを提唱した代表的人物は？", "o": ["バドリー", "スキナー", "パブロフ", "ロジャーズ"], "a": 0},
  {"q": "印象派という名称の由来となった『印象・日の出』の作者は？", "o": ["ルノワール", "モネ", "ドガ", "セザンヌ"], "a": 1},
  {"q": "マグナ・カルタが成立した年は？", "o": ["1066年", "1215年", "1453年", "1689年"], "a": 1},
  {"q": "地球大気の対流圏と成層圏の境界は？", "o": ["圏界面", "電離層", "磁気圏", "雪線"], "a": 0},
  {"q": "タンパク質の一次構造とは？", "o": ["アミノ酸配列", "αヘリックスのみ", "サブユニット間結合", "立体構造全体"], "a": 0},
  {"q": "TCP/IPでIPが主に担う機能は？", "o": ["経路選択とパケット配送", "暗号化", "名前解決", "ファイル圧縮"], "a": 0},
  {"q": "公開鍵暗号で一般に秘密鍵について正しいのは？", "o": ["全員に公開する", "所有者が秘匿する", "CAだけが生成できる", "毎パケット公開する"], "a": 1},
  {"q": "データベースの第1正規形が基本的に要求することは？", "o": ["各属性値を原子的にする", "全ての表を1列にする", "外部キーを禁止する", "主キーを複合キーにする"], "a": 0},
  {"q": "計算量O(log n)の代表例は？", "o": ["線形探索", "二分探索", "バブルソート", "全順列列挙"], "a": 1},
  {"q": "OSI参照モデルでルーティングを主に扱う層は？", "o": ["データリンク層", "ネットワーク層", "トランスポート層", "セッション層"], "a": 1},
  {"q": "ルネサンス期の『君主論』の著者は？", "o": ["マキャヴェリ", "ホッブズ", "ボダン", "エラスムス"], "a": 0},
  {"q": "宗教改革で「95か条の論題」を発表した人物は？", "o": ["カルヴァン", "ルター", "ツヴィングリ", "エラスムス"], "a": 1},
  {"q": "仏教の四諦で苦の原因を示すものは？", "o": ["苦諦", "集諦", "滅諦", "道諦"], "a": 1},
  {"q": "イスラーム暦の起点となるヒジュラは西暦何年？", "o": ["570年", "610年", "622年", "632年"], "a": 2},
  {"q": "『リヴァイアサン』で社会契約を論じた哲学者は？", "o": ["ホッブズ", "ロック", "ルソー", "バーク"], "a": 0},
  {"q": "功利主義の「最大多数の最大幸福」と特に結びつく人物は？", "o": ["ベンサム", "カント", "ニーチェ", "ロールズ"], "a": 0},
  {"q": "ロールズの『正義論』で用いられる思考実験は？", "o": ["無知のヴェール", "洞窟の比喩", "中国語の部屋", "囚人のジレンマ"], "a": 0},
  {"q": "社会学で「アノミー」概念を自殺研究に用いた人物は？", "o": ["デュルケーム", "マートン", "ゴフマン", "ブルデュー"], "a": 0},
  {"q": "心理学で古典的条件づけの研究で知られる人物は？", "o": ["パブロフ", "スキナー", "バンデューラ", "ピアジェ"], "a": 0},
  {"q": "ピアジェの発達段階で抽象的・仮説的思考が可能になる段階は？", "o": ["感覚運動期", "前操作期", "具体的操作期", "形式的操作期"], "a": 3},
  {"q": "メンデルの分離の法則が直接扱うのは？", "o": ["対立遺伝子が配偶子形成時に分かれること", "DNAが半保存的に複製すること", "突然変異が一定率で起こること", "自然選択が集団に働くこと"], "a": 0},
  {"q": "自然選択による進化論を『種の起源』で論じた人物は？", "o": ["ダーウィン", "ラマルク", "メンデル", "モーガン"], "a": 0},
  {"q": "地質年代で恐竜が絶滅したK-Pg境界は約何年前？", "o": ["660万年前", "6600万年前", "2億年前", "5億年前"], "a": 1},
  {"q": "モホロビチッチ不連続面は何と何の境界か？", "o": ["地殻とマントル", "マントルと外核", "外核と内核", "対流圏と成層圏"], "a": 0},
  {"q": "海水の平均塩分は概ね何％？", "o": ["0.35%", "1.5%", "3.5%", "10%"], "a": 2},
  {"q": "太陽のエネルギー源の中心的反応は？", "o": ["核分裂", "水素の核融合", "化学燃焼", "重力収縮のみ"], "a": 1},
  {"q": "ブラックホールの事象の地平面とは？", "o": ["そこより内側から光も脱出できない境界", "物質が必ず固体化する面", "銀河の外縁", "恒星の光球"], "a": 0},
  {"q": "特殊相対性理論で真空中の光速について正しいのは？", "o": ["慣性系によらず一定", "観測者の速度と単純加算される", "光源の質量で決まる", "周波数が高いほど速い"], "a": 0},
  {"q": "電磁誘導の法則と最も結びつく人物は？", "o": ["ファラデー", "クーロン", "オーム", "ボルタ"], "a": 0},
  {"q": "原子番号は原子核中の何の数で決まる？", "o": ["中性子", "陽子", "電子殻", "核子総数"], "a": 1},
  {"q": "アボガドロ定数は約いくつ？", "o": ["6.02×10²³ mol⁻¹", "9.81×10² mol⁻¹", "3.00×10⁸ mol⁻¹", "1.38×10⁻²³ mol⁻¹"], "a": 0},
  {"q": "共有結合は主に何によって形成される？", "o": ["電子対の共有", "陽子の交換", "中性子の共有", "原子核の融合"], "a": 0},
  {"q": "微分積分学の基本定理が結びつける二つの操作は？", "o": ["微分と積分", "加法と乗法", "対数と指数", "行列とベクトル"], "a": 0},
  {"q": "行列式が0の正方行列について正しいのは？", "o": ["逆行列を持たない", "必ず単位行列である", "固有値を持たない", "全要素が0である"], "a": 0},
  {"q": "確率変数Xの期待値E[X]は何を表すか？", "o": ["長期反復における平均的値", "必ず最頻値", "必ず中央値", "標準偏差の二乗"], "a": 0},
  {"q": "相関係数が0であることから一般に言えるのは？", "o": ["線形相関がない", "独立である", "因果関係がない", "同じ分布である"], "a": 0},
  {"q": "帰無仮説が正しいのに棄却する誤りは？", "o": ["第1種の誤り", "第2種の誤り", "標本誤差ではない", "交互作用"], "a": 0},
  {"q": "GDPの支出面で通常含まれないものは？", "o": ["家計消費", "民間投資", "政府支出", "中古品そのものの売買額"], "a": 3},
  {"q": "中央銀行が政策金利を引き上げると、他条件一定で一般に期待される方向は？", "o": ["需要抑制", "需要刺激", "通貨供給の無限増加", "税率の自動低下"], "a": 0},
  {"q": "貸借対照表で資産＝負債＋何か？", "o": ["純資産", "売上高", "営業利益", "キャッシュフロー"], "a": 0},
  {"q": "減価償却の主な会計上の意味は？", "o": ["固定資産の取得原価を耐用期間に配分する", "現金を積み立てる", "負債を免除する", "売上を繰り延べる"], "a": 0},
  {"q": "株式会社で株主の責任は原則として？", "o": ["出資額を限度とする有限責任", "会社債務への無限責任", "取締役と同じ責任", "国が全て負担"], "a": 0},
  {"q": "日本の民法で契約自由の原則に含まれる考え方は？", "o": ["契約締結の自由", "刑罰制定の自由", "裁判拒否の自由", "納税拒否の自由"], "a": 0},
  {"q": "日本の刑法で「罪刑法定主義」が要求する核心は？", "o": ["犯罪と刑罰をあらかじめ法律で定める", "裁判官が自由に犯罪を新設する", "慣習だけで刑罰を科す", "行政命令を法律より常に優先する"], "a": 0},
  {"q": "国際連合安全保障理事会の常任理事国はいくつ？", "o": ["4か国", "5か国", "6か国", "10か国"], "a": 1},
  {"q": "冷戦期のNATO設立年は？", "o": ["1945年", "1949年", "1955年", "1961年"], "a": 1},
  {"q": "明治維新後、廃藩置県が行われた年は？", "o": ["1868年", "1871年", "1877年", "1889年"], "a": 1},
  {"q": "大日本帝国憲法が発布された年は？", "o": ["1871年", "1881年", "1889年", "1894年"], "a": 2},
  {"q": "鎌倉幕府が御家人統制のため1232年に制定した法は？", "o": ["御成敗式目", "武家諸法度", "公事方御定書", "養老律令"], "a": 0},
  {"q": "中国史で科挙を本格的に制度化した王朝は？", "o": ["秦", "隋", "元", "清"], "a": 1},
  {"q": "三国時代の魏で九品官人法を創設した人物は？", "o": ["陳羣", "司馬遷", "董仲舒", "王安石"], "a": 0},
  {"q": "古代ギリシアで『歴史』を書き「歴史の父」と呼ばれる人物は？", "o": ["ヘロドトス", "トゥキュディデス", "クセノフォン", "ポリュビオス"], "a": 0},
  {"q": "プラトンの『国家』で哲学的認識を説明する有名な比喩は？", "o": ["洞窟の比喩", "蜜蜂の寓話", "船のテセウス", "見えざる手"], "a": 0},
  {"q": "アリストテレスが論理学で体系化した代表的推論形式は？", "o": ["三段論法", "帰納法のみ", "弁証法的唯物論", "反証主義"], "a": 0},
  {"q": "20世紀美術のキュビスムを代表する画家は？", "o": ["ピカソ", "モネ", "クリムト", "カンディンスキー"], "a": 0},
  {"q": "バウハウスを1919年に創設した建築家は？", "o": ["ヴァルター・グロピウス", "ル・コルビュジエ", "ミース・ファン・デル・ローエ", "フランク・ロイド・ライト"], "a": 0},
  {"q": "遠近法で平行線が収束して見える点を何という？", "o": ["消失点", "焦点", "中点", "黄金点"], "a": 0},
  {"q": "音楽理論で平均律の1オクターブは何個の半音に分かれる？", "o": ["8", "10", "12", "16"], "a": 2},
  {"q": "文学で『カラマーゾフの兄弟』の作者は？", "o": ["トルストイ", "ドストエフスキー", "ツルゲーネフ", "チェーホフ"], "a": 1},
  {"q": "『百年の孤独』の作者は？", "o": ["ボルヘス", "ガルシア＝マルケス", "ネルーダ", "バルガス＝リョサ"], "a": 1}
];

function startTownQuiz() {
  if (!QUIZ_ENABLED) return;
  if (activeQuiz || wss.clients.size === 0) return;
  let quizIndex;
  do { quizIndex = Math.floor(Math.random()*QUIZZES.length); }
  while (QUIZZES.length > 1 && quizIndex === lastQuizIndex);
  lastQuizIndex = quizIndex;
  const item = QUIZZES[quizIndex];
  activeQuiz = { id:String(++quizSeq), item };
  quizAnswered.clear();
  broadcastMap("yunagicho",{type:"town_quiz",id:activeQuiz.id,question:item.q,options:item.o,durationMs:QUIZ_DURATION_MS});
  setTimeout(()=>{
    if(!activeQuiz) return;
    const id=activeQuiz.id;
    activeQuiz=null;
    quizAnswered.clear();
    broadcastMap("yunagicho",{type:"quiz_closed",id});
  },QUIZ_DURATION_MS);
}


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

function randomColor() {
  const colors = [0xf87171, 0x60a5fa, 0xfacc15, 0xa78bfa, 0x34d399, 0xfb923c];
  return colors[Math.floor(Math.random() * colors.length)];
}

function sendJson(socket, data) {
  if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data));
}

function broadcastAll(data, except) {
  const text = JSON.stringify(data);
  for (const client of wss.clients) {
    if (client !== except && client.readyState === WebSocket.OPEN) client.send(text);
  }
}

function broadcastMap(map, data, except) {
  const text = JSON.stringify(data);
  for (const client of wss.clients) {
    if (client === except || client.readyState !== WebSocket.OPEN) continue;
    const pid = client.playerId;
    const target = pid ? players.get(pid) : null;
    if (target?.map === map) client.send(text);
  }
}

function serveStatic(req, res) {
  if (DEV) {
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("なんとかOnline WebSocket dev server");
    return;
  }

  const dist = path.join(__dirname, "..", "dist");
  const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
  let filePath = path.join(dist, urlPath === "/" ? "index.html" : urlPath);

  // Prevent traversal outside dist.
  const normalizedDist = path.resolve(dist);
  filePath = path.resolve(filePath);
  if (!filePath.startsWith(normalizedDist)) {
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
const wss = new WebSocketServer({ server });

wss.on("connection", (socket) => {
  socket.isAlive = true;
  socket.on("pong",()=>{ socket.isAlive = true; });

  const id = Math.random().toString(36).slice(2, 10);
  let joined = false;
  socket.playerId = id;

  const player = {
    id,
    x: 820 + Math.floor(Math.random() * 80),
    y: 520 + Math.floor(Math.random() * 80),
    color: 0x60a5fa,
    name: "WALKER",
    height: 1,
    money: 0,
    map: "yunagicho",
  };

  socket.on("message", (raw) => {
    let msg;
    try {
      msg = JSON.parse(String(raw));
    } catch {
      return;
    }

    if (msg.type === "join" && !joined) {
      const allowedColors = [0x60a5fa, 0xf87171, 0x34d399, 0xfacc15, 0xa78bfa, 0xfb923c];
      const name = typeof msg.name === "string" ? msg.name.trim().slice(0, 16) : "WALKER";
      const color = allowedColors.includes(Number(msg.color)) ? Number(msg.color) : 0x60a5fa;
      const height = [0.9, 1, 1.1].includes(Number(msg.height)) ? Number(msg.height) : 1;

      player.name = name || "WALKER";
      player.color = color;
      player.height = height;
      const requestedJoinMap =
        msg.map === "komorebi" ? "komorebi" :
        msg.map === "convenience" ? "convenience" :
        "yunagicho";
      player.map = requestedJoinMap;
      if (Number.isFinite(msg.x)) player.x = Math.max(20, Math.min(1520, Number(msg.x)));
      if (Number.isFinite(msg.y)) player.y = Math.max(20, Math.min(848, Number(msg.y)));
      player.race =
        msg.race === "ancient-robot" ? "ancient-robot" :
        msg.race === "rabbit-jk" ? "rabbit-jk" :
        "teddy";
      joined = true;
      players.set(id, player);

      socket.send(JSON.stringify({ type: "welcome", id, player }));
      socket.send(JSON.stringify({ type: "money", amount: player.money }));
      socket.send(JSON.stringify({
        type: "snapshot",
        players: [...players.values()].filter((p) => p.id !== id && p.map === player.map)
      }));
      broadcastMap(player.map,{ type: "join", player }, socket);
      if(QUIZ_ENABLED && activeQuiz && player.map==="yunagicho"){
        socket.send(JSON.stringify({type:"town_quiz",id:activeQuiz.id,question:activeQuiz.item.q,options:activeQuiz.item.o,durationMs:QUIZ_DURATION_MS}));
      }
      return;
    }

    if (!joined) return;

    if (msg.type === "heartbeat") {
      sendJson(socket,{
        type:"heartbeat_ack",
        ts:Date.now(),
        map:player.map,
        players:[...players.values()].filter(p=>p.id!==id && p.map===player.map)
      });
      return;
    }

    if (msg.type === "quiz_answer") {
      if (!QUIZ_ENABLED) return;
      if (player.map !== "yunagicho") return;
      if (!activeQuiz || String(msg.id) !== activeQuiz.id || quizAnswered.has(id)) return;
      const answer = Number(msg.answer);
      if (!Number.isInteger(answer) || answer < 0 || answer > 3) return;
      quizAnswered.add(id);
      const correct = answer === activeQuiz.item.a;
      if (correct) player.money += 100;
      socket.send(JSON.stringify({type:"quiz_result",id:activeQuiz.id,correct,
        correctText:activeQuiz.item.o[activeQuiz.item.a],money:player.money}));
      return;
    }

    if (msg.type === "chat") {
      const text = typeof msg.text === "string" ? msg.text.trim().slice(0, 80) : "";
      if (!text) return;
      broadcastMap(player.map,{ type: "chat", id, text }, socket);
      return;
    }

    if (msg.type !== "move") return;
    if (!Number.isFinite(msg.x) || !Number.isFinite(msg.y)) return;

    const requestedMap = msg.map === "komorebi" ? "komorebi" : msg.map === "convenience" ? "convenience" : msg.map === "yunagicho" ? "yunagicho" : player.map;
    const oldMap = player.map;
    if (requestedMap !== oldMap) {
      // The client only requests a map change at the authored portals.
      broadcastMap(oldMap,{type:"leave",id},socket);
      player.map = requestedMap;
      player.x = Math.max(20, Math.min(1520, msg.x));
      player.y = Math.max(20, Math.min(848, msg.y));
      sendJson(socket,{type:"map_snapshot",map:player.map,
        players:[...players.values()].filter(p=>p.id!==id && p.map===player.map)});
      broadcastMap(player.map,{type:"join",player},socket);
      if(QUIZ_ENABLED && player.map==="yunagicho" && activeQuiz){
        sendJson(socket,{type:"town_quiz",id:activeQuiz.id,question:activeQuiz.item.q,
          options:activeQuiz.item.o,durationMs:QUIZ_DURATION_MS});
      }
      return;
    }

    player.x = Math.max(20, Math.min(1520, msg.x));
    player.y = Math.max(20, Math.min(848, msg.y));
    broadcastMap(player.map,{ type: "move", id, x: player.x, y: player.y, map:player.map }, socket);
  });

  socket.on("close", () => {
    if (!joined) return;
    players.delete(id);
    broadcastMap(player.map,{ type: "leave", id });
  });
});

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

wss.on("close",()=>clearInterval(websocketKeepAlive));

if (QUIZ_ENABLED) {
  setTimeout(startTownQuiz, 15000);
  setInterval(startTownQuiz, QUIZ_INTERVAL_MS);
}

server.listen(PORT, "0.0.0.0", () => {
  console.log("");
  console.log("なんとかOnline β 0.47");
  console.log(`Server: http://localhost:${PORT}`);
  console.log(`Mode: ${DEV ? "development websocket-only" : "production single-URL"}`);
  if (!DEV) {
    console.log("Game + WebSocket are served from the same port.");
  }
  console.log("");
});
