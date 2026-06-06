"""write_to_sheets.py — Google Sheets への書き込み（シート自動作成つき）"""
import gspread
from datetime import date
import config

SNAP_HEADER = [
    "取得日", "video_id", "動画タイトル", "公開日", "経過日数", "総再生数",
    "検索流入数", "ブラウズ流入数", "関連流入数", "外部流入数", "登録者流入数", "平均視聴時間(秒)",
]
TERM_HEADER = ["取得日", "video_id", "経過日数", "検索キーワード", "流入数"]


def open_sheets():
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    sh = gc.open(config.SHEET_NAME)
    snap = _ensure_ws(sh, "snapshots", SNAP_HEADER)
    term = _ensure_ws(sh, "search_terms", TERM_HEADER)
    return snap, term


def _ensure_ws(sh, name, header):
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=len(header))
    if ws.row_values(1) != header:
        ws.update("A1", [header])
    return ws


def build_snapshot_row(video, traffic_rows, days):
    views = {r[0]: r[1] for r in traffic_rows}
    avg = {r[0]: r[3] for r in traffic_rows}
    return [
        str(date.today()), video["video_id"], video["title"],
        video["published"], days, sum(views.values()),
        views.get("YT_SEARCH", 0), views.get("BROWSE", 0),
        views.get("SUGGESTED_VIDEO", 0), views.get("EXT_URL", 0),
        views.get("SUBSCRIBER", 0), avg.get("YT_SEARCH", ""),
    ]


def build_term_rows(video_id, term_rows, days):
    today = str(date.today())
    return [[today, video_id, days, kw, views] for kw, views in term_rows]
