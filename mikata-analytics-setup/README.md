# 中学受験のミカタ アナリティクス自動化 — Claude Code セットアップ一式

このパッケージは、Claude Code に渡すだけで YouTube Analytics 自動化パイプラインを
ほぼ自走で構築させるための下準備一式です。

## 中身

| ファイル / フォルダ | 役割 |
|---|---|
| `CLAUDE.md` | Claude Code が最初に読む最上位指示書（自動進行ルール込み） |
| `docs/REQUIREMENTS.md` | 分析要件・設計・Sheetsスキーマ・cron設計 |
| `docs/SETUP_GUIDE.md` | Claude Code の起動・進め方 |
| `docs/MANUAL_STEPS.md` | 人間が手動で行う3点だけ |
| `docs/SIDEBAR_PIN.md` | ローカルフォルダをFinderサイドバーに固定する方法 |
| `.claude/settings.json` | 許可の事前承認（確認を激減させる肝） |
| `.claude/agents/*.md` | サブエージェント3種（環境構築/コード生成/クラウド・cron） |
| `setup.sh` | ローカル環境を一括構築するスクリプト |
| `reference_code/*.py` | 各スクリプトの動作する雛形（構文チェック済み） |

## 使い方（3行）
1. このフォルダ一式をローカルの `~/mikata-analytics` に置く
2. `cd ~/mikata-analytics && claude` で起動
3. 「CLAUDE.md と docs/ を読んで自走で進めて。手動3点に来たら止めて」と指示

詳細は `docs/SETUP_GUIDE.md` を参照。

## 設計の要点
- 配置は必ずローカル（Drive配下は厳禁。token.json同期事故を防ぐ）
- 公開日からの経過日数(1/3/7/14/28)軸で、流入元・流入KW・再生数の推移を比較
- 手動が残るのは「クライアントID取得」「auth.py承認(共有アカウント)」「Sheets共有」の3点のみ
- 通知(notify.py)は差し替え可能。LINE Notifyは終了の経緯あり→実装時に現行手段を確認
