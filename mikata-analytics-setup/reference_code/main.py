"""main.py — 毎日の収集オーケストレーション"""
import traceback
import fetch_analytics as fa
import write_to_sheets as ws
import config


def run():
    snap_ws, term_ws = ws.open_sheets()
    videos = fa.get_all_videos()
    end = fa.yesterday_str()

    snap_batch, term_batch = [], []
    for v in videos:
        try:
            days = fa.days_since(v["published"])
            if days < 0 or days > config.MAX_TRACK_DAYS:
                continue
            traffic = fa.get_traffic_by_source(v["video_id"], v["published"], end)
            snap_batch.append(ws.build_snapshot_row(v, traffic, days))
            terms = fa.get_search_terms(v["video_id"], v["published"], end)
            term_batch.extend(ws.build_term_rows(v["video_id"], terms, days))
        except Exception:
            print(f"[WARN] skip {v.get('video_id')}: ")
            traceback.print_exc()

    if snap_batch:
        snap_ws.append_rows(snap_batch, value_input_option="RAW")
    if term_batch:
        term_ws.append_rows(term_batch, value_input_option="RAW")
    print(f"完了: snapshot {len(snap_batch)}本 / term {len(term_batch)}行 を追記")


if __name__ == "__main__":
    run()
