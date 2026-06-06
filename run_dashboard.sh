#!/bin/sh
# run_dashboard.sh — ダッシュボードを起動。0.0.0.0 バインドで自宅LAN内の他端末からも閲覧可。
# 閲覧URL: http://<このMacのLAN IP>:8501  （IP確認: ipconfig getifaddr en0）
cd "$(dirname "$0")" || exit 1
./venv/bin/streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501
