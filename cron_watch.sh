#!/bin/sh
# cron_watch.sh — 毎時の新着監視 (watch_new.py)。cron から呼ばれる。
# caffeinate -i で実行中のアイドルスリープを防止。ログは logs/watch.log に追記。
cd "$(dirname "$0")" || exit 1
mkdir -p logs
{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') watch start ===="
  /usr/bin/caffeinate -i ./venv/bin/python watch_new.py
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') watch end (exit $?) ===="
} >> logs/watch.log 2>&1
