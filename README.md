# 午後三時、夏の果。 β 0.47

「みんなで歩けるだけ」の最小オンライン散歩空間。

## 技術

- Phaser 3
- TypeScript
- Vite
- Node.js
- ws (WebSocket)
- DBなし

## 開発モード

```powershell
npm install
npm run dev
```

PCブラウザ:

```text
http://localhost:5173
```

開発時だけ以下の2ポートを使います。

```text
5173 = Vite
8080 = WebSocket
```

---

# WAN公開モード

v0.04では本番時にゲーム画面とWebSocketを同じNode.jsサーバーから配信します。

## 1. ビルド

```powershell
npm run build
```

`dist` フォルダが生成されます。

## 2. 本番サーバー起動

```powershell
npm start
```

ブラウザで確認:

```text
http://localhost:8080
```

この状態では、

```text
8080
├─ ゲーム画面
└─ WebSocket
```

の1ポート構成です。

---

# Cloudflare Quick Tunnel でWAN公開

Cloudflare の `cloudflared` をインストールした後、

```powershell
cloudflared tunnel --url http://localhost:8080
```

を実行します。

すると、

```text
https://xxxxxxxx.trycloudflare.com
```

のようなURLが表示されます。

そのURLを友達へ送れば、別Wi-Fiや4G/5Gから同じオンライン空間へ入れます。

HTTPSで開いた場合、WebSocketも自動的に `wss://` で同一URLへ接続します。

## Cloudflared インストール例（Windows / winget）

```powershell
winget install --id Cloudflare.cloudflared
```

インストール後、一度PowerShellを開き直してください。

---

## 正式ゲーム名
- 正式ゲーム名を **「午後三時、夏の果。」** に統一
- 末尾の句点「。」までを正式名称として扱う
- ブラウザタイトル、サーバー表示、アップデータ、仕様書・READMEの旧称を統一
- ログイン画面上部に「午後三時、夏の果。」を控えめに表示
