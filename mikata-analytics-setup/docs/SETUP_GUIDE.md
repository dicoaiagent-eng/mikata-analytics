# SETUP_GUIDE.md — Claude Code でのキックオフ手順

このパッケージ一式を実行ホスト（自宅で常時稼働の MacBook Pro M1 Max）の **ローカル**（Drive外）に置き、Claude Code を起動して使う。

---

## 0. パッケージの配置

このセットアップ一式（`CLAUDE.md` / `docs/` / `.claude/` / `reference_code/` / `setup.sh`）を、
ローカルのホーム直下の作業用フォルダに置く。例:

```bash
mkdir -p ~/mikata-analytics
# ダウンロードした setup パッケージの中身を ~/mikata-analytics にコピー
```

`.claude/` フォルダごと置くことで、許可設定（settings.json）とサブエージェントが自動で効く。

---

## 1. Claude Code を起動

```bash
cd ~/mikata-analytics
claude
```

起動後、最初のプロンプトで次のように指示するだけでよい:

> CLAUDE.md と docs/ を読んで、セットアップを進めて。手動が必要な3点に来たら止めて教えて。それ以外は自走でいい。

Claude Code は `.claude/settings.json` の事前許可により、ファイル生成・venv・pip・gcloud有効化・cron登録などを**逐一確認なしで**実行する。

---

## 2. Claude Code が自走する範囲

1. `setup.sh` 実行（venv・pip・.gitignore・.env テンプレ）
2. `reference_code/` を元に各 .py を `~/mikata-analytics` 直下へ配置
3. gcloud があれば3つのAPIを有効化
4. LINE通知の現行手段を確認し `notify.py` を確定
5. ここで `docs/MANUAL_STEPS.md` の3点を提示して一旦停止

## 3. あなたが手動でやる3点（詳細は MANUAL_STEPS.md）

1. OAuthクライアントID作成 → `client_secret.json` 配置
2. `auth.py` を共有アカウントで承認 → `token.json` 生成
3. スプレッドシート作成 → サービスアカウントに編集者共有 + `.env` の値入力

## 4. 手動完了後、再び自走

> 手動部分が終わった。動作確認して cron まで設定して。

Claude Code が `main.py` テスト実行 → Sheets書き込み確認 → `analyze.py` 確認 → crontab 登録 → README 仕上げ、まで進める。

---

## トラブル時

- `token.json` 承認で弾かれる → テストユーザーに共有アカウントが入っているか（対象画面）
- Sheets 403 → サービスアカウントのメールにシートを編集者共有したか
- cron が動かない → Mac のスリープ。`pmset -g` 確認、スリープ無効化 or `caffeinate`
