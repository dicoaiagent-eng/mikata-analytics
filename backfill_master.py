"""backfill_master.py — 既存の全公開動画を videos_master に一括登録（初回バックフィル）

- uploads再生リストの全動画（長尺・ショート両方）を対象
- メタデータ取得・video_type判定・訴求型6分類(haiku)を全動画に適用
- videos_master に既に記録済みの video_id はスキップ
  → 毎時 cron (watch_new.py) が先に発火していても重複登録しない

実行: ./venv/bin/python backfill_master.py
"""
import traceback
from datetime import datetime, timezone, timedelta
import fetch_analytics as fa
import write_to_sheets as ws
import classify
import config

_JST = timezone(timedelta(hours=config.JST_OFFSET_HOURS))


def _now_iso():
    return datetime.now(_JST).strftime("%Y-%m-%dT%H:%M:%S")


def run():
    vm_ws, _ = ws.open_watch_sheets()
    known = ws.known_video_ids(vm_ws)

    videos = fa.get_all_videos()
    targets = [v for v in videos if v["video_id"] not in known]
    print(f"全 {len(videos)} 本中、未登録 {len(targets)} 本を処理（記録済み {len(known)} 本はスキップ）")
    if not targets:
        print("追加対象なし。終了。")
        return

    details = fa.get_video_details([v["video_id"] for v in targets])

    # 分析対象は公開(public)動画のみ。限定公開(unlisted)・非公開(private)は除外。
    public = [v for v in targets if details.get(v["video_id"], {}).get("privacy_status") == "public"]
    skipped = len(targets) - len(public)
    print(f"うち public {len(public)} 本を登録（unlisted/private {skipped} 本は対象外）")
    now_iso = _now_iso()

    rows = []
    for i, v in enumerate(public, 1):
        vid = v["video_id"]
        try:
            d = details.get(vid)
            if not d:
                print(f"[WARN] details なし: {vid}")
                continue
            vtype = fa.detect_video_type(vid, d["duration_sec"])
            appeal = classify.classify_title(d["title"])
            rows.append(ws.build_master_row({
                "video_id": vid,
                "title": d["title"],
                "published_at": d["published_at"],
                "weekday": fa.published_weekday(d["published_at"]),
                "time": fa.published_time(d["published_at"]),
                "video_type": vtype,
                "duration_sec": d["duration_sec"],
                "tags": d["tags"],
                "description": d["description"],
                "appeal": appeal,
                "recorded_at": now_iso,
            }))
            print(f"  [{i}/{len(public)}] {vtype:5s} {appeal or '(分類なし)':　<8} {d['title'][:30]}")
        except Exception:
            print(f"[WARN] skip {vid}:")
            traceback.print_exc()

    if rows:
        vm_ws.append_rows(rows, value_input_option="RAW")
    print(f"完了: videos_master に {len(rows)} 本を追記")


if __name__ == "__main__":
    run()
