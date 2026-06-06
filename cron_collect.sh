#!/bin/sh
# cron_collect.sh — 毎日の収集 (main.py)。cron から呼ばれる。
# caffeinate -i で実行中のアイドルスリープを防止。ログは logs/collect.log に追記。
cd "$(dirname "$0")" || exit 1
mkdir -p logs
{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') collect start ===="
  /usr/bin/caffeinate -i ./venv/bin/python main.py
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') collect end (exit $?) ===="
} >> logs/collect.log 2>&1
