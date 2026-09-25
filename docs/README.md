# 午後三時、夏の果。 — Documentation

2026-09-26以降、仕様・技術判断はGitHub上の文書を正本とする。

## Canonical documents

- `../SPEC.md` — ゲーム全体仕様
- `../CHARACTER_SPRITE_SPEC.md` — キャラクタースプライト規格
- `SHARED_BACKEND.md` — 人生クエストとの共通認証/DB接続仕様

## Shared core

共通認証・共通プレイヤー・種族・Presence・DBスキーマの正本は、現在以下に置く。

`keisasaki3/keisasaki3.github.io/shared-world-core/`

将来 `shared-world-core` 専用repoを作成した場合、この参照先を更新する。

## Documentation rule

仕様変更時はコードだけを変更せず、対応するGitドキュメントを同じ作業内で更新する。

ChatGPTプロジェクト内の会話は設計議論の履歴であり、確定仕様はGitを優先する。
