# 午後三時、夏の果て — 実装仕様（現行）

更新: 2026-09-28 / β 0.59

## 1. 作品

正式名称は **「午後三時、夏の果て」**。末尾の「。」を含む。

2Dオンライン空間を歩き、世界そのものに滞在することを中心にする。ブラウザを第一ターゲットとし、現在は Phaser 3 + TypeScript + Vite + Node.js + `ws` で構成する。

本番はRenderで公開する: https://summer-end-3pm.onrender.com

## 2. 現行マップ

- `yunagicho` — 夕凪町
- `komorebi` — 木漏れ日神社
- `convenience` — コンビニ

夕凪町・木漏れ日神社の背景画像はβ0.57で差し替えた（1672×941の一枚絵をワールド1536×864に表示）。コンビニの背景は現行を維持する。

当たり判定:

- 夕凪町（β0.57）: 歩ける範囲（道路・歩道）を多角形で指定し、足元がその外に出る移動は不可。歩ける範囲は商店前の歩道、中央の交差点、北へ上る道、防波堤沿いの道、右の堤防の上（階段上の踊り場から右端まで）と階段・階段下の道、右下へ下る道と物置前の路地。家・屋根・塀・植え込み・海・左上の小道には入れない
- 木漏れ日神社（β0.57）: 夕凪町と同じく歩ける範囲を多角形で指定。範囲は境内の砂利・石畳の参道・拝殿前の石段。拝殿・狛犬・灯籠・手水舎・社務所・植え込み・ベンチには入れない
- コンビニ: β0.55で背景画像に合わせて補正した障害物多角形（駐車場より奥の店舗裏・空）

ワープ:

- 夕凪町→コンビニ: 下端の道路（x1012〜1140, y≥835）。到着 1440,760
- コンビニ→夕凪町: 右端の道路の上下中央（x≥1500, y710〜810）。到着 1076,800
- 夕凪町→木漏れ日神社: 暫定で北へ上る道の上端（x805〜860, y≤104）。到着 820,805。正式な位置は未設定（TODO）
- 木漏れ日神社→夕凪町: 石畳の参道の下端（x720〜930, y≥835）。到着 830,140

横または縦だけの入力で壁に当たった場合は、道が斜めなら道に沿って滑るように進む（傾き1:1まで、全マップ共通）。

キャラクターの表示サイズは全マップ共通（84px基準 × 種族の visual_scale）。新しい夕凪町の背景でも自販機・戸口との比率が合うため変更しない。

初期スポーン（保存位置なし）は夕凪町の中央交差点（x600〜680, y500〜560）。

保存位置や判定変更で障害物の中・歩ける範囲の外にいる場合は、ログイン/再接続時にいちばん近い通行可能な位置へ移し、その位置をサーバーへ送る。それでも障害物の中にいる場合は、外へ出られるよう移動を許可する。

## 3. キャラクター

Shared World Core の `profiles.race_id -> races.race_id` を共通種族として使用する。

現行クライアントが描画できる種族:

- `teddy` — テディぐま
- `ancient-robot` — いにしえロボット
- `rabbit-jk` — うさぎjk

種族ごとの `sprite_key / visual_scale / move_speed` は Supabase の `races` を正本とし、クライアントには上記3種族の既存スプライトを同梱する。個人ごとの身長・色・装備等のアバターカスタマイズは持たない。外見は race_id だけで決まる。

スプライト形式の詳細は `CHARACTER_SPRITE_SPEC.md` を参照する。

## 4. Shared World Core

共通バックエンドの正式な Source of Truth は次のリポジトリである。

`keisasaki3/keisasaki3.github.io/shared-world-core/`

特に以下を正とする。

- `docs/ARCHITECTURE.md`
- `docs/AUTH.md`
- `docs/DATABASE.md`
- `supabase/migrations/001_initial_schema.sql`
- `supabase/seed.sql`

本リポジトリの `docs/SHARED_BACKEND.md` は「午後三時、夏の果て」側の利用方法だけを定義する。

## 5. 認証と共通人格

Supabase Auth を使用する。

対応ログイン:

- Google OAuth
- Email + Password

認証モードでは:

- 永続プレイヤーID = `auth.users.id`
- 表示名 = `profiles.display_name`
- 種族 = `profiles.race_id`
- race未設定時のみログイン画面で共通種族を選択する
- ブラウザから送信された `user_id / name / race` をWebSocketサーバーは権威値として信用しない
- WebSocket join で Supabase access token を送り、サーバーが `auth.getUser(token)` で検証する
- サーバーはDBから profile/race/presence を読み直してプレイヤーを構成する

`SUPABASE_SERVICE_ROLE_KEY` は Node.js サーバー専用で、Vite環境変数・クライアントbundle・Gitには絶対に含めない。

## 6. Presence status

Shared World Core の `player_presence.status` に対応する。

- `online` — オンライン（頭上は名前のみ）
- `studying` — 勉強中
- `reading` — 読書中
- `busy` — 取り込み中
- `afk` — AFK

ログイン時に共通値を読み込み、OPTIONSから変更できる。ゲーム中の変更はWebSocketサーバーを経由してDBへ保存し、同一マップのプレイヤーへ `presence_update` を配信する。

## 7. リアルタイムWebSocket / キャラクター描画順

リアルタイム位置の authoritative source は引き続き既存 Node.js / `ws` サーバー。

維持する仕組み:

- client heartbeat: 12秒
- heartbeat ack に同一マップの authoritative presence snapshot
- server WebSocket ping: 25秒
- reconnect: 1 / 2 / 4 / 8秒バックオフ
- map scoped join / move / chat / leave
- Y座標（足元）によるキャラクター描画順

client heartbeatは「送ったheartbeatに20秒以上ackがない」場合だけ切断扱いにする。非アクティブタブでタイマーが間引かれても、応答が返っていれば切断しない。

位置同期:

- 自キャラの移動は最短50ms間隔で送信し、止まった直後の最終位置も必ず送信する
- 他プレイヤーは受信位置を目標として毎フレーム補間し、最終位置まで到達させる
- チャット入力中も他プレイヤーの補間・アニメーションは継続する
- チャットは送信できた場合だけ自分の吹き出し・ログに表示する

キャラクターの前後関係は `player-depth.ts` が毎フレーム全プレイヤーを同一ルールで並べ替える。

- 足元Yが大きいキャラクターほど手前に描画する
- 自キャラ / 他キャラで通常の優先度を変えない
- 生成順による固定バイアスは使用しない
- 足元Yがほぼ同一（1px以内）の場合だけ、自キャラをタイブレークとして手前に出し、操作中の自キャラが完全に隠れ続ける状態を防ぐ
- 他キャラ同士の完全同位置はX座標・表示名で決定論的にタイブレークする
- `player-depth.ts` は別Phaser importの `Phaser.GAMES` に依存せず、実際に起動したGameインスタンスを参照してソートする

認証モードでは同一 `auth.users.id` の重複接続は **新しいsocketを優先**する。古いsocketのclose処理が新socketのプレイヤー状態を消さないよう、active socketを照合する。

置き換えられた古い画面（close code `4000`）は自動再接続しない。自動再接続すると2画面が互いを切断し続けるため、「この画面で再接続」ボタンを表示し、押した場合だけ再接続する。

join時の認証エラーのうち、DB/認証サーバーの一時障害（`AUTH_UNAVAILABLE` / `*_READ_FAILED`）ではログアウトせず、通常の再接続バックオフで復帰する。トークン無効・プロフィール/種族不備の場合だけログアウトして再ログインさせる。

マップ移動時は移動先への join / snapshot 配信を先に行い、DB保存は待たずに即時実行する。

サーバーは不正URL・不正/過大なWebSocketメッセージ（上限16KB）で落ちないようにする。


## 8. 永続位置

`summer_end_player_state` を再ログイン用の durable snapshot として使用する。

保存項目:

- `map_id`
- `x`
- `y`
- `direction`

保存タイミング:

- マップ移動時: 即時
- 明示的ログアウト時: 即時
- socket切断時: 即時ベストエフォート
- 通常移動中: dirty stateを約15秒以上の間隔でthrottle保存

毎フレーム・毎move packetではDBへ書き込まない。

復帰優先順位:

1. 一時切断からのWebSocket reconnectでclientに現在の `me` がある場合、その `map/x/y/direction` を優先
2. 同一accountの既存live socketを新socketが置き換える場合、既存live位置を優先
3. 通常の再ログイン/ページ再読込では `summer_end_player_state` を使用
4. 保存値がなければ既存初期spawn

これによりreconnect時に古いDB snapshotへ巻き戻さない。

## 9. 互換モード

Shared World Core用環境変数がサーバー・クライアント双方で未設定のローカル環境では、従来型のローカルログインを使ってゲームを起動できる。

互換モードでも既存のマップ、WebSocket同期、heartbeat、chat、reconnect、キャラクター表示を維持する。永続アカウント/位置保存は行わない。

本番でクライアントだけSupabase有効・サーバーだけ無効のような片側設定は構成ミスとして扱う。

## 10. 環境変数

### Browser / Vite（公開可能値のみ）

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- legacy互換: `VITE_SUPABASE_ANON_KEY`

### Node.js server only

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

`.env.example` に名前だけを置き、実値はcommitしない。

## 11. 音声

各マップで環境音をループ再生する。

現行音源:

- 夕凪町: `yunagicho-perves-village`
- 木漏れ日神社: `komorebi-cicadas-birds`
- コンビニ: `convenience-night-ambience`

静的配信はContent-LengthとRange(206)を返す。これが無いとXingヘッダの無いMP3（コンビニ音源）の長さがInfinityになりループ処理が働かない。

夕凪町とコンビニは、タブやウィンドウが非アクティブになっても可能な限り継続再生するため、HTML5 Audio を使用し `pauseOnBlur = false` とする。MP3境界対策として同一音源の2トラックを使い、ロード時に `instances: 2` を確保する（main.tsの `load.audio` で指定）。音声要素のネイティブ `ended` も監視し、クロスフェードを取りこぼした場合は即座に次を再生する。終端5秒前から次トラックの再生を試み、`play()` 成功後に4秒間の equal-power（sin/cos）クロスフェードを行う。

木漏れ日神社はループ切れ検証のため、上記HTML5 Audioクロスフェード経路を実再生では使用しない。`client/src/shrine-web-audio-loop.ts` が同一オリジンのMP3を `fetch` し、`decodeAudioData()` でPCMの `AudioBuffer` に展開する。1個の `AudioBufferSourceNode` を `loop = true` にして継続再生し、JSタイマー監視・毎周の `play()`・2トラック切替を行わない。MP3エンコーダ境界の影響を避けるため、現行実証値として先頭と末尾を各50ms除外し、`loopStart = 0.05`、`loopEnd = buffer.duration - 0.05` とする。

神社のWeb Audioはブラウザによりバックグラウンド時にsuspendされる可能性がある。現段階では「ゲームを見ている間の途切れないループ」を優先して実証する。

ユーザーのOPTIONS音量は共通マスター音量とする。音源そのものの体感差は `client/src/map-audio-levels.ts` のマップ別補正倍率で吸収する。

実効音量:

`実効音量 = ユーザーのマスター音量 × MAP_AUDIO_GAIN[map]`

現行補正倍率:

- `yunagicho`: `1.00`
- `komorebi`: `0.25`
- `convenience`: `1.00`

マップを追加・音源を交換した場合は、ユーザーのマスター音量を変更するのではなく、そのマップの `MAP_AUDIO_GAIN` を校正する。

### 11.1 HUD配置

- マップ名・時刻・β表記はゲーム画面左上に表示する。
- OPTIONSボタンと座標表示は右上に表示する。
- 座標表示は初期OFF（OPTIONSでON/OFF、localStorageに保存）。
- 操作説明（WASD／ドラッグ）の表示はβ0.58で削除した。

### 11.2 スマホ表示

- タッチ操作端末かつ画面の短辺600px以下をスマホとし、読み込み時に判定する（PCは1280x720固定のまま変更なし）。
- スマホではゲーム画面を端末の画面いっぱい（スクロールなし）に表示し、画面1pxをワールド1pxとして一部だけを映す。カメラがプレイヤーを追う。
- 画面がマップ（1536x864）より大きい方向がある場合のみ、マップ外が見えないよう拡大する。
- 画面回転・サイズ変更時は表示サイズを合わせ直す。
- 高精細画面では端末の画素密度（最大2倍）で描画し、カメラをその倍率でズームする（見える範囲は同じ。名札・吹き出しの文字をくっきり表示するため）。スティックは画面基準のDOMで描く。

### 11.3 UIデザイン（β0.58）

- OPTIONSの「デザイン」で8種から選べる（画面にはデザイン名だけを表示し、A・Dなどの記号は出さない）。初期はA。選択はlocalStorage（`summer-end-3pm-ui-theme`）に保存する。
  - A 便箋（マップ名は縦書き）／D ホーロー看板／E 障子・木枠／I 新聞・活版／L 絵本／N カセット80s／P 夜空・星／R 風鈴
- 対象はHUD（マップ名・時刻・β表記、OPTIONSボタン、座標、チャットログ、チャット入力）、ログイン画面、OPTIONS、再接続案内、キャラの名札と吹き出し。
- 見た目は `client/src/ui-themes.css`、名札・吹き出しの色とフォントは `client/src/ui-theme.ts` で定義する。
- フォントはGoogle Fontsから読み込む（Klee One／しっぽり明朝／油性マジック／はちまるポップ／禅丸ゴシック／解星デコール／禅紅道）。

### 11.4 タッチ・クリック操作（β0.58）

- 画面のどこでもドラッグすると、押した位置にスティックが出て、その方向へ歩く（少しの遊びあり）。
- 短くタップ（クリック）すると、その場所へ歩く（目印を表示）。着くか、壁などで進めなくなったら止まる。キー入力・スティック・マップ移動で取り消す。

## 12. 知性バトル（β0.59 最小版）

旧教養クイズと夏円はβ0.54で完全削除済み。β0.59で `docs/IDEAS.md` §2.1 の暫定仕様から最小版を新規に作った。コードは `client/src/intellect-battle.ts`（問題づくり・戦闘画面・問題図鑑）と `main.ts` のキメラ処理。

- 戦闘地域: 夕凪町の右の堤防の上だけ。キメラ「ソロバンハリネズミ」（数学、画像は仮にコードで描いたもの）が1体歩き回る。他のマップ・場所は安全。
- エンカウント: キメラはプレイヤーが近づく（約240px）と追いかけてきて、触れると戦闘。堤防から離れすぎると追うのをやめる。背後からの先制などはなし。
- 戦闘: 画面に「魔法書：分数の加法・減法」を表示。問題は4択。制限時間はなし（β0.59.1で削除）。正解でキメラを撃破。
- ハート: 3つから始まる（戦闘ごとに満タン）。間違えると1つ減り、同じキメラが次の問題を出す。0になると夕凪町の中央交差点に戻される。
- 「わからん」: 押すと正解と1行解説を表示し、そのままキメラを撃破。ハートは減らない。
- 苦手枠: 間違えた・わからんだった問題は「苦手」になり、次の戦闘で「苦手なソロバンハリネズミも現れた！」として同じ問題が紛れて出る。正解すると苦手から外れる。
- 撃破・敗北後、キメラは20秒後に堤防の上に再び現れる。
- 問題: 数学「分数の加法・減法」1トピックのみ。問題は保存せず、4つの型（同じ分母の足し算／違う分母の足し算／違う分母の引き算／帯分数の引き算）から数字をランダムに作る。答えは約分済み。
- 問題図鑑: OPTIONSの「問題図鑑」から開く。出会った問題、答え、解説、解いた回数、間違えた回数（わからんも含む）、苦手かどうかを表示。保存先はこの端末のlocalStorage（`summer-end-3pm-question-book`）で、DBには保存しない。
- 最小版に含めないもの: パーティ戦、魔法書（トピック）の装備画面、人生クエスト連携（Lv表示・★）、複数体の出現、報酬。

## 13. 検証要件 / 実装運用

実装依頼を受けた場合は、以下の順番で処理する。

1. `SPEC.md` を読む
2. `TODO` を読む
3. ユーザー依頼と同時に処理可能なTODOを原則まとめて実装する
4. 完了したTODOを削除し、`SPEC.md` を現行実装に合わせて更新する（README更新履歴・HANDOFFの版番号などは更新不要。2026-09-27 Keita指示）
5. 検証を1回行う（2026-09-27 Keita指示で2回→1回）

Shared World Core統合を変更する場合は少なくとも次を確認する。

- TypeScript / JavaScript構文
- import / dependency
- sprite validation
- build
- service role keyがclient source / distに存在しない
- Auth joinではserverがtokenからuser idを確定
- name/race/statusはserver側共通DB値が権威
- fresh loginはDB保存位置を復元
- reconnectはclient live位置を優先
- 2人同時接続、heartbeat snapshot、reconnect、chat、3マップ、Y-sortを維持
- マップ音量は `master volume × map gain` で適用される

成果物/commit前に検証を1回行う。

## 14. TODO

- コンビニの背景画像と種族（スプライト）を、最高性能のastraに作り直してもらう（夕凪町・木漏れ日神社の背景はβ0.57で差し替え済み）
- 夕凪町の新しい背景に合わせて、木漏れ日神社・コンビニへのワープ位置を決める（現在は暫定位置）
- 今後作りたいマップリスト
  - 冒険者のカフェ（構想は `docs/IDEAS.md` §1）
  - 護岸のある砂浜
  - あぜ道と田んぼと遠くに森の見えるバス停
  - 大きな池のほとりにベンチが2つあるイチョウ公園

## Audio credits

- コンビニBGM: **Night Ambience** — cclaretc (Freesound) / Pixabay
- https://pixabay.com/sound-effects/nature-night-ambience-17064/

- 夕凪町BGM: **Perves Ambient Mountains Distant Small Village** — jordir / Freesound
- Source: https://freesound.org/people/jordir/sounds/587370/
- License: CC0

- 木漏れ日神社BGM: **Cicadas + Birds** — kvgarlic / Freesound
- Source: https://freesound.org/people/kvgarlic/sounds/275634/
