#!/bin/sh
# share.sh — ダッシュボードを外部に一時公開（Cloudflare quick tunnel）
#
# 使い方:  ./share.sh
#   1) .env に DASH_PASSWORD=好きな合言葉 を設定しておく（公開URLの閲覧保護）
#   2) 実行すると https://xxxxx.trycloudflare.com のURLが表示される
#   3) そのURLを外出先の自分／先方に共有（パスワードで保護）
#   ※ このウィンドウを閉じる or Macがスリープすると公開は停止します。
#   ※ URLは実行ごとに変わります（恒久URLは README の Streamlit Cloud 手順を参照）。
cd "$(dirname "$0")" || exit 1
mkdir -p logs

# ダッシュボード未起動なら起動（localhost:8501）
if ! curl -s -o /dev/null http://localhost:8501; then
  echo "ダッシュボードを起動中..."
  nohup ./venv/bin/streamlit run dashboard.py --server.port 8501 --server.headless true \
    > logs/dashboard.log 2>&1 &
  until curl -s -o /dev/null http://localhost:8501; do sleep 1; done
fi

echo "公開URLを発行します（停止は Ctrl+C）..."
exec cloudflared tunnel --url http://localhost:8501
