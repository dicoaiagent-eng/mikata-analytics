"""write_to_sheets.py — Google Sheets への書き込み（シート自動作成つき）"""
import gspread
from datetime import date
import config

SNAP_HEADER = [
    "取得日", "video_id", "動画タイトル", "公開日", "経過日数", "総再生数",
    "検索流入数", "ブラウズ流入数", "関連流入数", "外部流入数", "登録者流入数", "平均視聴時間(秒)",
    "公開曜日", "公開時刻", "video_type",
]
TERM_HEADER = ["取得日", "video_id", "経過日数", "検索キーワード", "流入数"]
VIDEOS_MASTER_HEADER = [
    "video_id", "タイトル", "公開日時", "公開曜日", "公開時刻", "video_type",
    "動画長(秒)", "タグ", "説明文", "訴求型", "初回記録日時",
]
HOURLY_HEADER = ["取得時刻", "video_id", "video_type", "経過時間(h)", "viewCount"]
CHANNEL_STATS_HEADER = ["取得日", "登録者数", "総再生数", "総本数"]
VIDEO_METRICS_HEADER = ["取得日", "video_id", "経過日数", "視聴維持率",
                        "平均視聴秒", "期間再生", "登録獲得", "登録喪失"]


def open_sheets():
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    sh = gc.open(config.SHEET_NAME)
    snap = _ensure_ws(sh, "snapshots", SNAP_HEADER)
    term = _ensure_ws(sh, "search_terms", TERM_HEADER)
    return snap, term


def open_channel_stats():
    """チャンネル統計シート (channel_stats) を開く（無ければ作成）"""
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    sh = gc.open(config.SHEET_NAME)
    return _ensure_ws(sh, "channel_stats", CHANNEL_STATS_HEADER)


def build_channel_row(stats):
    """channel_stats の1行（1日1行）。stats は get_channel_stats() の戻り値。"""
    return [
        str(date.today()), stats["subscribers"],
        stats["total_views"], stats["video_count"],
    ]


def open_video_metrics():
    """動画総合指標シート (video_metrics) を開く（無ければ作成）"""
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    sh = gc.open(config.SHEET_NAME)
    return _ensure_ws(sh, "video_metrics", VIDEO_METRICS_HEADER)


def build_video_metrics_row(video_id, days, m):
    """video_metrics の1行。m は get_video_metrics() の戻り値。"""
    return [
        str(date.today()), video_id, days,
        m.get("avg_view_pct", ""), m.get("avg_dur", ""),
        m.get("views", ""), m.get("subs_gained", ""), m.get("subs_lost", ""),
    ]


def open_watch_sheets():
    """新着監視用シート (videos_master / hourly_views) を開く（無ければ作成）"""
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    sh = gc.open(config.SHEET_NAME)
    vm = _ensure_ws(sh, "videos_master", VIDEOS_MASTER_HEADER)
    hv = _ensure_ws(sh, "hourly_views", HOURLY_HEADER)
    return vm, hv


def known_video_ids(vm_ws):
    """videos_master に既に記録済みの video_id 集合（ヘッダー除く）"""
    return set(vm_ws.col_values(1)[1:])


def _ensure_ws(sh, name, header):
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(header))
    if ws.row_values(1) != header:
        ws.update("A1", [header])
    return ws


def build_snapshot_row(video, traffic_rows, days, weekday="", pub_time="", video_type=""):
    views = {r[0]: r[1] for r in traffic_rows}
    avg = {r[0]: r[3] for r in traffic_rows}
    return [
        str(date.today()), video["video_id"], video["title"],
        video["published"], days, sum(views.values()),
        views.get("YT_SEARCH", 0), views.get("BROWSE", 0),
        views.get("SUGGESTED_VIDEO", 0), views.get("EXT_URL", 0),
        views.get("SUBSCRIBER", 0), avg.get("YT_SEARCH", ""),
        weekday, pub_time, video_type,
    ]


def build_term_rows(video_id, term_rows, days):
    today = str(date.today())
    return [[today, video_id, days, kw, views] for kw, views in term_rows]


def build_master_row(v):
    """videos_master の1行（1動画1行）"""
    return [
        v["video_id"], v["title"], v["published_at"], v["weekday"], v["time"],
        v["video_type"], v["duration_sec"], ", ".join(v["tags"]),
        (v["description"] or "")[:1000], v["appeal"], v["recorded_at"],
    ]


def build_hourly_row(video_id, video_type, hours, view_count, ts):
    """hourly_views の1行"""
    return [ts, video_id, video_type, hours, view_count]
