"""main.py — 毎日の収集オーケストレーション"""
import traceback
import fetch_analytics as fa
import write_to_sheets as ws
import config


def run():
    snap_ws, term_ws = ws.open_sheets()
    vm_ws = ws.open_video_metrics()

    # チャンネル統計を日次で1行記録（登録者の28日差分などの履歴用）
    try:
        cs_ws = ws.open_channel_stats()
        cs_ws.append_row(ws.build_channel_row(fa.get_channel_stats()),
                         value_input_option="RAW")
    except Exception:
        print("[WARN] channel_stats 記録に失敗:")
        traceback.print_exc()

    videos = fa.get_all_videos()
    end = fa.yesterday_str()

    # 追跡対象（公開60日以内）。詳細を取得し「公開(public)」動画のみに限定。
    # 限定公開/非公開（先方確認用など）は数値データに含めない。
    in_range = [v for v in videos if 0 <= fa.days_since(v["published"]) <= config.MAX_TRACK_DAYS]
    details = fa.get_video_details([v["video_id"] for v in in_range])
    public = [v for v in in_range
              if details.get(v["video_id"], {}).get("privacy_status") == "public"]
    print(f"対象: 公開60日以内 {len(in_range)} 本中 public {len(public)} 本のみ収集")

    snap_batch, term_batch, metrics_batch = [], [], []
    for v in public:
        try:
            days = fa.days_since(v["published"])
            traffic = fa.get_traffic_by_source(v["video_id"], v["published"], end)
            weekday = fa.published_weekday(v["published_at"])
            pub_time = fa.published_time(v["published_at"])
            vtype = fa.detect_video_type(v["video_id"], details.get(v["video_id"], {}).get("duration_sec", 0))
            snap_batch.append(ws.build_snapshot_row(v, traffic, days, weekday, pub_time, vtype))
            terms = fa.get_search_terms(v["video_id"], v["published"], end)
            term_batch.extend(ws.build_term_rows(v["video_id"], terms, days))
            # 総合指標（視聴維持率・登録獲得など）
            m = fa.get_video_metrics(v["video_id"], v["published"], end)
            if m:
                metrics_batch.append(ws.build_video_metrics_row(v["video_id"], days, m))
        except Exception:
            print(f"[WARN] skip {v.get('video_id')}: ")
            traceback.print_exc()

    if snap_batch:
        snap_ws.append_rows(snap_batch, value_input_option="RAW")
    if term_batch:
        term_ws.append_rows(term_batch, value_input_option="RAW")
    if metrics_batch:
        vm_ws.append_rows(metrics_batch, value_input_option="RAW")
    print(f"完了: snapshot {len(snap_batch)} / term {len(term_batch)} / "
          f"metrics {len(metrics_batch)} を追記")


if __name__ == "__main__":
    run()
