# 午後三時、夏の果て — Documentation

2026-09-26以降、仕様・技術判断はGitHub上の文書を正本とする。

作業ルール・検証手順・会話でだけ決まっていた判断は `../AGENTS.md` にまとめてある（Claude / GPT 共通）。

## Canonical documents

- `../SPEC.md` — ゲーム全体仕様
- `../CHARACTER_SPRITE_SPEC.md` — キャラクタースプライト規格
- `SHARED_BACKEND.md` — 人生クエストとの共通認証/DB接続仕様

## Ideas (未決)

- `IDEAS.md` — 未決アイデア置き場。採用が明示された項目だけ実装する

## Shared core

共通認証・共通プレイヤー・種族・Presence・DBスキーマの正本は、現在以下に置く。

`keisasaki3/keisasaki3.github.io/shared-world-core/`

将来 `shared-world-core` 専用repoを作成した場合、この参照先を更新する。

## Documentation rule

仕様変更時はコードだけを変更せず、対応するGitドキュメントを同じ作業内で更新する。

ChatGPTプロジェクト内の会話は設計議論の履歴であり、確定仕様はGitを優先する。
