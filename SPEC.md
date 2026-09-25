# 午後三時、夏の果。 仕様書

## 正式ゲーム名
- 日本語正式名：**午後三時、夏の果。**
- 末尾の句点「。」までを正式名称に含む
- GitHub / Render の技術識別子：`summer-end-3pm`

## プロダクト
2Dオンライン空間。「世界を攻略するのではなく、世界に滞在する」。
戦闘を中心にせず、歩くこと・空間・他プレイヤーの気配を中心にする。

## 技術
- Phaser 3
- TypeScript
- Vite
- Node.js
- ws
- Browser first

## 現行マップ
- 夕凪町
- 木漏れ日神社
- コンビニ

## プレイヤー種族
### テディぐま
- race-id: `teddy`
- 隠し移動速度: 168
- sizeClass: standard
- visualScale: 1.0

### いにしえロボット
- race-id: `ancient-robot`
- 隠し移動速度: 176
- sizeClass: standard
- visualScale: 1.0
- テディぐまより気持ちだけ速い

### うさぎjk
- race-id: `rabbit-jk`
- 隠し移動速度: 168
- sizeClass: standard
- visualScale: 1.0

キャラクター画像規格は `CHARACTER_SPRITE_SPEC.md` v1.0 を参照。

## キャラクターアセット運用
- 正式シート: `public/sprites/sheets/<race-id>.png`
- 原本: `public/sprites/source/<race-id>-original.png`
- ランタイム: `public/sprites/runtime/<race-id>/<direction>-<frame>.png`
- `npm run validate:sprites` で自動検品
- `npm run build` は検品成功後のみ実行

## 実装運用
1. 仕様書を読む
2. TODOを読む
3. TODOに基づいて実装する
4. 実装・検証する
5. 完了したTODOを削除する
6. 実装後の状態に合わせて仕様書を更新する
7. `update.zip` と完全版ZIPを出力する

仕様変更が確定した場合、コードだけ変更して仕様書を放置しない。

## TODO
現在、仕様書に記載された実装対象TODOはなし。

新しい未実装仕様が決定した場合は、この欄へ追加してから実装する。

## クイズ
- 教養クイズ機能は現在一時停止中
- サーバーは出題タイマーを起動しない
- クライアントはクイズUIを生成しない
- 再開時は `QUIZ_ENABLED` とクライアントUIを再有効化する

## オンライン接続 / Presence
- クライアントは12秒ごとにアプリレベルheartbeatを送信する
- heartbeat応答には同一マップのauthoritative presence snapshotを含め、表示漏れを自己修復する
- サーバーは25秒ごとにWebSocket pingを送信し、アイドル接続を維持・死活監視する
- 接続断時はクライアントが1/2/4/8秒のバックオフで自動再接続する
- 再接続時は現在マップ・座標・種族を再送し、その場から復帰する

## マップ音響
- 旧BGM `Late Summer at the Pier` は削除済み
- 現在は全マップ無音
- 各マップは `audio.bgmKey` と `audio.ambienceKeys` を持つ
- 音源ファイルは `audioAssets` に key -> URL を登録し、マップ側はkeyを参照する
- マップ移動時に現在音響を停止し、新マップ設定へ自動切替する
- 今後の環境音実装は `ambienceKeys` を使用する
