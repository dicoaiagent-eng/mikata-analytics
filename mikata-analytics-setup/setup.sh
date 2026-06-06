#!/usr/bin/env bash
# setup.sh — ローカル環境を一括構築する
# 使い方: bash setup.sh
# 前提: Mac のホーム直下に作る。Google Drive 配下では実行しない。
set -euo pipefail

TARGET="$HOME/mikata-analytics"

echo "==> 作業ディレクトリ: $TARGET"
case "$TARGET" in
  *"Google Drive"*|*"GoogleDrive"*|*"マイドライブ"*)
    echo "!! エラー: パスが Google Drive 配下です。ローカルのホーム直下に変更してください。"
    exit 1 ;;
esac

mkdir -p "$TARGET"
cd "$TARGET"

echo "==> venv 作成"
python3 -m venv venv

echo "==> requirements.txt 作成"
cat > requirements.txt <<'EOF'
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
gspread
anthropic
python-dotenv
EOF

echo "==> 依存インストール"
./venv/bin/pip install --upgrade pip >/dev/null
./venv/bin/pip install -r requirements.txt

echo "==> .gitignore 作成"
cat > .gitignore <<'EOF'
venv/
__pycache__/
*.pyc
.env
client_secret.json
token.json
service_account.json
log.txt
EOF

echo "==> .env テンプレ作成（値は空。手動で埋める）"
if [ ! -f .env ]; then
cat > .env <<'EOF'
ANTHROPIC_API_KEY=
LINE_TOKEN=
CHANNEL_ID=
SHEET_NAME=ミカタ_アナリティクス台帳
EOF
fi

echo "==> 完了。次は Python ファイル生成 → 手動ステップ(MANUAL_STEPS.md)へ。"
ls -la
