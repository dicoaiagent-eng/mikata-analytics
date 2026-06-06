#!/bin/sh
# cron_report.sh — 隔週のレポート (analyze.py)。cron からは「毎週月曜」呼ばれ、
# ISO週番号が偶数の週だけ実行することで隔週を実現する。
# caffeinate -i で実行中のアイドルスリープを防止。ログは logs/report.log に追記。
cd "$(dirname "$0")" || exit 1
mkdir -p logs

week=$(date +%V)
week=${week#0}            # 先頭の0を除去（08→8 等、8進数誤認を回避）
if [ $((week % 2)) -ne 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') skip: 奇数週 (week $week) のためレポートなし" >> logs/report.log
  exit 0
fi

{
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') report start (week $week) ===="
  /usr/bin/caffeinate -i ./venv/bin/python analyze.py
  echo "==== $(date '+%Y-%m-%d %H:%M:%S') report end (exit $?) ===="
} >> logs/report.log 2>&1
