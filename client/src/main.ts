import Phaser from "phaser";

const isViteDev = location.port === "5173";
const SERVER_URL = isViteDev
  ? `ws://${location.hostname}:8080`
  : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`;

type MapId = "yunagicho" | "komorebi" | "convenience";
type MapAudioConfig = { bgmKey: string | null; ambienceKeys: string[] };
type MapDefinition = { name: string; texture: string; quiz: boolean; audio: MapAudioConfig };
type PlayerState = { id: string; x: number; y: number; color: number; name: string; height: number; race: string; map?: MapId };

class WalkScene extends Phaser.Scene {
  private meId = "";
  private me?: Phaser.GameObjects.Container;
  private others = new Map<string, Phaser.GameObjects.Container>();
  private cursors?: Phaser.Types.Input.Keyboard.CursorKeys;
  private keys?: Record<string, Phaser.Input.Keyboard.Key>;
  private socket?: WebSocket;
  private reconnectTimer?: number;
  private heartbeatTimer?: number;
  private reconnectAttempts = 0;
  private lastHeartbeatAck = 0;
  private lastSent = 0;

  private joystick = { active:false, pointerId:-1, originX:0, originY:0, dx:0, dy:0 };
  private chatInput?: HTMLInputElement;
  private chatLog?: HTMLDivElement;
  private chatLines: string[] = [];
  private coordHud?: HTMLDivElement;
  private coordsVisible = (
    localStorage.getItem("nantoka-show-coords") ??
    localStorage.getItem("vw-show-coords") ??
    "1"
  ) !== "0";
  private playerName = "WALKER";
  private playerColor = 0x60a5fa;
  private playerHeight = 1;
  private playerRace = "teddy";
  private loginOpen = true;
  private money = 0;
  private moneyHud?: HTMLDivElement;
  private quizPanel?: HTMLDivElement;
  private activeQuizId: string | null = null;
  private rectBlockers: Phaser.Geom.Rectangle[] = [];
  private circleBlockers: Phaser.Geom.Circle[] = [];
  private polygonBlockers: Phaser.Geom.Polygon[] = [];
  private currentMap: MapId = "yunagicho";
  private background?: Phaser.GameObjects.Image;
  private mapTitle?: Phaser.GameObjects.Text;
  private transitionLock = false;
  private activeMapBgm?: Phaser.Sound.BaseSound;
  private activeMapAmbience: Phaser.Sound.BaseSound[] = [];

  // 今後、環境音/BGMファイルを追加したらここへ key -> URL を登録する。
  private readonly audioAssets: Record<string,string> = {};

  // 種族固有の隠しパラメータ。UIには表示しない。
  // テディぐまを基準速度とし、いにしえロボットは「気持ちだけ」速い。
  private readonly raceData = {
    teddy: {
      texturePrefix:"teddy",
      moveSpeed:168,
      sizeClass:"standard",
      visualScale:1.0
    },
    "ancient-robot": {
      texturePrefix:"ancient-robot",
      moveSpeed:176,
      sizeClass:"standard",
      visualScale:1.0
    },
    "rabbit-jk": {
      texturePrefix:"rabbit-jk",
      moveSpeed:168,
      sizeClass:"standard",
      visualScale:1.0
    }
  } as const;

  private readonly mapData: Record<MapId,MapDefinition> = {
    yunagicho: {
      name:"夕凪町", texture:"yunagicho-field", quiz:false,
      audio:{ bgmKey:null, ambienceKeys:[] }
    },
    komorebi: {
      name:"木漏れ日神社", texture:"komorebi-field", quiz:false,
      audio:{ bgmKey:null, ambienceKeys:[] }
    },
    convenience: {
      name:"コンビニ", texture:"convenience-field", quiz:false,
      audio:{ bgmKey:null, ambienceKeys:[] }
    }
  };

  constructor() { super("walk"); }

  private getRaceData(race:string) {
    if(race === "ancient-robot") return this.raceData["ancient-robot"];
    if(race === "rabbit-jk") return this.raceData["rabbit-jk"];
    return this.raceData.teddy;
  }

  private installInputIsolation() {
    const isEditor=(el: EventTarget | null)=>{
      const h=el as HTMLElement | null;
      return !!h && (h.tagName==="INPUT" || h.tagName==="TEXTAREA" || h.isContentEditable);
    };
    document.addEventListener("focusin",(e)=>{
      if(isEditor(e.target) && this.input.keyboard){
        this.input.keyboard.resetKeys();
        this.input.keyboard.enabled=false;
      }
    });
    document.addEventListener("focusout",(e)=>{
      if(isEditor(e.target) && this.input.keyboard){
        this.input.keyboard.resetKeys();
        this.input.keyboard.enabled=true;
      }
    });
  }

  preload() {
    this.load.image("yunagicho-field", "/yunagicho.png");
    this.load.image("komorebi-field", "/komorebi-jinja.png");
    this.load.image("convenience-field", "/convenience-store.png");
    (["down","left","right","up"] as const).forEach(dir=>{
      for(let i=0;i<7;i++){
        this.load.image(`teddy-${dir}-${i}`,`/sprites/runtime/teddy/${dir}-${i}.png`);
        this.load.image(`ancient-robot-${dir}-${i}`,`/sprites/runtime/ancient-robot/${dir}-${i}.png`);
        this.load.image(`rabbit-jk-${dir}-${i}`,`/sprites/runtime/rabbit-jk/${dir}-${i}.png`);
      }
    });
    for(const [key,url] of Object.entries(this.audioAssets)) {
      this.load.audio(key,url);
    }
  }

  create() {
    this.installInputIsolation();
    this.cameras.main.setBackgroundColor("#c88f72");
    this.setupImageField();

    if (this.input.keyboard) {
      this.cursors = {
        up: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.UP, false),
        down: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.DOWN, false),
        left: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.LEFT, false),
        right: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.RIGHT, false),
        space: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE, false),
        shift: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SHIFT, false)
      } as Phaser.Types.Input.Keyboard.CursorKeys;
    }
    if (this.input.keyboard) {
      this.keys = this.input.keyboard.addKeys("W,A,S,D", false) as Record<string, Phaser.Input.Keyboard.Key>;
    this.input.keyboard.removeCapture([
      Phaser.Input.Keyboard.KeyCodes.W, Phaser.Input.Keyboard.KeyCodes.A,
      Phaser.Input.Keyboard.KeyCodes.S, Phaser.Input.Keyboard.KeyCodes.D,
      Phaser.Input.Keyboard.KeyCodes.UP, Phaser.Input.Keyboard.KeyCodes.DOWN,
      Phaser.Input.Keyboard.KeyCodes.LEFT, Phaser.Input.Keyboard.KeyCodes.RIGHT,
      Phaser.Input.Keyboard.KeyCodes.SPACE
    ]);
    }

    this.setupTouchControls();
    this.setupLogin();
    this.setupCollisionMap();

    this.mapTitle = this.add.text(18, 18, "夕凪町　18:42　β 0.47", {
      fontFamily: "serif", fontSize: "18px", color: "#fff4df",
      backgroundColor: "#2b243088", padding: { x:10, y:7 }
    }).setScrollFactor(0).setDepth(1000);

    const hint = this.add.text(18, 58, "WASD / 矢印　・　スマホは左側をドラッグ", {
      fontFamily: "sans-serif", fontSize: "13px", color: "#f8e8d0",
      backgroundColor: "#2b243066", padding: { x:8, y:5 }
    }).setScrollFactor(0).setDepth(1000);
  }

  private drawWorld() {
    const g = this.add.graphics();

    // Ground / evening grass
    g.fillStyle(0x75856a); g.fillRect(0,0,1800,1200);

    // River
    g.fillStyle(0x536f83); g.fillRect(0,870,1800,230);
    for (let x=20; x<1800; x+=95) {
      g.fillStyle(0x91a6ad, .24); g.fillRect(x, 920 + (x%3)*18, 54, 3);
    }

    // Roads
    g.fillStyle(0xb9a88c); g.fillRect(0,455,1800,175);
    g.fillRect(760,0,190,1200);
    g.fillStyle(0xd6c3a0,.55);
    for(let x=0;x<1800;x+=90) g.fillRect(x,540,45,4);

    // Station platform / tracks
    g.fillStyle(0x4a4646); g.fillRect(0,120,720,92);
    g.fillStyle(0x292a2c); g.fillRect(0,145,720,8); g.fillRect(0,184,720,8);
    g.fillStyle(0xd5c57c); g.fillRect(0,215,720,10);
    this.add.text(55,72,"夕凪駅", {fontFamily:"serif",fontSize:"30px",color:"#eee2c8"});

    // Shopping street buildings
    const buildings = [
      [1030,280,220,150,0x9b6659],[1280,300,180,130,0x776c72],[1490,260,240,170,0x8a725d],
      [1050,660,190,140,0x726c61],[1280,680,230,120,0x8b7868],[1550,650,180,150,0x6f7167]
    ];
    buildings.forEach(([x,y,w,h,c])=>{
      g.fillStyle(c as number); g.fillRect(x as number,y as number,w as number,h as number);
      g.fillStyle(0x463d42); g.fillRect((x as number)+18,(y as number)+42,48,52);
      g.fillStyle(0xe6c783,.55); g.fillRect((x as number)+92,(y as number)+42,48,52);
    });

    // Trees
    const trees = [[170,330],[330,350],[560,340],[1120,850],[1350,845],[1610,840],[300,760],[520,740]];
    trees.forEach(([x,y])=>{
      g.fillStyle(0x4f5849); g.fillRect(x-6,y,12,35);
      g.fillStyle(0x4e684f); g.fillCircle(x,y-8,29);
      g.fillStyle(0x64765a); g.fillCircle(x-12,y-17,17);
    });

    // Bridge
    g.fillStyle(0x8e8173); g.fillRect(735,850,240,270);
    g.fillStyle(0x5c5653); g.fillRect(745,850,8,270); g.fillRect(957,850,8,270);

    // Lamps
    [[990,470],[1260,470],[1510,470],[690,690]].forEach(([x,y])=>{
      g.fillStyle(0x3e3c3d); g.fillRect(x,y,5,58);
      g.fillStyle(0xf3c97b,.25); g.fillCircle(x+2,y,28);
      g.fillStyle(0xffdda0); g.fillCircle(x+2,y,7);
    });

    // Riverside path
    g.fillStyle(0xa89b80); g.fillRect(0,815,1800,55);
    this.add.text(1120,885,"川の音が近い。", {fontFamily:"serif",fontSize:"16px",color:"#d8dfdf",alpha:.65});

    // Evening overlay
    g.fillStyle(0x563f68,.17); g.fillRect(0,0,1800,1200);
  }

  private makePlayer(x:number,y:number,color:number,label:string,height=1,race="teddy") {
    const visual=this.add.container(0,0);

    // 足元をプレイヤー座標そのものに固定。
    // 旧図形キャラ・疑似影は完全撤去し、正式スプライトだけを表示する。
    const raceKey=this.getRaceData(race).texturePrefix;
    const sprite=this.add.image(0,0,`${raceKey}-down-3`).setOrigin(.5,1);
    const raceInfo=this.getRaceData(race);
    const targetHeight=84*raceInfo.visualScale;
    sprite.setScale(targetHeight/sprite.height);
    visual.add(sprite);
    visual.setScale(height);

    const name=this.add.text(0,-88*height,label,{
      fontFamily:"sans-serif",fontSize:"11px",color:"#f8ead8",
      backgroundColor:"#29232d88",padding:{x:4,y:2}
    }).setOrigin(.5);

    const c=this.add.container(x,y,[visual,name]).setDepth(10);
    c.setData("visual",visual);
    c.setData("sprite",sprite);
    c.setData("phase",0);
    c.setData("direction","down");
    c.setData("height",height);
    c.setData("race",race);
    c.setData("playerName",label);
    c.setData("remoteDX",0);
    c.setData("remoteDY",0);
    c.setData("movingUntil",0);
    c.setData("idleAnimating",false);
    c.setData("idleFrame",3);
    c.setData("idleAnimStart",0);
    c.setData("nextIdleAnim",performance.now()+Phaser.Math.Between(4500,11000));
    return c;
  }

  private animateWalker(c:Phaser.GameObjects.Container,moving:boolean,dx=0,dy=0) {
    const sprite=c.getData("sprite") as Phaser.GameObjects.Image | undefined;
    if(!sprite)return;

    let dir=String(c.getData("direction")||"down");
    if(Math.abs(dx)>Math.abs(dy) && dx!==0) dir=dx<0 ? "left" : "right";
    else if(dy!==0) dir=dy<0 ? "up" : "down";
    c.setData("direction",dir);

    const race=String(c.getData("race")||"teddy");
    const raceKey=this.getRaceData(race).texturePrefix;
    let col=3;

    if(moving){
      // 移動中は歩行3コマを継続。
      c.setData("idleAnimating",false);
      const phase=Number(c.getData("phase")||0)+.16;
      c.setData("phase",phase);
      col=[0,1,2][Math.floor(phase)%3];
      // 停止直後にすぐ立ちアニメが始まらないよう次回時刻を取り直す。
      c.setData("nextIdleAnim",performance.now()+Phaser.Math.Between(4500,11000));
    }else{
      const now=performance.now();
      let idleAnimating=Boolean(c.getData("idleAnimating"));
      const nextIdle=Number(c.getData("nextIdleAnim")||0);

      if(!idleAnimating && now>=nextIdle){
        idleAnimating=true;
        c.setData("idleAnimating",true);
        c.setData("idleAnimStart",now);
      }

      if(idleAnimating){
        const elapsed=now-Number(c.getData("idleAnimStart")||now);
        // 約1.2秒だけ 3→4→5→6 と一度アニメーション。
        const step=Math.floor(elapsed/300);
        if(step>=4){
          c.setData("idleAnimating",false);
          c.setData("nextIdleAnim",now+Phaser.Math.Between(4500,11000));
          col=3;
        }else{
          col=[3,4,5,6][step];
        }
      }else{
        // 通常の立ち状態は完全静止。
        col=3;
      }
    }

    const key=`${raceKey}-${dir}-${col}`;
    if(sprite.texture.key!==key){
      sprite.setTexture(key);
      const raceInfo=this.getRaceData(race);
      sprite.setScale((84*raceInfo.visualScale)/sprite.height);
    }
    sprite.setPosition(0,0);
  }


  private showBubble(c: Phaser.GameObjects.Container, text: string) {
    const old = c.getData("bubble") as Phaser.GameObjects.Container | undefined;
    if (old) old.destroy(true);

    const safe = text.trim().slice(0, 80);
    if (!safe) return;

    const h = Number(c.getData("height") || 1);
    const label = this.add.text(0, -78*h, safe, {
      fontFamily: "sans-serif",
      fontSize: "14px",
      color: "#242027",
      backgroundColor: "#fffaf0",
      padding: { x: 8, y: 5 },
      wordWrap: { width: 960, useAdvancedWrap: true },
      align: "center"
    }).setOrigin(0.5, 1);

    const bubble = this.add.container(0, 0, [label]);
    c.add(bubble);
    c.setData("bubble", bubble);

    this.time.delayedCall(5000, () => {
      if (c.getData("bubble") === bubble) {
        bubble.destroy(true);
        c.setData("bubble", undefined);
      }
    });
  }


  private setupLogin() {
    if (this.input.keyboard) this.input.keyboard.enabled = false;
    const overlay = document.createElement("div");
    Object.assign(overlay.style, {
      position:"fixed", inset:"0", zIndex:"20000",
      display:"flex", alignItems:"center", justifyContent:"center",
      background:"rgba(20,18,24,.9)", fontFamily:"sans-serif"
    } as Partial<CSSStyleDeclaration>);

    const panel = document.createElement("div");
    Object.assign(panel.style, {
      width:"min(420px, calc(100vw - 32px))",
      padding:"24px", borderRadius:"16px",
      background:"#2d2933", color:"#fff8e8",
      boxShadow:"0 18px 50px rgba(0,0,0,.35)"
    } as Partial<CSSStyleDeclaration>);

    const title = document.createElement("div");
    title.textContent = "夕凪町へ";
    Object.assign(title.style, {
      fontSize:"26px", fontWeight:"700", marginBottom:"18px"
    });

    const nameLabel = document.createElement("label");
    nameLabel.textContent = "名前";
    nameLabel.style.display = "block";
    nameLabel.style.marginBottom = "6px";

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.maxLength = 16;
    nameInput.placeholder = "名前を入力";
    Object.assign(nameInput.style, {
      width:"100%", height:"42px", boxSizing:"border-box",
      marginBottom:"18px", borderRadius:"10px",
      border:"1px solid rgba(255,255,255,.2)",
      background:"#211e27", color:"#fff",
      padding:"0 12px", fontSize:"16px", outline:"none"
    } as Partial<CSSStyleDeclaration>);

    const raceLabel=document.createElement("div");
    raceLabel.textContent="種族";
    raceLabel.style.marginBottom="8px";

    const raceRow=document.createElement("div");
    Object.assign(raceRow.style,{
      display:"grid",gridTemplateColumns:"repeat(3, 1fr)",gap:"8px",marginBottom:"18px"
    } as Partial<CSSStyleDeclaration>);
    let selectedColor=0x60a5fa;
    let selectedRace="teddy";
    const raceButtons: HTMLButtonElement[]=[];
    [
      {label:"テディぐま",value:"teddy"},
      {label:"いにしえロボット",value:"ancient-robot"},
      {label:"うさぎjk",value:"rabbit-jk"}
    ].forEach((item,idx)=>{
      const b=document.createElement("button");
      b.type="button";
      b.textContent=item.label;
      Object.assign(b.style,{
        height:"48px",borderRadius:"10px",
        border:idx===0 ? "2px solid #fff" : "2px solid rgba(255,255,255,.15)",
        background:"#211e27",color:"#fff8e8",
        fontSize:"14px",fontWeight:"700",cursor:"pointer"
      } as Partial<CSSStyleDeclaration>);
      b.onclick=()=>{
        selectedRace=item.value;
        raceButtons.forEach(x=>x.style.border="2px solid rgba(255,255,255,.15)");
        b.style.border="2px solid #fff";
      };
      raceButtons.push(b);
      raceRow.appendChild(b);
    });

    const heightLabel = document.createElement("div");
    heightLabel.textContent = "背の高さ";
    heightLabel.style.marginBottom = "8px";

    const heightRow = document.createElement("div");
    Object.assign(heightRow.style, {
      display:"grid", gridTemplateColumns:"repeat(3, 1fr)",
      gap:"8px", marginBottom:"20px"
    } as Partial<CSSStyleDeclaration>);

    let selectedHeight = 1;
    const heightButtons: HTMLButtonElement[] = [];
    [
      {label:"低め", value:.9},
      {label:"ふつう", value:1},
      {label:"高め", value:1.1}
    ].forEach((item, idx) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = item.label;
      Object.assign(b.style, {
        height:"42px", borderRadius:"10px",
        border: idx===1 ? "2px solid #fff" : "2px solid rgba(255,255,255,.15)",
        background:"#211e27", color:"#fff8e8",
        fontSize:"14px", cursor:"pointer"
      } as Partial<CSSStyleDeclaration>);
      b.onclick = () => {
        selectedHeight = item.value;
        heightButtons.forEach(x => x.style.border = "2px solid rgba(255,255,255,.15)");
        b.style.border = "2px solid #fff";
      };
      heightButtons.push(b);
      heightRow.appendChild(b);
    });

    const start = document.createElement("button");
    start.type = "button";
    start.textContent = "散歩をはじめる";
    Object.assign(start.style, {
      width:"100%", height:"46px", border:"0",
      borderRadius:"12px", background:"#f2e7c8",
      color:"#242027", fontSize:"16px",
      fontWeight:"700", cursor:"pointer"
    } as Partial<CSSStyleDeclaration>);

    const begin = () => {
      const entered = nameInput.value.trim();
      this.playerName = entered || "WALKER";
      this.playerColor = selectedColor;
      this.playerHeight = selectedHeight;
      this.playerRace = selectedRace;
      overlay.remove();
      this.loginOpen = false;
      if (this.input.keyboard) this.input.keyboard.enabled = true;
      this.setupChat();
      this.applyMapAudio();
      this.setupOptions();
      this.setupMoneyHud();
      // 教養クイズは一時停止中。UIを生成しない。
      this.connect();
    };

    start.onclick = begin;
    nameInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") begin();
    });

    panel.append(
      title, nameLabel, nameInput,
      raceLabel, raceRow,
      heightLabel, heightRow,
      start
    );
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    nameInput.focus();
  }

  private setupChatLog() {
    const log=document.createElement("div");
    Object.assign(log.style,{
      position:"fixed",left:"18px",bottom:"76px",zIndex:"9998",
      width:"min(430px, calc(100vw - 36px))",minHeight:"58px",maxHeight:"142px",
      overflow:"hidden",boxSizing:"border-box",padding:"9px 12px",
      borderRadius:"8px",background:"rgba(13,16,22,.42)",
      color:"rgba(255,248,235,.88)",font:"13px/1.55 system-ui,sans-serif",
      textShadow:"0 1px 2px rgba(0,0,0,.65)",pointerEvents:"none",
      transition:"background .16s ease, opacity .16s ease",opacity:".86"
    } as Partial<CSSStyleDeclaration>);
    document.body.appendChild(log);
    this.chatLog=log;
    this.renderChatLog();
  }

  private addChatLog(name:string,text:string) {
    const cleanName=String(name||"WALKER").slice(0,16);
    const cleanText=String(text||"").slice(0,80);
    if(!cleanText)return;
    this.chatLines.push(`${cleanName}：${cleanText}`);
    if(this.chatLines.length>30)this.chatLines.splice(0,this.chatLines.length-30);
    this.renderChatLog();
  }

  private renderChatLog() {
    if(!this.chatLog)return;
    this.chatLog.replaceChildren();
    const visible=this.chatLines.slice(-6);
    for(const line of visible){
      const row=document.createElement("div");
      row.textContent=line;
      row.style.whiteSpace="pre-wrap";
      row.style.overflowWrap="anywhere";
      this.chatLog.appendChild(row);
    }
    this.chatLog.style.display=visible.length ? "block" : "none";
  }

  private setupChat() {
    this.setupChatLog();
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 80;
    input.placeholder = "Speak into the evening...";
    input.autocomplete = "off";
    Object.assign(input.style, {
      position: "fixed",
      left: "50%",
      bottom: "18px",
      transform: "translateX(-50%)",
      width: "min(520px, calc(100vw - 28px))",
      height: "44px",
      boxSizing: "border-box",
      border: "1px solid rgba(255,255,255,.35)",
      borderRadius: "12px",
      background: "rgba(34,29,38,.88)",
      color: "#fff7e8",
      fontSize: "16px",
      padding: "0 14px",
      outline: "none",
      zIndex: "10000"
    } as Partial<CSSStyleDeclaration>);

    const disableGameKeys = () => {
      if(this.chatLog){this.chatLog.style.background="rgba(13,16,22,.68)";this.chatLog.style.opacity="1";}
      if (this.input.keyboard) {
        this.input.keyboard.resetKeys();
        this.input.keyboard.enabled = false;
      }
      this.joystick.active = false;
      this.joystick.dx = 0;
      this.joystick.dy = 0;
    };

    const enableGameKeys = () => {
      if(this.chatLog){this.chatLog.style.background="rgba(13,16,22,.42)";this.chatLog.style.opacity=".86";}
      if (this.input.keyboard) {
        this.input.keyboard.resetKeys();
        this.input.keyboard.enabled = true;
      }
    };

    const focusChat = () => {
      disableGameKeys();
      input.focus({ preventScroll: true });
    };

    const leaveChat = () => {
      input.blur();
      enableGameKeys();
    };

    // Capture Enter before Phaser can act on it.
    window.addEventListener("keydown", (e) => {
      if (this.loginOpen) return;
      if (e.key === "Enter" && document.activeElement !== input) {
        e.preventDefault();
        e.stopImmediatePropagation();
        focusChat();
      }
    }, true);

    input.addEventListener("focus", disableGameKeys);
    input.addEventListener("blur", () => {
      if (!this.loginOpen) enableGameKeys();
    });

    // Stop keyboard events at the DOM input so WASD/arrow keys are guaranteed to type.
    for (const eventName of ["keydown", "keyup", "keypress"] as const) {
      input.addEventListener(eventName, (e) => {
        e.stopPropagation();
      });
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopImmediatePropagation();
        leaveChat();
        return;
      }

      if (e.key !== "Enter") return;

      e.preventDefault();
      e.stopImmediatePropagation();

      const text = input.value.trim();
      if (text && this.me) {
        this.showBubble(this.me, text);
        this.addChatLog(this.playerName,text);
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.socket.send(JSON.stringify({ type: "chat", text }));
        }
        input.value = "";
      }

      leaveChat();
    });

    document.body.appendChild(input);
    this.chatInput = input;
  }


  private setupCollisionMap() {
    this.rectBlockers=[]; this.circleBlockers=[]; this.polygonBlockers=[];
    const P=(pts:number[][])=>this.polygonBlockers.push(new Phaser.Geom.Polygon(pts.flat()));
    if(this.currentMap==="yunagicho"){
      // 左上の神社周辺は当たり判定を大きく撤去。鳥居～階段～上端を自由に通行可能。
      // Main shop block ("浦のや") and attached frontage; sidewalk edge left open.
    P([[346,126],[710,126],[745,213],[732,354],[699,426],[650,454],[557,464],[470,451],[402,417],[362,353]]);

    // Deep center-left/center houses bordering the narrow northbound lane.
    P([[620,0],[936,0],[940,176],[900,207],[862,255],[825,325],[790,390],[752,431],[718,417],[740,315],[748,211],[714,131]]);

    // Newspaper office / greenery / bus-stop island. Road around it remains open.
    P([[948,0],[1290,0],[1300,135],[1278,219],[1263,305],[1250,367],[1217,416],[1173,461],[1094,478],[1017,465],[994,405],[1004,323],[1007,217],[970,142]]);
    // Bus shelter itself
    P([[1090,349],[1282,344],[1300,431],[1271,474],[1111,478],[1084,442]]);

    // Far-right sea / breakwater beyond waterfront road.
    P([[1412,0],[1536,0],[1536,497],[1490,489],[1462,448],[1447,385],[1433,303],[1421,214]]);
    // Right edge sea below waterfront railing
    P([[1484,462],[1536,449],[1536,864],[1378,864],[1396,746],[1438,660],[1468,563]]);

    // Bottom-left foreground houses, walls and planting.
    P([[0,558],[88,572],[170,613],[242,651],[322,682],[389,704],[405,864],[0,864]]);
    P([[258,676],[474,679],[516,733],[526,864],[386,864],[382,742]]);

    // Bottom-center garden/wall: keeps only the road descending to bridge open.
    // 真ん中下の道路はコンビニへの通路として開放。

    // Canal/bridge left parapet and lower-right water mass.
    P([[958,638],[1060,609],[1192,574],[1334,543],[1392,552],[1382,614],[1302,637],[1198,667],[1082,699],[1018,722]]);
    // X927〜1208 / Y848周辺はコンビニ往復用の道路として完全開放。

    // Small solid objects on otherwise walkable pavement.
    P([[391,630],[419,630],[424,700],[390,701]]); // utility post
    P([[985,453],[1045,446],[1060,495],[1004,505]]); // flower/stop island
    } else if(this.currentMap==="komorebi") {
      // 木漏れ日神社: 中央参道・拝殿前広場・右参道・手水舎周辺を歩行可能に。
      P([[0,0],[145,0],[148,190],[202,254],[250,309],[286,386],[246,454],[0,454]]);
      P([[148,0],[545,0],[562,112],[530,224],[480,325],[426,430],[340,474],[276,414],[303,324],[350,228],[390,116]]);
      P([[555,0],[1110,0],[1130,82],[1082,148],[1045,252],[1025,325],[970,350],[908,319],[872,281],[748,283],[697,318],[620,333],[555,285]]);
      P([[1110,0],[1536,0],[1536,270],[1460,281],[1400,312],[1350,353],[1307,411],[1248,405],[1260,319],[1300,226],[1330,120]]);
      // 拝殿本体
      P([[748,82],[1105,78],[1127,257],[1080,305],[790,303],[744,260]]);
      // 絵馬掛け
      P([[506,308],[690,307],[704,448],[510,452]]);
      // 手水舎
      P([[116,256],[433,244],[456,468],[355,515],[167,505],[112,440]]);
      // 右端社務所
      P([[1470,286],[1536,270],[1536,655],[1460,646]]);
      // 下部植栽・柵。中央の南参道は出口として開ける。
      P([[0,555],[220,545],[354,574],[492,633],[630,700],[704,764],[704,864],[0,864]]);
      P([[944,691],[1100,648],[1260,616],[1435,604],[1536,620],[1536,864],[946,864]]);
      // 左下の灯籠・植栽島
      P([[214,515],[381,508],[437,569],[409,654],[250,670],[190,607]]);
      // 右下ベンチ・植栽
      P([[1168,631],[1455,612],[1474,730],[1380,778],[1200,756]]);
    } else {
      // コンビニ: 駐車場を主な歩行エリアにする。
      P([[410,255],[1115,255],[1115,510],[410,510]]); // 店舗本体
      P([[175,430],[310,425],[325,555],[180,555]]);  // 車
      P([[335,390],[405,390],[410,525],[335,525]]);  // 左設備
      P([[1190,405],[1435,405],[1445,585],[1185,585]]); // 自販機・ゴミ箱
      P([[0,0],[150,0],[170,420],[145,620],[0,650]]);
      P([[1460,0],[1536,0],[1536,650],[1460,620]]);
    }
  }

  private isBlocked(x:number,y:number,r=10) {
    if(x<16||x>1520)return true;
    // 夕凪町コンビニ接続道路: 指定範囲周辺は一切の当たり判定を持たせない。
    // 下端だけでなく少し上まで開け、帰還スポーン後に確実に移動できるようにする。
    if(this.currentMap==="yunagicho" && x>=927 && x<=1208 && y>=760) return false;
    if(this.currentMap==="yunagicho"){
      if(y>848 && !(x>=1012&&x<=1140)) return true;
      if(y<16)return true;
      if(y<80 && !(x>=70&&x<=300)) return true;
    }else if(this.currentMap==="komorebi"){
      if(y<16)return true;
      if(y>848 && !(x>=720&&x<=930)) return true;
    }else{
      if(y<16)return true;
      if(y>848 && !(x>=1376&&x<=1504)) return true;
    }
    const hit=new Phaser.Geom.Circle(x,y,r);
    for(const rect of this.rectBlockers)if(Phaser.Geom.Intersects.CircleToRectangle(hit,rect))return true;
    for(const c of this.circleBlockers){const d=r+c.radius,dx=x-c.x,dy=y-c.y;if(dx*dx+dy*dy<d*d)return true;}
    const samples=[[x,y],[x-r,y],[x+r,y],[x,y-r],[x,y+r]];
    for(const poly of this.polygonBlockers)if(samples.some(([px,py])=>Phaser.Geom.Polygon.Contains(poly,px,py)))return true;
    return false;
  }

  private tryMovePlayer(dx:number,dy:number,delta:number) {
    if(!this.me)return;
    const speed=this.getRaceData(this.playerRace).moveSpeed;
    const step=speed*delta/1000;
    const nx=Phaser.Math.Clamp(this.me.x+dx*step,16,1520),ny=Phaser.Math.Clamp(this.me.y+dy*step,80,848);
    if(!this.isBlocked(nx,this.me.y))this.me.x=nx;
    if(!this.isBlocked(this.me.x,ny))this.me.y=ny;
  }

  private clearOtherPlayers() {
    for(const other of this.others.values()) other.destroy(true);
    this.others.clear();
  }

  private syncOtherPlayers(players:PlayerState[]) {
    const visibleIds=new Set<string>();
    for(const p of players){
      if(p.id===this.meId) continue;
      visibleIds.add(p.id);
      let other=this.others.get(p.id);
      if(!other){
        other=this.makePlayer(p.x,p.y,p.color,p.name,p.height,p.race||"teddy");
        this.others.set(p.id,other);
      }else{
        other.setPosition(p.x,p.y);
      }
    }
    for(const [id,other] of this.others){
      if(!visibleIds.has(id)){
        other.destroy(true);
        this.others.delete(id);
      }
    }
  }

  private stopHeartbeat() {
    if(this.heartbeatTimer!==undefined){
      window.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer=undefined;
    }
  }

  private startHeartbeat(socket:WebSocket) {
    this.stopHeartbeat();
    this.lastHeartbeatAck=performance.now();
    const send=()=>{
      if(this.socket!==socket || socket.readyState!==WebSocket.OPEN) return;
      if(performance.now()-this.lastHeartbeatAck>45000){
        socket.close();
        return;
      }
      socket.send(JSON.stringify({type:"heartbeat"}));
    };
    send();
    this.heartbeatTimer=window.setInterval(send,12000);
  }

  private scheduleReconnect() {
    if(this.loginOpen || this.reconnectTimer!==undefined) return;
    const delay=Math.min(1000*Math.pow(2,this.reconnectAttempts),8000);
    this.reconnectAttempts=Math.min(this.reconnectAttempts+1,3);
    this.reconnectTimer=window.setTimeout(()=>{
      this.reconnectTimer=undefined;
      this.connect();
    },delay);
  }

  private connect() {
    if(this.socket && (this.socket.readyState===WebSocket.OPEN || this.socket.readyState===WebSocket.CONNECTING)) return;

    const socket=new WebSocket(SERVER_URL);
    this.socket=socket;

    socket.addEventListener("open",()=>{
      if(this.socket!==socket) return;
      this.reconnectAttempts=0;
      socket.send(JSON.stringify({
        type:"join",
        name:this.playerName,
        color:this.playerColor,
        height:this.playerHeight,
        race:this.playerRace,
        map:this.currentMap,
        x:this.me ? Math.round(this.me.x) : undefined,
        y:this.me ? Math.round(this.me.y) : undefined
      }));
      this.startHeartbeat(socket);
    });

    socket.addEventListener("message",(event)=>{
      if(this.socket!==socket) return;
      let msg:any;
      try{ msg=JSON.parse(String(event.data)); }catch{ return; }

      if(msg.type==="heartbeat_ack"){
        this.lastHeartbeatAck=performance.now();
        if(msg.map===this.currentMap && Array.isArray(msg.players)){
          this.syncOtherPlayers(msg.players as PlayerState[]);
        }
        return;
      }

      if(msg.type==="welcome"){
        this.meId=msg.id;
        const p=msg.player as PlayerState;
        if(p.map) this.currentMap=p.map;
        if(this.me) this.me.destroy(true);
        this.me=this.makePlayer(p.x,p.y,p.color,p.name,p.height,p.race||"teddy");
        this.background?.setTexture(this.mapData[this.currentMap].texture);
        this.background?.setDisplaySize(1536,864);
        this.setupCollisionMap();
        this.applyMapAudio();
        this.cameras.main.startFollow(this.me,true,.08,.08);
        this.cameras.main.setBounds(0,0,1536,864);
        return;
      }

      if(msg.type==="map_snapshot" || msg.type==="snapshot"){
        this.syncOtherPlayers((msg.players||[]) as PlayerState[]);
        return;
      }

      if(msg.type==="join"){
        const p=msg.player as PlayerState;
        if(p.id!==this.meId&&!this.others.has(p.id)) {
          this.others.set(p.id,this.makePlayer(p.x,p.y,p.color,p.name,p.height,p.race||"teddy"));
        }
        return;
      }

      if(msg.type==="move"){
        const p=this.others.get(msg.id);
        if(p){
          const oldX=p.x, oldY=p.y;
          p.x=Phaser.Math.Linear(p.x,msg.x,.42);
          p.y=Phaser.Math.Linear(p.y,msg.y,.42);
          const rdx=p.x-oldX, rdy=p.y-oldY;
          p.setData("remoteDX",rdx);
          p.setData("remoteDY",rdy);
          p.setData("movingUntil",performance.now()+180);
        }
        return;
      }

      if(msg.type==="chat"){
        if(msg.id===this.meId) return;
        const p=this.others.get(msg.id);
        if(p){
          this.showBubble(p,msg.text);
          this.addChatLog(String(p.getData("playerName")||"WALKER"),String(msg.text||""));
        }
        return;
      }

      if(msg.type==="money"){
        this.money=Number(msg.amount)||0;
        this.renderMoney();
        return;
      }

      if(msg.type==="leave"){
        const p=this.others.get(msg.id);
        if(p){ p.destroy(true); this.others.delete(msg.id); }
      }
    });

    socket.addEventListener("close",()=>{
      if(this.socket!==socket) return;
      this.stopHeartbeat();
      this.socket=undefined;
      this.clearOtherPlayers();
      this.scheduleReconnect();
    });

    socket.addEventListener("error",()=>{
      if(this.socket===socket && socket.readyState!==WebSocket.CLOSED) socket.close();
    });
  }

  private stopMapAudio() {
    if(this.activeMapBgm){
      this.activeMapBgm.stop();
      this.activeMapBgm.destroy();
      this.activeMapBgm=undefined;
    }
    for(const sound of this.activeMapAmbience){
      sound.stop();
      sound.destroy();
    }
    this.activeMapAmbience=[];
  }

  private applyMapAudio() {
    this.stopMapAudio();
    const config=this.mapData[this.currentMap].audio;

    if(config.bgmKey && this.cache.audio.exists(config.bgmKey)){
      this.activeMapBgm=this.sound.add(config.bgmKey,{loop:true,volume:1});
      this.activeMapBgm.play();
    }

    for(const key of config.ambienceKeys){
      if(!this.cache.audio.exists(key)) continue;
      const sound=this.sound.add(key,{loop:true,volume:1});
      sound.play();
      this.activeMapAmbience.push(sound);
    }
  }

  private setupMoneyHud() {
    const hud=document.createElement("div");
    Object.assign(hud.style,{position:"fixed",left:"14px",top:"14px",zIndex:"30",
      padding:"9px 14px",border:"1px solid #ffffff55",borderRadius:"8px",
      background:"#161616cc",color:"#fff",font:"700 16px system-ui",pointerEvents:"none"});
    document.body.appendChild(hud);
    this.moneyHud=hud;
    this.renderMoney();
  }

  private renderMoney() {
    if(this.moneyHud) this.moneyHud.textContent=`所持金　${this.money} 夏円`;
  }

  private setupTownQuiz() {
    const panel=document.createElement("div");
    Object.assign(panel.style,{display:"none",position:"fixed",left:"50%",top:"50%",
      transform:"translate(-50%,-50%)",zIndex:"45",width:"min(560px,88vw)",boxSizing:"border-box",
      background:"#151515f2",color:"#fff",border:"1px solid #ffffff55",borderRadius:"12px",
      padding:"22px",fontFamily:"system-ui",boxShadow:"0 18px 55px #0008"});
    document.body.appendChild(panel);
    this.quizPanel=panel;
  }

  private showTownQuiz(msg:any) {
    if(!this.quizPanel) return;
    this.activeQuizId=String(msg.id);
    const panel=this.quizPanel;
    panel.innerHTML="";
    panel.style.display="block";
    const announce=document.createElement("div");
    announce.textContent="📢 夕凪町 町内アナウンス";
    Object.assign(announce.style,{fontSize:"14px",opacity:".72",marginBottom:"7px"});
    const title=document.createElement("div");
    title.textContent="教養クイズ　正解で100夏円";
    Object.assign(title.style,{fontSize:"20px",fontWeight:"800",marginBottom:"14px"});
    const q=document.createElement("div");
    q.textContent=String(msg.question);
    Object.assign(q.style,{fontSize:"17px",lineHeight:"1.6",marginBottom:"14px"});
    panel.append(announce,title,q);
    (msg.options||[]).forEach((text:string,i:number)=>{
      const b=document.createElement("button");
      b.textContent=`${["A","B","C","D"][i]}. ${text}`;
      Object.assign(b.style,{display:"block",width:"100%",textAlign:"left",padding:"12px",
        margin:"8px 0",borderRadius:"7px",border:"1px solid #ffffff44",background:"#292929",
        color:"#fff",cursor:"pointer",fontSize:"15px"});
      b.addEventListener("click",()=>{
        panel.querySelectorAll("button").forEach(x=>(x as HTMLButtonElement).disabled=true);
        this.socket?.send(JSON.stringify({type:"quiz_answer",id:this.activeQuizId,answer:i}));
      });
      panel.appendChild(b);
    });
    const foot=document.createElement("div");
    foot.textContent="町にいるみんなが同じ問題に挑戦中。受付は20秒間。";
    Object.assign(foot.style,{fontSize:"12px",opacity:".58",marginTop:"12px"});
    panel.appendChild(foot);
  }

  private showQuizResult(msg:any) {
    if(!this.quizPanel || this.activeQuizId!==String(msg.id)) return;
    this.money=Number(msg.money)||this.money;
    this.renderMoney();
    const panel=this.quizPanel;
    const result=document.createElement("div");
    result.textContent=msg.correct ? `正解！ +100夏円　（${this.money}夏円）` : `不正解。正解は「${msg.correctText}」`;
    Object.assign(result.style,{marginTop:"14px",padding:"12px",borderRadius:"7px",
      background:msg.correct?"#24452f":"#4a2929",fontWeight:"700"});
    panel.appendChild(result);
    setTimeout(()=>this.closeTownQuiz(),3500);
  }

  private closeTownQuiz(message?:string) {
    if(!this.quizPanel) return;
    if(message){
      const note=document.createElement("div"); note.textContent=message;
      Object.assign(note.style,{marginTop:"12px",opacity:".7"}); this.quizPanel.appendChild(note);
      setTimeout(()=>{if(this.quizPanel)this.quizPanel.style.display="none";},1200);
    } else this.quizPanel.style.display="none";
    this.activeQuizId=null;
  }

  private setupOptions() {
    const coordHud=document.createElement("div");
    Object.assign(coordHud.style,{position:"fixed",right:"14px",top:"64px",zIndex:"29",
      padding:"5px 8px",borderRadius:"6px",background:"rgba(10,12,16,.58)",
      color:"rgba(255,255,255,.9)",font:"12px/1.2 monospace",pointerEvents:"none"});
    document.body.appendChild(coordHud);
    this.coordHud=coordHud;
    coordHud.style.display=this.coordsVisible ? "block" : "none";

    const button=document.createElement("button");
    button.textContent="⚙";
    button.title="Options";
    Object.assign(button.style,{position:"fixed",right:"14px",top:"14px",zIndex:"30",
      width:"42px",height:"42px",fontSize:"21px",border:"1px solid #ffffff66",
      borderRadius:"8px",background:"#161616cc",color:"#fff",cursor:"pointer"});
    document.body.appendChild(button);

    const panel=document.createElement("div");
    Object.assign(panel.style,{display:"none",position:"fixed",inset:"0",zIndex:"40",
      background:"#0008",alignItems:"center",justifyContent:"center"});
    panel.innerHTML=`<div style="width:min(360px,86vw);background:#181818;color:white;padding:24px;border:1px solid #ffffff33;border-radius:10px;font-family:system-ui">
      <div style="font-size:20px;font-weight:700;margin-bottom:22px">OPTIONS</div>
      <label style="display:flex;align-items:center;gap:9px;cursor:pointer">
        <input id="nantoka-coords" type="checkbox"> 座標を表示
      </label>
      <div style="display:flex;gap:10px;margin-top:18px">
        <button id="nantoka-close" style="flex:1;padding:10px">CLOSE</button>
      </div></div>`;
    document.body.appendChild(panel);
    const coords=panel.querySelector("#nantoka-coords") as HTMLInputElement;
    const sync=()=>{coords.checked=this.coordsVisible;};
    sync();
    coords.addEventListener("change",()=>{
      this.coordsVisible=coords.checked;
      localStorage.setItem("nantoka-show-coords",this.coordsVisible ? "1" : "0");
      if(this.coordHud)this.coordHud.style.display=this.coordsVisible ? "block" : "none";
    });
    const close=()=>panel.style.display="none";
    panel.querySelector("#nantoka-close")?.addEventListener("click",close);
    button.addEventListener("click",()=>{sync();panel.style.display="flex";});
    panel.addEventListener("click",(e)=>{if(e.target===panel)close();});
  }

  private setupImageField() {
    this.background=this.add.image(0,0,"yunagicho-field").setOrigin(0).setDepth(-100);
    this.background.setDisplaySize(1536,864);
    this.cameras.main.setBounds(0,0,1536,864);
  }

  private switchMap(map:MapId, x:number, y:number) {
    if(this.transitionLock || !this.me) return;
    this.transitionLock=true;
    this.currentMap=map;
    const data=this.mapData[map];
    this.background?.setTexture(data.texture);
    this.background?.setDisplaySize(1536,864);
    this.setupCollisionMap();
    this.applyMapAudio();
    for(const other of this.others.values()) other.destroy(true);
    this.others.clear();
    this.me.setPosition(x,y);
    this.mapTitle?.setText(
      map==="yunagicho" ? "夕凪町　18:42　β 0.47" :
      map==="komorebi" ? "木漏れ日神社　β 0.47" :
      "コンビニ　β 0.47"
    );
    if(map!=="yunagicho" && this.quizPanel?.style.display!=="none") this.closeTownQuiz("");
    if(this.socket?.readyState===WebSocket.OPEN){
      this.socket.send(JSON.stringify({type:"move",x:Math.round(x),y:Math.round(y),map}));
    }
    this.time.delayedCall(700,()=>this.transitionLock=false);
  }

  private checkMapTransition() {
    if(!this.me || this.transitionLock) return;
    if(this.currentMap==="yunagicho"){
      if(this.me.x>=70 && this.me.x<=300 && this.me.y<=105){
        this.switchMap("komorebi",820,805); return;
      }
      // 夕凪町・真ん中下の道路 → コンビニ
      if(this.me.x>=1012 && this.me.x<=1140 && this.me.y>=835){
        this.switchMap("convenience",1440,790);
      }
    }else if(this.currentMap==="komorebi"){
      if(this.me.x>=720 && this.me.x<=930 && this.me.y>=835){
        this.switchMap("yunagicho",170,125);
      }
    }else{
      // コンビニ駐車場・中央下 → 夕凪町
      if(this.me.x>=1376 && this.me.x<=1504 && this.me.y>=835){
        this.switchMap("yunagicho",1076,800);
      }
    }
  }

  private setupTouchControls(){
    this.input.on("pointerdown",(p:Phaser.Input.Pointer)=>{
      if(p.x>this.scale.width*.65)return;
      Object.assign(this.joystick,{active:true,pointerId:p.id,originX:p.x,originY:p.y,dx:0,dy:0});
    });
    this.input.on("pointermove",(p:Phaser.Input.Pointer)=>{
      if(!this.joystick.active||p.id!==this.joystick.pointerId)return;
      const dx=p.x-this.joystick.originX,dy=p.y-this.joystick.originY,len=Math.hypot(dx,dy)||1,max=58,s=Math.min(1,max/len);
      this.joystick.dx=dx*s/max;this.joystick.dy=dy*s/max;
    });
    const release=(p:Phaser.Input.Pointer)=>{
      if(p.id!==this.joystick.pointerId)return;
      this.joystick.active=false;this.joystick.dx=0;this.joystick.dy=0;
    };
    this.input.on("pointerup",release);this.input.on("pointerupoutside",release);
  }


  private isDomEditing() {
    const el=document.activeElement as HTMLElement | null;
    return !!el && (el.tagName==="INPUT" || el.tagName==="TEXTAREA" || el.isContentEditable);
  }

  update(time:number,delta:number){
    if(this.me && this.coordHud && this.coordsVisible){
      this.coordHud.textContent=`${this.mapData[this.currentMap].name}  X:${Math.round(this.me.x)}  Y:${Math.round(this.me.y)}`;
    }
    if (this.loginOpen || this.isDomEditing()) return;
    if(!this.me)return;
    this.checkMapTransition();

    // 他プレイヤーも描画フレームごとに歩行/立ちアニメーションする。
    const now=performance.now();
    for(const other of this.others.values()){
      const moving=now < Number(other.getData("movingUntil")||0);
      this.animateWalker(
        other,
        moving,
        Number(other.getData("remoteDX")||0),
        Number(other.getData("remoteDY")||0)
      );
    }

    const typing =
      this.loginOpen ||
      (this.chatInput !== undefined && document.activeElement === this.chatInput);

    let dx=0,dy=0;

    if(!typing){
      if(this.cursors?.left.isDown||this.keys?.A?.isDown)dx--;
      if(this.cursors?.right.isDown||this.keys?.D?.isDown)dx++;
      if(this.cursors?.up.isDown||this.keys?.W?.isDown)dy--;
      if(this.cursors?.down.isDown||this.keys?.S?.isDown)dy++;
      dx+=this.joystick.dx;
      dy+=this.joystick.dy;
    }

    const len=Math.hypot(dx,dy),moving=len>0;

    if(moving){
      dx/=len;dy/=len;
      const beforeX=this.me.x, beforeY=this.me.y;
      this.tryMovePlayer(dx,dy,delta);

      const actuallyMoved =
        Math.abs(this.me.x-beforeX)>.01 ||
        Math.abs(this.me.y-beforeY)>.01;

      this.animateWalker(this.me,actuallyMoved,dx,dy);

      if(actuallyMoved && time-this.lastSent>50 && this.socket?.readyState===WebSocket.OPEN){
        this.socket.send(JSON.stringify({
          type:"move",
          x:Math.round(this.me.x),
          y:Math.round(this.me.y)
        }));
        this.lastSent=time;
      }
    } else {
      this.animateWalker(this.me,false);
    }
  }
}

new Phaser.Game({
  type:Phaser.AUTO,
  parent:"app",
  width:1280,
  height:720,
  backgroundColor:"#0d0d0d",
  scene:WalkScene,
  scale:{
    mode:Phaser.Scale.NONE,
    autoCenter:Phaser.Scale.NO_CENTER,
    width:1280,
    height:720
  },
  render:{pixelArt:true,antialias:false}
});
