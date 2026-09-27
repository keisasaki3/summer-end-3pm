import Phaser from "phaser";
import { GAME_TITLE } from "./branding";
import {
  ensureProfile,
  getCurrentSession,
  loadPresenceStatus,
  loadRaceMasters,
  savePresenceStatus,
  saveProfile,
  sharedBackendEnabled,
  signInWithEmail,
  signInWithGoogle,
  signOutShared,
  signUpWithEmail,
  supabase,
  type PresenceStatus,
  type RaceMaster,
} from "./shared-backend";

const isViteDev = location.port === "5173";
const SERVER_URL = isViteDev
  ? `ws://${location.hostname}:8080`
  : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}`;

type MapId = "yunagicho" | "komorebi" | "convenience";
type Direction = "up" | "down" | "left" | "right";
type MapAudioConfig = { bgmKey: string | null; ambienceKeys: string[] };
type MapDefinition = { name: string; texture: string; audio: MapAudioConfig };
type PlayerState = {
  id: string;
  x: number;
  y: number;
  color: number;
  name: string;
  height: number;
  race: string;
  map?: MapId;
  direction?: Direction;
  status?: PresenceStatus;
};
type RuntimeRaceData = {
  texturePrefix: string;
  moveSpeed: number;
  sizeClass: "standard";
  visualScale: number;
};

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
  private pendingHeartbeatSince = 0;
  private lastSent = 0;
  private positionUnsent = false;
  private replacedByNewerConnection = false;

  private joystick = { active:false, pointerId:-1, originX:0, originY:0, dx:0, dy:0 };
  private chatInput?: HTMLInputElement;
  private chatLog?: HTMLDivElement;
  private chatLines: string[] = [];
  private coordHud?: HTMLDivElement;
  private coordsVisible = (
    localStorage.getItem("summer-end-3pm-show-coords") ??
    localStorage.getItem("nantoka-show-coords") ??
    localStorage.getItem("vw-show-coords") ??
    "1"
  ) !== "0";
  private playerName = "WALKER";
  private playerColor = 0x60a5fa;
  private playerHeight = 1;
  private playerRace = "teddy";
  private authUserId = "";
  private accessToken = "";
  private presenceStatus: PresenceStatus = "online";
  private loginOpen = true;
  private rectBlockers: Phaser.Geom.Rectangle[] = [];
  private circleBlockers: Phaser.Geom.Circle[] = [];
  private polygonBlockers: Phaser.Geom.Polygon[] = [];
  // 空でないマップでは、この範囲の外を通行不可にする。
  private walkablePolygons: Phaser.Geom.Polygon[] = [];
  private currentMap: MapId = "yunagicho";
  private background?: Phaser.GameObjects.Image;
  private mapTitle?: Phaser.GameObjects.Text;
  private transitionLock = false;
  private activeMapBgm?: Phaser.Sound.HTML5AudioSound;
  private activeMapAmbience: Phaser.Sound.HTML5AudioSound[] = [];
  private masterVolume = Math.min(1, Math.max(0, Number(localStorage.getItem("summer-end-3pm-master-volume") ?? "1")));

  // 今後、環境音/BGMファイルを追加したらここへ key -> URL を登録する。
  private readonly audioAssets: Record<string,string> = {
    "yunagicho-perves-village": "/audio/yunagicho-perves-village-587370.mp3",
    "komorebi-cicadas-birds": "/audio/komorebi-cicadas-birds-275634.mp3",
    "convenience-night-ambience": "/audio/convenience-night-ambience-17064.mp3"
  };

  // Shared World Core の races をログイン時に読み込み、このfallback値を上書きする。
  // sprite asset 自体は CHARACTER_SPRITE_SPEC.md の既存3種族を使用する。
  private readonly raceData: Record<string, RuntimeRaceData> = {
    teddy: { texturePrefix:"teddy", moveSpeed:168, sizeClass:"standard", visualScale:1.0 },
    "ancient-robot": { texturePrefix:"ancient-robot", moveSpeed:176, sizeClass:"standard", visualScale:1.0 },
    "rabbit-jk": { texturePrefix:"rabbit-jk", moveSpeed:168, sizeClass:"standard", visualScale:1.0 }
  };
  private readonly supportedSpriteRaces = new Set(["teddy", "ancient-robot", "rabbit-jk"]);

  private readonly mapData: Record<MapId,MapDefinition> = {
    yunagicho: {
      name:"夕凪町", texture:"yunagicho-field",
      audio:{ bgmKey:"yunagicho-perves-village", ambienceKeys:[] }
    },
    komorebi: {
      name:"木漏れ日神社", texture:"komorebi-field",
      audio:{ bgmKey:"komorebi-cicadas-birds", ambienceKeys:[] }
    },
    convenience: {
      name:"コンビニ", texture:"convenience-field",
      audio:{ bgmKey:"convenience-night-ambience", ambienceKeys:[] }
    }
  };

  constructor() { super("walk"); }

  private getRaceData(race:string): RuntimeRaceData {
    return this.raceData[race] ?? this.raceData.teddy;
  }

  private applyRaceMasters(races:RaceMaster[]) {
    for(const race of races){
      if(!this.supportedSpriteRaces.has(race.race_id)) continue;
      this.raceData[race.race_id]={
        texturePrefix:race.sprite_key,
        moveSpeed:race.move_speed,
        sizeClass:"standard",
        visualScale:race.visual_scale
      };
    }
  }

  private normalizeStatus(value:unknown):PresenceStatus {
    return value === "online" || value === "studying" || value === "reading" || value === "busy" || value === "afk" ? value : "online";
  }

  private statusLabel(status:PresenceStatus) {
    return status === "online" ? "" :
      status === "studying" ? "勉強中" :
      status === "reading" ? "読書中" :
      status === "busy" ? "取り込み中" : "AFK";
  }

  private playerLabel(name:string,status:PresenceStatus) {
    return status === "online" ? name : `${name}: ${this.statusLabel(status)}`;
  }

  private normalizeDirection(value:unknown):Direction {
    return value === "up" || value === "left" || value === "right" ? value : "down";
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
    // マップ環境音はクロスフェードループ用に同じ音源のaudio要素を2つ確保する。
    for(const [key,url] of Object.entries(this.audioAssets)) {
      // 木漏れ日神社は shrine-web-audio-loop.ts がWeb Audioで再生するため1つでよい。
      this.load.audio(key,url,{instances:key==="komorebi-cicadas-birds" ? 1 : 2});
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
    void this.setupLogin();
    this.setupCollisionMap();

    this.mapTitle = this.add.text(18, 18, "夕凪町　18:42　β 0.57", {
      fontFamily: "serif", fontSize: "18px", color: "#fff4df",
      backgroundColor: "#2b243088", padding: { x:10, y:7 }
    }).setScrollFactor(0).setDepth(1000);

    const hint = this.add.text(18, 58, "WASD / 矢印　・　スマホは左側をドラッグ", {
      fontFamily: "sans-serif", fontSize: "13px", color: "#f8e8d0",
      backgroundColor: "#2b243066", padding: { x:8, y:5 }
    }).setScrollFactor(0).setDepth(1000);
  }

  private makePlayer(
    x:number,
    y:number,
    color:number,
    label:string,
    height=1,
    race="teddy",
    direction:Direction="down",
    status:PresenceStatus="afk"
  ) {
    const visual=this.add.container(0,0);

    // Character coordinate is the feet. player-depth.ts Y-sorts these containers.
    const raceKey=this.getRaceData(race).texturePrefix;
    const sprite=this.add.image(0,0,`${raceKey}-${direction}-3`).setOrigin(.5,1);
    const raceInfo=this.getRaceData(race);
    const targetHeight=84*raceInfo.visualScale;
    sprite.setScale(targetHeight/sprite.height);
    visual.add(sprite);
    visual.setScale(height);

    const name=this.add.text(0,-88*height,this.playerLabel(label,status),{
      fontFamily:"sans-serif",fontSize:"11px",color:"#f8ead8",
      backgroundColor:"#29232d88",padding:{x:4,y:2}
    }).setOrigin(.5);

    const c=this.add.container(x,y,[visual,name]).setDepth(10);
    c.setData("visual",visual);
    c.setData("sprite",sprite);
    c.setData("nameText",name);
    c.setData("phase",0);
    c.setData("direction",direction);
    c.setData("height",height);
    c.setData("race",race);
    c.setData("playerName",label);
    c.setData("status",status);
    c.setData("remoteDX",0);
    c.setData("remoteDY",0);
    c.setData("targetX",x);
    c.setData("targetY",y);
    c.setData("movingUntil",0);
    c.setData("idleAnimating",false);
    c.setData("idleFrame",3);
    c.setData("idleAnimStart",0);
    c.setData("nextIdleAnim",performance.now()+Phaser.Math.Between(4500,11000));
    return c;
  }

  private updatePlayerIdentity(
    c:Phaser.GameObjects.Container,
    name:string,
    status:PresenceStatus,
    direction?:Direction
  ) {
    c.setData("playerName",name);
    c.setData("status",status);
    if(direction) c.setData("direction",direction);
    const nameText=c.getData("nameText") as Phaser.GameObjects.Text | undefined;
    nameText?.setText(this.playerLabel(name,status));
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


  private async setupLogin() {
    if (this.input.keyboard) this.input.keyboard.enabled = false;

    const overlay = document.createElement("div");
    Object.assign(overlay.style, {
      position:"fixed", inset:"0", zIndex:"20000",
      display:"flex", alignItems:"center", justifyContent:"center",
      background:"rgba(20,18,24,.92)", fontFamily:"sans-serif"
    } as Partial<CSSStyleDeclaration>);

    const panel = document.createElement("div");
    Object.assign(panel.style, {
      width:"min(440px, calc(100vw - 32px))",
      padding:"24px", borderRadius:"16px",
      background:"#2d2933", color:"#fff8e8",
      boxShadow:"0 18px 50px rgba(0,0,0,.35)"
    } as Partial<CSSStyleDeclaration>);

    const brand=document.createElement("div");
    brand.textContent=GAME_TITLE;
    Object.assign(brand.style,{
      fontSize:"16px",fontWeight:"600",letterSpacing:".08em",opacity:".78",marginBottom:"7px"
    } as Partial<CSSStyleDeclaration>);

    const title = document.createElement("div");
    title.textContent = "夕凪町へ";
    Object.assign(title.style, {
      fontSize:"26px", fontWeight:"700", marginBottom:"18px"
    } as Partial<CSSStyleDeclaration>);

    const message=document.createElement("div");
    Object.assign(message.style,{
      minHeight:"20px",fontSize:"13px",lineHeight:"1.5",opacity:".82",marginBottom:"14px"
    } as Partial<CSSStyleDeclaration>);

    const setMessage=(text:string,error=false)=>{
      message.textContent=text;
      message.style.color=error ? "#ffb7b7" : "#fff0cf";
    };

    panel.append(brand,title,message);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    const enterGame=(accessToken:string)=>{
      this.accessToken=accessToken;
      overlay.remove();
      this.loginOpen=false;
      if(this.input.keyboard)this.input.keyboard.enabled=true;
      this.setupChat();
      this.applyMapAudio();
      this.setupOptions();
      this.connect();
    };

    if(!sharedBackendEnabled || !supabase){
      setMessage("共有バックエンド未設定のため互換モードで起動します。");
      this.renderLegacyLogin(panel,enterGame);
      return;
    }

    const showProfileStep=async()=>{
      try{
        setMessage("共通プロフィールを読み込み中…");
        const session=await getCurrentSession();
        if(!session){
          this.renderAuthLogin(panel,setMessage,showProfileStep);
          return;
        }

        this.authUserId=session.user.id;
        this.accessToken=session.access_token;
        const [profile,races,presence]=await Promise.all([
          ensureProfile(session.user),
          loadRaceMasters(),
          loadPresenceStatus(session.user.id)
        ]);
        this.applyRaceMasters(races);
        this.presenceStatus=presence;

        this.renderSharedProfileStep(
          panel,
          setMessage,
          profile,
          races,
          presence,
          async(displayName,raceId,status)=>{
            const saved=await saveProfile(session.user.id,displayName,raceId);
            await savePresenceStatus(session.user.id,status);
            const currentSession=await getCurrentSession();
            if(!currentSession)throw new Error("認証セッションが見つかりません。再ログインしてください。");

            this.playerName=saved.display_name;
            this.playerRace=saved.race_id || raceId;
            this.playerHeight=1;
            this.playerColor=0x60a5fa;
            this.presenceStatus=status;
            enterGame(currentSession.access_token);
          }
        );
      }catch(error){
        console.error(error);
        setMessage(error instanceof Error ? error.message : "プロフィールの読み込みに失敗しました。",true);
      }
    };

    await showProfileStep();
  }

  private clearLoginStep(panel:HTMLDivElement) {
    Array.from(panel.querySelectorAll("[data-login-step]")).forEach((node)=>node.remove());
  }

  private renderAuthLogin(
    panel:HTMLDivElement,
    setMessage:(text:string,error?:boolean)=>void,
    onAuthenticated:()=>Promise<void>
  ) {
    this.clearLoginStep(panel);
    const wrap=document.createElement("div");
    wrap.dataset.loginStep="auth";

    const email=document.createElement("input");
    email.type="email";
    email.placeholder="メールアドレス";
    email.autocomplete="email";
    const password=document.createElement("input");
    password.type="password";
    password.placeholder="パスワード";
    password.autocomplete="current-password";

    for(const input of [email,password]){
      Object.assign(input.style,{
        width:"100%",height:"42px",boxSizing:"border-box",marginBottom:"10px",borderRadius:"10px",
        border:"1px solid rgba(255,255,255,.2)",background:"#211e27",color:"#fff",padding:"0 12px",
        fontSize:"15px",outline:"none"
      } as Partial<CSSStyleDeclaration>);
    }

    const row=document.createElement("div");
    Object.assign(row.style,{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"8px",marginBottom:"10px"} as Partial<CSSStyleDeclaration>);
    const login=document.createElement("button");
    login.type="button";
    login.textContent="ログイン";
    const signup=document.createElement("button");
    signup.type="button";
    signup.textContent="新規登録";
    for(const button of [login,signup]){
      Object.assign(button.style,{
        height:"42px",borderRadius:"10px",border:"1px solid rgba(255,255,255,.2)",
        background:"#f2e7c8",color:"#242027",fontWeight:"700",cursor:"pointer"
      } as Partial<CSSStyleDeclaration>);
    }
    row.append(login,signup);

    const google=document.createElement("button");
    google.type="button";
    // 人生クエストのGoogleボタンと同じ公式Gアイコン。
    google.innerHTML='<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true" style="flex:none"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>';
    const googleLabel=document.createElement("span");
    googleLabel.textContent="Googleでログイン";
    google.appendChild(googleLabel);
    Object.assign(google.style,{
      display:"flex",alignItems:"center",justifyContent:"center",gap:"10px",
      width:"100%",height:"44px",borderRadius:"10px",border:"1px solid rgba(255,255,255,.25)",
      background:"#211e27",color:"#fff8e8",fontWeight:"700",cursor:"pointer"
    } as Partial<CSSStyleDeclaration>);

    const setDisabled=(value:boolean)=>{
      login.disabled=value;signup.disabled=value;google.disabled=value;
    };
    const run=async(action:()=>Promise<void>)=>{
      try{
        setMessage("認証中…");
        setDisabled(true);
        await action();
      }catch(error){
        console.error(error);
        setMessage(error instanceof Error ? error.message : "認証に失敗しました。",true);
      }finally{
        setDisabled(false);
      }
    };

    login.onclick=()=>void run(async()=>{
      if(!email.value.trim()||!password.value)throw new Error("メールアドレスとパスワードを入力してください。");
      await signInWithEmail(email.value.trim(),password.value);
      await onAuthenticated();
    });
    signup.onclick=()=>void run(async()=>{
      if(!email.value.trim()||password.value.length<6)throw new Error("メールアドレスと6文字以上のパスワードを入力してください。");
      const session=await signUpWithEmail(email.value.trim(),password.value);
      if(session){
        await onAuthenticated();
      }else{
        setMessage("確認メールを送信しました。メール内のリンクから認証してください。");
      }
    });
    google.onclick=()=>void run(signInWithGoogle);

    const submitOnEnter=(event:KeyboardEvent)=>{
      if(event.key!=="Enter")return;
      event.preventDefault();
      login.click();
    };
    email.addEventListener("keydown",submitOnEnter);
    password.addEventListener("keydown",submitOnEnter);

    wrap.append(email,password,row,google);
    panel.appendChild(wrap);
    setMessage("共通アカウントでログインしてください。");
    email.focus();
  }

  private renderSharedProfileStep(
    panel:HTMLDivElement,
    setMessage:(text:string,error?:boolean)=>void,
    profile:{display_name:string;race_id:string|null},
    races:RaceMaster[],
    presence:PresenceStatus,
    onStart:(displayName:string,raceId:string,status:PresenceStatus)=>Promise<void>
  ) {
    this.clearLoginStep(panel);
    const wrap=document.createElement("div");
    wrap.dataset.loginStep="profile";

    const nameLabel=document.createElement("label");
    nameLabel.textContent="表示名";
    nameLabel.style.display="block";
    nameLabel.style.marginBottom="6px";
    const nameInput=document.createElement("input");
    nameInput.type="text";
    nameInput.maxLength=20;
    nameInput.value=profile.display_name;
    Object.assign(nameInput.style,{
      width:"100%",height:"42px",boxSizing:"border-box",marginBottom:"16px",borderRadius:"10px",
      border:"1px solid rgba(255,255,255,.2)",background:"#211e27",color:"#fff",padding:"0 12px",fontSize:"16px"
    } as Partial<CSSStyleDeclaration>);

    const usableRaces=races.filter((race)=>this.supportedSpriteRaces.has(race.race_id));
    const storedRace=usableRaces.find((race)=>race.race_id===profile.race_id) ?? null;
    let selectedRace=storedRace?.race_id ?? "";

    const raceLabel=document.createElement("div");
    raceLabel.textContent="種族";
    raceLabel.style.marginBottom="8px";
    const raceArea=document.createElement("div");
    raceArea.style.marginBottom="16px";

    Object.assign(raceArea.style,{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:"8px"} as Partial<CSSStyleDeclaration>);
const raceButtons:HTMLButtonElement[]=[];
for(const race of usableRaces){
  const button=document.createElement("button");
  button.type="button";
  button.textContent=race.name_ja;
  Object.assign(button.style,{
    minHeight:"48px",borderRadius:"10px",background:"#211e27",color:"#fff8e8",fontSize:"13px",
    fontWeight:"700",cursor:"pointer",border:selectedRace===race.race_id ? "2px solid #fff" : "2px solid rgba(255,255,255,.15)"
  } as Partial<CSSStyleDeclaration>);
  button.onclick=()=>{
    selectedRace=race.race_id;
    raceButtons.forEach((item)=>item.style.border="2px solid rgba(255,255,255,.15)");
    button.style.border="2px solid #fff";
  };
  raceButtons.push(button);
  raceArea.appendChild(button);
}

    const statusLabel=document.createElement("label");
    statusLabel.textContent="ステータス";
    statusLabel.style.display="block";
    statusLabel.style.marginBottom="6px";
    const status=document.createElement("select");
    for(const [value,label] of [["online","オンライン"],["studying","勉強中"],["reading","読書中"],["busy","取り込み中"],["afk","AFK"]] as const){
      const option=document.createElement("option");
      option.value=value;
      option.textContent=label;
      option.selected=value===presence;
      status.appendChild(option);
    }
    Object.assign(status.style,{
      width:"100%",height:"42px",boxSizing:"border-box",marginBottom:"18px",borderRadius:"10px",
      border:"1px solid rgba(255,255,255,.2)",background:"#211e27",color:"#fff",padding:"0 10px"
    } as Partial<CSSStyleDeclaration>);

    const start=document.createElement("button");
    start.type="button";
    start.textContent="散歩をはじめる";
    Object.assign(start.style,{
      width:"100%",height:"46px",border:"0",borderRadius:"12px",background:"#f2e7c8",color:"#242027",
      fontSize:"16px",fontWeight:"700",cursor:"pointer"
    } as Partial<CSSStyleDeclaration>);
    start.onclick=()=>void(async()=>{
      try{
        if(!selectedRace)throw new Error("種族を選択してください。");
        start.disabled=true;
        setMessage("プロフィールを保存中…");
        await onStart(nameInput.value,selectedRace,status.value as PresenceStatus);
      }catch(error){
        console.error(error);
        setMessage(error instanceof Error ? error.message : "プロフィール保存に失敗しました。",true);
        start.disabled=false;
      }
    })();

    wrap.append(nameLabel,nameInput,raceLabel,raceArea,statusLabel,status,start);
    panel.appendChild(wrap);
    setMessage("なつめポータル共通のプロフィールです");
  }

  private renderLegacyLogin(panel:HTMLDivElement,onStart:(accessToken:string)=>void) {
    this.clearLoginStep(panel);
    const wrap=document.createElement("div");
    wrap.dataset.loginStep="legacy";

    const name=document.createElement("input");
    name.placeholder="名前";
    name.maxLength=16;
    Object.assign(name.style,{
      width:"100%",height:"42px",boxSizing:"border-box",marginBottom:"12px",borderRadius:"10px",
      background:"#211e27",color:"#fff",border:"1px solid #ffffff33",padding:"0 12px"
    } as Partial<CSSStyleDeclaration>);

    const race=document.createElement("select");
    for(const [value,label] of [["teddy","テディぐま"],["ancient-robot","いにしえロボット"],["rabbit-jk","うさぎjk"]]){
      const option=document.createElement("option");
      option.value=value;
      option.textContent=label;
      race.appendChild(option);
    }
    Object.assign(race.style,{
      width:"100%",height:"42px",boxSizing:"border-box",marginBottom:"16px",borderRadius:"10px",
      background:"#211e27",color:"#fff",border:"1px solid #ffffff33",padding:"0 10px"
    } as Partial<CSSStyleDeclaration>);

    const start=document.createElement("button");
    start.type="button";
    start.textContent="散歩をはじめる";
    Object.assign(start.style,{
      width:"100%",height:"46px",border:"0",borderRadius:"12px",background:"#f2e7c8",fontWeight:"700",cursor:"pointer"
    } as Partial<CSSStyleDeclaration>);
    const begin=()=>{
      this.playerName=name.value.trim()||"WALKER";
      this.playerRace=race.value;
      this.playerHeight=1;
      this.playerColor=0x60a5fa;
      this.presenceStatus="online";
      onStart("");
    };
    start.onclick=begin;
    name.addEventListener("keydown",(event)=>{if(event.key==="Enter")begin();});

    wrap.append(name,race,start);
    panel.appendChild(wrap);
    name.focus();
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
    const cleanName=String(name||"WALKER").slice(0,20);
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
      if (text && this.me && this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: "chat", text }));
        this.showBubble(this.me, text);
        this.addChatLog(this.playerName,text);
        input.value = "";
      }

      leaveChat();
    });

    document.body.appendChild(input);
    this.chatInput = input;
  }


  private setupCollisionMap() {
    this.rectBlockers=[]; this.circleBlockers=[]; this.polygonBlockers=[]; this.walkablePolygons=[];
    const P=(pts:number[][])=>this.polygonBlockers.push(new Phaser.Geom.Polygon(pts.flat()));
    const W=(pts:number[][])=>this.walkablePolygons.push(new Phaser.Geom.Polygon(pts.flat()));
    if(this.currentMap==="yunagicho"){
      // β0.57: 背景画像差し替えに合わせ、歩ける範囲（道路・歩道）を多角形で指定する。
      // 足元の5点がすべてこの範囲内にある場合だけ移動できる。
      // 範囲: 商店前の歩道、中央の交差点、北へ上る道、防波堤沿いの道、右の堤防の上と階段・階段下、
      // 右下へ下る道と物置前の路地。家・屋根・塀・植え込み・海には入れない。
      W([[140,478],[150,462],[230,460],[270,455],[470,450],[540,443],[560,445],[600,428],[660,408],[700,392],[760,360],[782,330],[797,300],[812,275],[830,255],[856,222],[858,188],[815,168],[806,130],[812,88],[856,88],[848,118],[855,148],[883,152],[927,162],[970,170],[1000,176],[1068,194],[1163,226],[1283,262],[1335,280],[1335,312],[1283,296],[1163,260],[1068,230],[1000,212],[977,222],[950,232],[900,252],[880,270],[882,330],[860,335],[820,360],[800,385],[782,398],[768,425],[770,505],[790,515],[923,598],[963,605],[1150,716],[1183,716],[1185,648],[1258,648],[1263,748],[1418,818],[1470,864],[820,864],[760,800],[705,760],[690,720],[665,680],[625,635],[565,595],[480,590],[420,570],[330,555],[290,540],[250,515],[140,500]]);
      // 右の堤防: 防波堤沿いの道の端から、階段上の踊り場・堤防の上・階段・階段下の道へ。
      W([[1320,262],[1397,258],[1460,264],[1520,278],[1520,345],[1460,324],[1400,306],[1382,304],[1320,304]]);
      W([[1334,296],[1384,296],[1376,372],[1332,372]]);
      W([[1288,342],[1336,342],[1376,360],[1356,372],[1356,394],[1288,394]]);
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
      // 拝殿右の大木・茂み・柵
      P([[1116,0],[1326,118],[1296,228],[1258,322],[1242,408],[1200,446],[1068,444],[1044,360],[1022,326],[1044,252],[1080,146],[1130,82]]);
      // 右側の茂み・灯籠
      P([[1350,353],[1460,286],[1460,646],[1368,600],[1338,504]]);
      // 絵馬掛け右の小さな柵
      P([[714,354],[792,354],[792,434],[714,434]]);
      // 左の灯籠
      P([[410,520],[478,520],[478,602],[410,602]]);
      // 南参道出口の門柱
      P([[640,650],[745,690],[745,780],[704,780],[630,700]]);
    } else {
      // コンビニ: 駐車場を主な歩行エリアにする。
      P([[410,255],[1115,255],[1115,510],[410,510]]); // 店舗本体
      P([[175,430],[310,425],[325,555],[180,555]]);  // 車
      P([[335,390],[405,390],[410,525],[335,525]]);  // 左設備
      P([[1190,405],[1435,405],[1445,585],[1185,585]]); // 自販機・ゴミ箱
      P([[0,0],[150,0],[170,420],[145,620],[0,650]]);
      P([[1460,0],[1536,0],[1536,650],[1460,620]]);
      // 店舗の裏・空・山（駐車場より奥へは入れない）
      P([[150,0],[1460,0],[1460,505],[150,505]]);
    }
  }

  private isBlocked(x:number,y:number,r=10) {
    if(x<16||x>1520)return true;
    if(this.currentMap==="yunagicho"){
      if(y<16)return true;
    }else if(this.currentMap==="komorebi"){
      if(y<16)return true;
      if(y>848 && !(x>=720&&x<=930)) return true;
    }else{
      if(y<16)return true;
      if(y>848) return true;
    }
    const hit=new Phaser.Geom.Circle(x,y,r);
    for(const rect of this.rectBlockers)if(Phaser.Geom.Intersects.CircleToRectangle(hit,rect))return true;
    for(const c of this.circleBlockers){const d=r+c.radius,dx=x-c.x,dy=y-c.y;if(dx*dx+dy*dy<d*d)return true;}
    const samples=[[x,y],[x-r,y],[x+r,y],[x,y-r],[x,y+r]];
    if(this.walkablePolygons.length && !samples.every(([px,py])=>this.walkablePolygons.some(poly=>Phaser.Geom.Polygon.Contains(poly,px,py))))return true;
    for(const poly of this.polygonBlockers)if(samples.some(([px,py])=>Phaser.Geom.Polygon.Contains(poly,px,py)))return true;
    return false;
  }

  // 保存位置が壁・建物の中（背景差し替えや判定変更で通行不可になった場所）なら、
  // いちばん近い通行可能な位置を返す。
  private findOpenPosition(x:number,y:number) {
    if(!this.isBlocked(x,y)) return {x,y};
    for(let radius=8; radius<=1200; radius+=8){
      const steps=Math.max(16,Math.ceil(radius/4));
      let best:{x:number,y:number}|undefined;
      for(let i=0;i<steps;i++){
        const a=i/steps*Math.PI*2;
        const nx=Math.round(x+Math.cos(a)*radius), ny=Math.round(y+Math.sin(a)*radius);
        if(nx<16||nx>1520||ny<80||ny>848||this.isBlocked(nx,ny)) continue;
        if(!best || Math.abs(ny-y)<Math.abs(best.y-y)) best={x:nx,y:ny};
      }
      if(best) return best;
    }
    return {x,y};
  }

  private tryMovePlayer(dx:number,dy:number,delta:number) {
    if(!this.me)return;
    const speed=this.getRaceData(this.playerRace).moveSpeed;
    const step=speed*delta/1000;
    const nx=Phaser.Math.Clamp(this.me.x+dx*step,16,1520),ny=Phaser.Math.Clamp(this.me.y+dy*step,80,848);
    // 保存位置や当たり判定の変更で障害物の中にいる場合は、外へ出られるよう移動を許可する。
    const stuck=this.isBlocked(this.me.x,this.me.y);
    const ox=this.me.x, oy=this.me.y;
    if(stuck || !this.isBlocked(nx,this.me.y))this.me.x=nx;
    if(stuck || !this.isBlocked(this.me.x,ny))this.me.y=ny;
    // 斜めの道（防波堤沿い・堤防の上など）では、横/縦だけの入力でも道に沿って滑るように進む。
    if(!stuck && this.me.x===ox && this.me.y===oy){
      const d=Math.abs(dx*step)+Math.abs(dy*step);
      for(const sgn of [1,-1]){
        if(dx!==0 && dy===0){
          const sy=Phaser.Math.Clamp(oy+sgn*d,80,848);
          if(!this.isBlocked(nx,sy)){ this.me.setPosition(nx,sy); break; }
        }else if(dy!==0 && dx===0){
          const sx=Phaser.Math.Clamp(ox+sgn*d,16,1520);
          if(!this.isBlocked(sx,ny)){ this.me.setPosition(sx,ny); break; }
        }
      }
    }
  }

  private placeRemote(c:Phaser.GameObjects.Container,x:number,y:number) {
    c.setPosition(x,y);
    c.setData("targetX",x);
    c.setData("targetY",y);
  }

  private clearOtherPlayers() {
    for(const other of this.others.values()) other.destroy(true);
    this.others.clear();
  }

  private syncOtherPlayers(players:PlayerState[]) {
    const visibleIds=new Set<string>();
    const now=performance.now();
    for(const p of players){
      if(p.id===this.meId) continue;
      visibleIds.add(p.id);
      const direction=this.normalizeDirection(p.direction);
      const status=this.normalizeStatus(p.status);
      const race=p.race||"teddy";
      let other=this.others.get(p.id);

      if(other && String(other.getData("race")||"teddy")!==race){
        other.destroy(true);
        this.others.delete(p.id);
        other=undefined;
      }

      if(!other){
        other=this.makePlayer(p.x,p.y,p.color,p.name,p.height,race,direction,status);
        this.others.set(p.id,other);
      }else{
        // 移動中のプレイヤーはsnapshotで引き戻さず、補間先だけ更新する。
        if(now >= Number(other.getData("movingUntil")||0)) this.placeRemote(other,p.x,p.y);
        else{ other.setData("targetX",p.x); other.setData("targetY",p.y); }
        this.updatePlayerIdentity(other,p.name,status,direction);
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
    this.pendingHeartbeatSince=0;
    const send=()=>{
      if(this.socket!==socket || socket.readyState!==WebSocket.OPEN) return;
      // 非アクティブタブではタイマーが間引かれるため、「前回送ったheartbeatに
      // 20秒以上応答がない」場合だけ切断扱いにする。
      const now=performance.now();
      if(this.pendingHeartbeatSince && now-this.pendingHeartbeatSince>20000){
        socket.close();
        return;
      }
      socket.send(JSON.stringify({type:"heartbeat"}));
      if(!this.pendingHeartbeatSince) this.pendingHeartbeatSince=now;
    };
    send();
    this.heartbeatTimer=window.setInterval(send,12000);
  }

  private scheduleReconnect() {
    if(this.loginOpen || this.replacedByNewerConnection || this.reconnectTimer!==undefined) return;
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

    socket.addEventListener("open",()=>void(async()=>{
      if(this.socket!==socket) return;

      let accessToken=this.accessToken;
      if(sharedBackendEnabled && supabase){
        try{
          const session=await getCurrentSession();
          if(!session)throw new Error("認証セッションが切れました。");
          accessToken=session.access_token;
          this.accessToken=accessToken;
        }catch(error){
          console.error(error);
          socket.close();
          return;
        }
      }

      const direction=this.me
        ? this.normalizeDirection(this.me.getData("direction"))
        : "down";

      socket.send(JSON.stringify({
        type:"join",
        accessToken,
        resume:Boolean(this.me),
        name:this.playerName,
        color:this.playerColor,
        height:1,
        race:this.playerRace,
        status:this.presenceStatus,
        map:this.currentMap,
        x:this.me ? Math.round(this.me.x) : undefined,
        y:this.me ? Math.round(this.me.y) : undefined,
        direction
      }));
      this.startHeartbeat(socket);
    })());

    socket.addEventListener("message",(event)=>{
      if(this.socket!==socket) return;
      let msg:any;
      try{ msg=JSON.parse(String(event.data)); }catch{ return; }

      if(msg.type==="auth_error"){
        console.error("Shared backend auth error:",msg.code||msg.message||"unknown");
        this.stopHeartbeat();
        // DB/認証サーバーの一時障害ではログアウトさせず、再接続で復帰する。
        const transient=["AUTH_UNAVAILABLE","PROFILE_READ_FAILED","PRESENCE_READ_FAILED","STATE_READ_FAILED","RACE_READ_FAILED"];
        if(transient.includes(String(msg.code))){
          socket.close();
          return;
        }
        this.loginOpen=true;
        socket.close();
        if(sharedBackendEnabled){
          window.alert(msg.message || "認証に失敗しました。もう一度ログインしてください。");
          void signOutShared().finally(()=>window.location.reload());
        }
        return;
      }

      if(msg.type==="heartbeat_ack"){
        this.lastHeartbeatAck=performance.now();
        this.pendingHeartbeatSince=0;
        if(msg.map===this.currentMap && Array.isArray(msg.players)){
          this.syncOtherPlayers(msg.players as PlayerState[]);
        }
        return;
      }

      if(msg.type==="welcome"){
        if(sharedBackendEnabled && msg.authMode!=="supabase"){
          console.error("Shared backend misconfiguration: client auth is enabled but server auth is not.");
          window.alert("共有バックエンドのサーバー設定が未完了です。管理者に連絡してください。");
          this.loginOpen=true;
          socket.close();
          return;
        }

        this.reconnectAttempts=0;
        this.meId=String(msg.id);
        const p=msg.player as PlayerState;
        this.playerName=p.name;
        this.playerRace=p.race||"teddy";
        this.playerHeight=1;
        this.playerColor=p.color;
        this.presenceStatus=this.normalizeStatus(p.status);
        if(p.map) this.currentMap=p.map;

        if(this.me) this.me.destroy(true);
        this.me=this.makePlayer(
          p.x,p.y,p.color,p.name,1,p.race||"teddy",
          this.normalizeDirection(p.direction),this.presenceStatus
        );
        this.background?.setTexture(this.mapData[this.currentMap].texture);
        this.background?.setDisplaySize(1536,864);
        this.setupCollisionMap();
        const open=this.findOpenPosition(this.me.x,this.me.y);
        if(open.x!==this.me.x || open.y!==this.me.y){
          this.me.setPosition(open.x,open.y);
          socket.send(JSON.stringify({
            type:"move",x:open.x,y:open.y,map:this.currentMap,
            direction:this.normalizeDirection(this.me.getData("direction"))
          }));
        }
        this.applyMapAudio();
        this.updateMapTitle();
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
        if(p.id===this.meId)return;
        const current=this.others.get(p.id);
        if(current){
          if(String(current.getData("race")||"teddy")!==p.race){
            current.destroy(true);
            this.others.delete(p.id);
          }else{
            this.placeRemote(current,p.x,p.y);
            this.updatePlayerIdentity(current,p.name,this.normalizeStatus(p.status),this.normalizeDirection(p.direction));
            return;
          }
        }
        this.others.set(p.id,this.makePlayer(
          p.x,p.y,p.color,p.name,p.height,p.race||"teddy",
          this.normalizeDirection(p.direction),this.normalizeStatus(p.status)
        ));
        return;
      }

      if(msg.type==="move"){
        const p=this.others.get(msg.id);
        if(p && Number.isFinite(msg.x) && Number.isFinite(msg.y)){
          // 受信位置へは update() で毎フレーム補間し、最後の位置まで必ず到達させる。
          p.setData("targetX",msg.x);
          p.setData("targetY",msg.y);
          p.setData("remoteDX",msg.x-p.x);
          p.setData("remoteDY",msg.y-p.y);
          if(msg.direction)p.setData("direction",this.normalizeDirection(msg.direction));
          p.setData("movingUntil",performance.now()+180);
        }
        return;
      }

      if(msg.type==="presence_update"){
        const status=this.normalizeStatus(msg.status);
        if(msg.id===this.meId){
          this.presenceStatus=status;
          if(this.me)this.updatePlayerIdentity(this.me,this.playerName,status);
        }else{
          const p=this.others.get(msg.id);
          if(p)this.updatePlayerIdentity(p,String(p.getData("playerName")||"WALKER"),status);
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

      if(msg.type==="leave"){
        const p=this.others.get(msg.id);
        if(p){ p.destroy(true); this.others.delete(msg.id); }
        return;
      }

      if(msg.type==="logout_ack"){
        socket.close(1000,"logout");
      }
    });

    socket.addEventListener("close",(event)=>{
      if(this.socket!==socket) return;
      this.stopHeartbeat();
      this.socket=undefined;
      this.clearOtherPlayers();
      if(event.code===4000){
        // 同じアカウントが別の画面で接続した。ここから再接続すると
        // 2つの画面が互いを切断し続けるため、自動再接続しない。
        this.replacedByNewerConnection=true;
        this.showReplacedNotice();
        return;
      }
      this.scheduleReconnect();
    });

    socket.addEventListener("error",()=>{
      if(this.socket===socket && socket.readyState!==WebSocket.CLOSED) socket.close();
    });
  }

  private showReplacedNotice() {
    const overlay=document.createElement("div");
    Object.assign(overlay.style,{
      position:"fixed",inset:"0",zIndex:"20000",display:"flex",alignItems:"center",justifyContent:"center",
      background:"rgba(20,18,24,.86)",fontFamily:"sans-serif"
    } as Partial<CSSStyleDeclaration>);
    const box=document.createElement("div");
    Object.assign(box.style,{
      width:"min(360px, calc(100vw - 32px))",padding:"22px",borderRadius:"14px",
      background:"#2d2933",color:"#fff8e8",textAlign:"center",lineHeight:"1.6"
    } as Partial<CSSStyleDeclaration>);
    const text=document.createElement("div");
    text.textContent="別の画面で同じアカウントが接続したため、この画面は切断されました。";
    const button=document.createElement("button");
    button.type="button";
    button.textContent="この画面で再接続";
    Object.assign(button.style,{
      marginTop:"16px",width:"100%",height:"44px",border:"0",borderRadius:"10px",
      background:"#f2e7c8",color:"#242027",fontWeight:"700",cursor:"pointer"
    } as Partial<CSSStyleDeclaration>);
    button.onclick=()=>{
      overlay.remove();
      this.replacedByNewerConnection=false;
      this.connect();
    };
    box.append(text,button);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
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
      this.activeMapBgm=this.sound.add(config.bgmKey,{loop:true,volume:this.masterVolume}) as Phaser.Sound.HTML5AudioSound;
      this.activeMapBgm.play();
    }

    for(const key of config.ambienceKeys){
      if(!this.cache.audio.exists(key)) continue;
      const sound=this.sound.add(key,{loop:true,volume:this.masterVolume}) as Phaser.Sound.HTML5AudioSound;
      sound.play();
      this.activeMapAmbience.push(sound);
    }
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
    const box=document.createElement("div");
    Object.assign(box.style,{
      width:"min(360px,86vw)",background:"#181818",color:"white",padding:"24px",
      border:"1px solid #ffffff33",borderRadius:"10px",fontFamily:"system-ui"
    } as Partial<CSSStyleDeclaration>);
    const heading=document.createElement("div");
    heading.textContent="OPTIONS";
    Object.assign(heading.style,{fontSize:"20px",fontWeight:"700",marginBottom:"22px"});

    const coordsLabel=document.createElement("label");
    Object.assign(coordsLabel.style,{display:"flex",alignItems:"center",gap:"9px",cursor:"pointer"});
    const coords=document.createElement("input");
    coords.type="checkbox";
    const coordsText=document.createTextNode("座標を表示");
    coordsLabel.append(coords,coordsText);
    box.append(heading,coordsLabel);

    const volumeLabel=document.createElement("label");
    Object.assign(volumeLabel.style,{display:"block",marginTop:"18px",marginBottom:"6px"} as Partial<CSSStyleDeclaration>);
    const volumeText=document.createElement("span");
    const volumeValue=document.createElement("span");
    volumeText.textContent="音量";
    volumeValue.textContent=` ${Math.round(this.masterVolume*100)}%`;
    volumeLabel.append(volumeText,volumeValue);
    const volume=document.createElement("input");
    volume.type="range";
    volume.min="0";
    volume.max="100";
    volume.step="1";
    volume.value=String(Math.round(this.masterVolume*100));
    Object.assign(volume.style,{width:"100%",margin:"0 0 2px"} as Partial<CSSStyleDeclaration>);
    volume.addEventListener("input",()=>{
      this.masterVolume=Math.min(1,Math.max(0,Number(volume.value)/100));
      volumeValue.textContent=` ${Math.round(this.masterVolume*100)}%`;
      localStorage.setItem("summer-end-3pm-master-volume",String(this.masterVolume));
      this.activeMapBgm?.setVolume(this.masterVolume);
      for(const sound of this.activeMapAmbience) sound.setVolume(this.masterVolume);
    });
    box.append(volumeLabel,volume);

    let statusSelect:HTMLSelectElement|undefined;
    if(sharedBackendEnabled && this.authUserId){
      const statusLabel=document.createElement("label");
      statusLabel.textContent="ステータス";
      statusLabel.style.display="block";
      statusLabel.style.marginTop="18px";
      statusLabel.style.marginBottom="6px";
      statusSelect=document.createElement("select");
      for(const [value,label] of [["online","オンライン"],["studying","勉強中"],["reading","読書中"],["busy","取り込み中"],["afk","AFK"]] as const){
        const option=document.createElement("option");
        option.value=value;option.textContent=label;statusSelect.appendChild(option);
      }
      Object.assign(statusSelect.style,{
        width:"100%",height:"40px",boxSizing:"border-box",borderRadius:"8px",
        background:"#242424",color:"#fff",border:"1px solid #ffffff33",padding:"0 8px"
      } as Partial<CSSStyleDeclaration>);
      statusSelect.value=this.presenceStatus;
      statusSelect.addEventListener("change",()=>{
        const next=this.normalizeStatus(statusSelect?.value);
        if(this.socket?.readyState!==WebSocket.OPEN){
          statusSelect!.value=this.presenceStatus;
          return;
        }
        this.socket.send(JSON.stringify({type:"status",status:next}));
      });
      box.append(statusLabel,statusSelect);
    }

    const credits=document.createElement("div");
    Object.assign(credits.style,{marginTop:"18px",paddingTop:"14px",borderTop:"1px solid #ffffff22",fontSize:"11px",lineHeight:"1.5",opacity:".72"} as Partial<CSSStyleDeclaration>);
    const creditTitle=document.createElement("div");
    creditTitle.textContent="BGM: Night Ambience — cclaretc (Freesound) / Pixabay";
    const creditLink=document.createElement("a");
    creditLink.href="https://pixabay.com/sound-effects/nature-night-ambience-17064/";
    creditLink.target="_blank";
    creditLink.rel="noopener noreferrer";
    creditLink.textContent="Pixabay";
    Object.assign(creditLink.style,{color:"#fff",opacity:".9"} as Partial<CSSStyleDeclaration>);
    const yunagiCreditTitle=document.createElement("div");
    yunagiCreditTitle.style.marginTop="8px";
    yunagiCreditTitle.textContent="BGM: Perves Ambient Mountains Distant Small Village — jordir / Freesound";
    const yunagiCreditLink=document.createElement("a");
    yunagiCreditLink.href="https://freesound.org/people/jordir/sounds/587370/";
    yunagiCreditLink.target="_blank";
    yunagiCreditLink.rel="noopener noreferrer";
    yunagiCreditLink.textContent="Freesound";
    Object.assign(yunagiCreditLink.style,{color:"#fff",opacity:".9"} as Partial<CSSStyleDeclaration>);
    const komorebiCreditTitle=document.createElement("div");
    komorebiCreditTitle.style.marginTop="8px";
    komorebiCreditTitle.textContent="BGM: Cicadas + Birds — kvgarlic / Freesound";
    const komorebiCreditLink=document.createElement("a");
    komorebiCreditLink.href="https://freesound.org/people/kvgarlic/sounds/275634/";
    komorebiCreditLink.target="_blank";
    komorebiCreditLink.rel="noopener noreferrer";
    komorebiCreditLink.textContent="Freesound";
    Object.assign(komorebiCreditLink.style,{color:"#fff",opacity:".9"} as Partial<CSSStyleDeclaration>);
    credits.append(creditTitle,creditLink,yunagiCreditTitle,yunagiCreditLink,komorebiCreditTitle,komorebiCreditLink);
    box.appendChild(credits);

    const actions=document.createElement("div");
    Object.assign(actions.style,{display:"flex",gap:"10px",marginTop:"20px"});
    const closeButton=document.createElement("button");
    closeButton.textContent="CLOSE";
    Object.assign(closeButton.style,{flex:"1",padding:"10px"});
    actions.appendChild(closeButton);

    if(sharedBackendEnabled && this.authUserId){
      const logout=document.createElement("button");
      logout.textContent="LOGOUT";
      Object.assign(logout.style,{flex:"1",padding:"10px"});
      logout.addEventListener("click",()=>void(async()=>{
        logout.disabled=true;
        this.loginOpen=true;
        try{
          const socket=this.socket;
          if(socket?.readyState===WebSocket.OPEN){
            await new Promise<void>((resolve)=>{
              let settled=false;
              const finish=()=>{if(settled)return;settled=true;resolve();};
              const timer=window.setTimeout(finish,1500);
              const onMessage=(event:MessageEvent)=>{
                try{
                  const msg=JSON.parse(String(event.data));
                  if(msg.type!=="logout_ack")return;
                  window.clearTimeout(timer);
                  socket.removeEventListener("message",onMessage);
                  finish();
                }catch{}
              };
              socket.addEventListener("message",onMessage);
              socket.send(JSON.stringify({type:"logout"}));
            });
          }
          await signOutShared();
        }finally{
          window.location.reload();
        }
      })());
      actions.appendChild(logout);
    }

    box.appendChild(actions);
    panel.appendChild(box);
    document.body.appendChild(panel);

    const sync=()=>{
      coords.checked=this.coordsVisible;
      if(statusSelect)statusSelect.value=this.presenceStatus;
    };
    coords.addEventListener("change",()=>{
      this.coordsVisible=coords.checked;
      localStorage.setItem("summer-end-3pm-show-coords",this.coordsVisible ? "1" : "0");
      if(this.coordHud)this.coordHud.style.display=this.coordsVisible ? "block" : "none";
    });
    const close=()=>panel.style.display="none";
    closeButton.addEventListener("click",close);
    button.addEventListener("click",()=>{sync();panel.style.display="flex";});
    panel.addEventListener("click",(event)=>{if(event.target===panel)close();});
  }

  private updateMapTitle() {
    this.mapTitle?.setText(
      this.currentMap==="yunagicho" ? "夕凪町　18:42　β 0.57" :
      this.currentMap==="komorebi" ? "木漏れ日神社　β 0.57" :
      "コンビニ　β 0.57"
    );
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
    this.updateMapTitle();
    if(this.socket?.readyState===WebSocket.OPEN){
      this.socket.send(JSON.stringify({
        type:"move",
        x:Math.round(x),
        y:Math.round(y),
        map,
        direction:this.normalizeDirection(this.me.getData("direction"))
      }));
    }
    this.time.delayedCall(700,()=>this.transitionLock=false);
  }

  private checkMapTransition() {
    if(!this.me || this.transitionLock) return;
    if(this.currentMap==="yunagicho"){
      // 暫定: 北へ上る道の上端 → 木漏れ日神社（正式なワープ位置は未設定）
      if(this.me.x>=805 && this.me.x<=860 && this.me.y<=104){
        this.switchMap("komorebi",820,805); return;
      }
      // 夕凪町・真ん中下の道路 → コンビニ
      if(this.me.x>=1012 && this.me.x<=1140 && this.me.y>=835){
        this.switchMap("convenience",1440,760);
      }
    }else if(this.currentMap==="komorebi"){
      if(this.me.x>=720 && this.me.x<=930 && this.me.y>=835){
        this.switchMap("yunagicho",830,140);
      }
    }else{
      // コンビニ右端の道路（上下中央） → 夕凪町
      if(this.me.x>=1500 && this.me.y>=710 && this.me.y<=810){
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
    // 他プレイヤーは、自分がチャット入力中でも描画フレームごとに補間・アニメーションする。
    const now=performance.now();
    const follow=1-Math.pow(.001,delta/1000*4);
    for(const other of this.others.values()){
      const tx=Number(other.getData("targetX")), ty=Number(other.getData("targetY"));
      if(Number.isFinite(tx) && Number.isFinite(ty)){
        if(Math.abs(tx-other.x)<.5 && Math.abs(ty-other.y)<.5) other.setPosition(tx,ty);
        else other.setPosition(Phaser.Math.Linear(other.x,tx,follow),Phaser.Math.Linear(other.y,ty,follow));
      }
      const moving=now < Number(other.getData("movingUntil")||0);
      this.animateWalker(
        other,
        moving,
        Number(other.getData("remoteDX")||0),
        Number(other.getData("remoteDY")||0)
      );
    }

    if (this.loginOpen || this.isDomEditing()) {
      // 移動中にチャット入力を開いた場合も、止まった位置を送っておく。
      if(this.positionUnsent && time-this.lastSent>50) { this.sendPosition(); this.lastSent=time; }
      return;
    }
    if(!this.me)return;
    this.checkMapTransition();

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

      if(actuallyMoved) this.positionUnsent=true;
    } else {
      this.animateWalker(this.me,false);
    }

    // 50ms間隔で送信し、止まった直後の最終位置も必ず送る。
    if(this.positionUnsent && time-this.lastSent>50 && this.socket?.readyState===WebSocket.OPEN){
      this.sendPosition();
      this.lastSent=time;
    }
  }

  private sendPosition() {
    if(!this.me || this.socket?.readyState!==WebSocket.OPEN) return;
    this.socket.send(JSON.stringify({
      type:"move",
      x:Math.round(this.me.x),
      y:Math.round(this.me.y),
      map:this.currentMap,
      direction:this.normalizeDirection(this.me.getData("direction"))
    }));
    this.positionUnsent=false;
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
