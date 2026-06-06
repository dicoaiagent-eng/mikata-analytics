"""watch_new.py — 毎時の新着監視 + 公開7日以内の総再生数追跡

- uploads再生リスト先頭ページとvideos_masterの差分で新着を検知
- 新着のメタデータ（公開日時/曜日/時刻・タイトル・説明・タグ・動画長・video_type・訴求型）を
  videos_master に1動画1行で追記
- 公開7日以内（長尺・ショート両方）の総再生数(Data API viewCount)を hourly_views に毎時追記
  → 公開直後の伸びカーブ用。Analytics API は約2日遅れのため毎時追跡には使わない。
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
    vm_ws, hv_ws = ws.open_watch_sheets()
    known = ws.known_video_ids(vm_ws)

    # --- 新着検知 ---
    recent = fa.get_recent_videos()
    new_ids = [v["video_id"] for v in recent if v["video_id"] not in known]

    new_rows = []
    if new_ids:
        details = fa.get_video_details(new_ids)
        # 分析対象は公開(public)動画のみ。限定公開・非公開は登録しない
        # （後日 public 化されれば、先頭ページに残っている限り次回以降に拾われる）
        public_ids = [vid for vid in new_ids
                      if details.get(vid, {}).get("privacy_status") == "public"]
        now_iso = _now_iso()
        for vid in public_ids:
            try:
                d = details.get(vid)
                if not d:
                    continue
                vtype = fa.detect_video_type(vid, d["duration_sec"])
                appeal = classify.classify_title(d["title"])
                new_rows.append(ws.build_master_row({
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
            except Exception:
                print(f"[WARN] new video skip {vid}:")
                traceback.print_exc()
        if new_rows:
            vm_ws.append_rows(new_rows, value_input_option="RAW")

    # --- 公開7日以内の総再生数を hourly_views へ ---
    # 直前で追記した新着も含めて読み直す
    records = vm_ws.get_all_records()
    tracked = []
    for r in records:
        try:
            if 0 <= fa.hours_since(r["公開日時"]) <= config.WATCH_DAYS * 24:
                tracked.append(r)
        except Exception:
            continue

    hourly_rows = []
    if tracked:
        counts = fa.get_view_counts([r["video_id"] for r in tracked])
        ts = _now_iso()
        for r in tracked:
            vid = r["video_id"]
            if vid not in counts:
                continue
            hourly_rows.append(ws.build_hourly_row(
                vid, r["video_type"], fa.hours_since(r["公開日時"]), counts[vid], ts,
            ))
        if hourly_rows:
            hv_ws.append_rows(hourly_rows, value_input_option="RAW")

    print(f"完了: 新着 {len(new_rows)}本 / hourly {len(hourly_rows)}行 を追記")


if __name__ == "__main__":
    run()
