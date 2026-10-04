# 開発ガイド（Claude / GPT 共通）

このリポジトリを触るAI（Claude、GPTなど）と人は、最初にこのファイルを読む。会話履歴が無くても、GitHub上の文書だけで安全に作業を続けられるようにするためのもの（2026-10-04 Keita依頼）。

人生クエストと共通のバックエンド・プロジェクト全体のルールは `keisasaki3/keisasaki3.github.io` の `AGENTS.md` にもある。食い違うときはこのファイルと `SPEC.md` を優先する。

## 1. 読む順

1. この `AGENTS.md`
2. `SPEC.md`（正本。§13 実装運用、§14 TODO）
3. 必要に応じて `docs/IDEAS.md`（未決）、`CHARACTER_SPRITE_SPEC.md`、`docs/SHARED_BACKEND.md`、`docs/IMPLEMENTATION_HANDOFF.md`（壊してはいけない約束）
4. 共通DB: `keisasaki3/keisasaki3.github.io` の `shared-world-core/`

`README.md` の「WAN公開モード」「Cloudflare Quick Tunnel」「ワンクリックアップデーター」（`update.bat` など）は旧方式の記録。本番はRender（https://summer-end-3pm.onrender.com）で、`main` にマージすると自動で公開される。`README.md` 冒頭の版は更新しておらず、現行の版は `SPEC.md` 冒頭を見る。

## 2. 優先順位と作業ルール

- Keitaの最新指示 ＞ `IDEAS.md` で採用が明示された内容 ＞ `SPEC.md` 等 ＞ 現行実装 ＞ 過去仕様。`IDEAS.md` に書いてあるだけでは作らない。
- **「実装」と言われるまで作らない**（2026-09-28〜、プロジェクト全体）。依頼は `SPEC.md` §14 TODO（未決の案は `docs/IDEAS.md`）に書いて止める。「実装」と言われたら、同時にできるTODOもまとめて作る（§13）。
- 指定外の機能・表示・文言・データ構造を変えない。勝手な説明文・装飾・名称変更・大規模リファクタ・機能削除・ライブラリ追加はしない。改善案は実装前に提案する。
- 作ったら完了したTODOを消し、`SPEC.md` を実装に合わせる（README・HANDOFFは版や履歴のためには触らない）。
- 返答は日本語で簡潔に。

## 3. これまでの判断（会話でしか決まっていなかったもの）

- 旧教養クイズと所持金「夏円」はβ0.54で削除済み。復活させない。
- 学習コンテンツは全学問の網羅を目指さない。全学問のクイズを作る案は費用が大きく「寝かせ」中（2026-10-02）。Keitaが学びたい題材を小さく選んで足す方針（2026-10-03）。
- 学問クイズは用語当ての暗記クイズにしない。問題集のような、考えて解く問題にする（2026-09-28、Keitaは用語クイズを嫌う）。時間制限は付けない（計算はノートで解く前提。2026-09-28 撤廃）。
- 戦闘のキメラは学問だけ。早押しクイズ・パズル・謎解きは別枠で、人生クエストとはつなげない（IDEAS §2.3）。
- 呼び名: 敵は「キメラ」、装備するトピックは「魔法書」。
- 英語の略称を `summer-end-three` に変える案は保留（2026-09-28）。localStorage のキー（`summer-end-3pm-*`）を変えると端末の保存データが消えるので、やるときは移行が要る。

## 4. 変更時の注意

- 版: 機能追加（マップ追加など）でβを0.01上げるときは、`SPEC.md` 冒頭、`package.json` の `version`、`client/src/main.ts` のHUD表記（`β 0.xx`）の3か所を揃える。小さな修正では上げなくてよい。
- マップを足すときは `client/src/main.ts` に加えて、`server/server.js` の有効なマップ一覧と `scripts/verify-shared-backend-static.mjs` の `all_maps` にも足す（β0.66の前例）。
- 学問のドット絵 `public/lq-icons/` は人生クエストの `apps/life-quest/icons/` のコピー。向こうを変えたらコピーし直す。
- 共通DB（`profiles`・`races`・`player_presence` など）を変えるときは人生クエストへの影響も確かめる。スキーマ変更は `shared-world-core/supabase/migrations/` に連番で書く。**本番DBへのSQLは毎回Keitaの了承を得てから。**
- `SUPABASE_SERVICE_ROLE_KEY` はサーバー専用。クライアント・`VITE_` 変数・Gitに入れない。実値はRenderの環境変数にあり、`.env.example` には名前だけ。

## 5. 検証（PR前に1回）

```bash
npm ci
npm run build          # スプライト検査 + 共通バックエンドの静的検査 + vite build
node --check server/server.js
node --check server/shared-backend.js
grep -r "service_role\|SERVICE_ROLE" client dist   # 何も出ないこと
```

Supabaseの環境変数が無いローカルでは互換モード（SPEC §9）で起動できる: `npm run dev`（http://localhost:5173）。画面の変更はPCとスマホ幅の両方で見る。`SPEC.md` §13 の確認項目のうち、変更に関係するものを確かめる。

## 6. PRとマージ

- 作業ブランチ → PR → 検証が通ったら自分でマージする（merge commit）。他の作業中のPRと同じファイルを触るときは、後からマージする側が合わせる。
- **本番の表示確認はKeitaがやる。** マージ後に本番を見に行かず、「本番で見てほしいところ」（版の表記、変えた場所）を一言伝える。
