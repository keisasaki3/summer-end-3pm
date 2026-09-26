# 午後三時、夏の果て — 実装仕様（現行）

更新: 2026-09-26 / β 0.53

## 1. 作品

正式名称は **「午後三時、夏の果て」**。末尾の「。」を含む。

2Dオンライン空間を歩き、世界そのものに滞在することを中心にする。ブラウザを第一ターゲットとし、現在は Phaser 3 + TypeScript + Vite + Node.js + `ws` で構成する。

## 2. 現行マップ

- `yunagicho` — 夕凪町
- `komorebi` — 木漏れ日神社
- `convenience` — コンビニ

背景画像・ポータル・既存当たり判定は現行実装を維持する。

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

キャラクターの前後関係は `player-depth.ts` が毎フレーム全プレイヤーを同一ルールで並べ替える。

- 足元Yが大きいキャラクターほど手前に描画する
- 自キャラ / 他キャラで通常の優先度を変えない
- 生成順による固定バイアスは使用しない
- 足元Yがほぼ同一（1px以内）の場合だけ、自キャラをタイブレークとして手前に出し、操作中の自キャラが完全に隠れ続ける状態を防ぐ
- 他キャラ同士の完全同位置はX座標・表示名で決定論的にタイブレークする
- `player-depth.ts` は別Phaser importの `Phaser.GAMES` に依存せず、実際に起動したGameインスタンスを参照してソートする

認証モードでは同一 `auth.users.id` の重複接続は **新しいsocketを優先**する。古いsocketのclose処理が新socketのプレイヤー状態を消さないよう、active socketを照合する。

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

各マップで環境音をループ再生する。タブやウィンドウが非アクティブになっても可能な限り継続再生するため、マップ環境音は HTML5 Audio を使用し、`pauseOnBlur = false` とする。

現行音源:

- 夕凪町: `yunagicho-perves-village`
- 木漏れ日神社: `komorebi-cicadas-birds`
- コンビニ: `convenience-night-ambience`

MP3のエンコーダ遅延・末尾/先頭の静音区間によるループ切れを避けるため、マップ環境音は同一音源の2トラックを交互に使う。現行実装では終端5秒前から次トラックを開始し、4秒間クロスフェードする。通常の `loop:true` だけには依存しない。

ユーザーのOPTIONS音量は共通マスター音量とする。音源そのものの体感差は `client/src/map-audio-levels.ts` のマップ別補正倍率で吸収する。

実効音量:

`実効音量 = ユーザーのマスター音量 × MAP_AUDIO_GAIN[map]`

現行補正倍率:

- `yunagicho`: `1.00`
- `komorebi`: `0.25`
- `convenience`: `1.00`

マップを追加・音源を交換した場合は、ユーザーのマスター音量を変更するのではなく、そのマップの `MAP_AUDIO_GAIN` を校正する。

## 12. クイズ

教養クイズはコードを残しているが `QUIZ_ENABLED = false` で完全停止中。明示指示なしに再有効化しない。

## 13. 検証要件 / 実装運用

実装依頼を受けた場合は、以下の順番で処理する。

1. `SPEC.md` を読む
2. `TODO` を読む
3. ユーザー依頼と同時に処理可能なTODOを原則まとめて実装する
4. 完了したTODOを削除し、仕様書を現行実装に合わせて更新する
5. 独立した2回の検証を行う

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

成果物/commit前に独立した2回の検証を行う。

## 14. TODO

現在なし。

## Audio credits

- コンビニBGM: **Night Ambience** — cclaretc (Freesound) / Pixabay
- https://pixabay.com/sound-effects/nature-night-ambience-17064/

- 夕凪町BGM: **Perves Ambient Mountains Distant Small Village** — jordir / Freesound
- Source: https://freesound.org/people/jordir/sounds/587370/
- License: CC0

- 木漏れ日神社BGM: **Cicadas + Birds** — kvgarlic / Freesound
- Source: https://freesound.org/people/kvgarlic/sounds/275634/
