"""fetch_analytics.py — YouTube Data/Analytics API からデータを取得"""
import re
from datetime import datetime, date, timedelta, timezone
import requests
from googleapiclient.discovery import build
import config
import gauth

_creds = gauth.youtube_credentials()
_yt_data = build("youtube", "v3", credentials=_creds)
_yt_analytics = build("youtubeAnalytics", "v2", credentials=_creds)

_JST = timezone(timedelta(hours=config.JST_OFFSET_HOURS))
_WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def uploads_playlist_id():
    """アップロード再生リストIDはチャンネルIDの UC→UU 変換で導出（API節約）"""
    return "UU" + config.CHANNEL_ID[2:]


def get_all_videos():
    """全動画の id / title / published(YYYY-MM-DD) / published_at(ISO) を返す"""
    videos = []
    page = None
    while True:
        res = _yt_data.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads_playlist_id(),
            maxResults=50, pageToken=page,
        ).execute()
        for it in res["items"]:
            pub = it["contentDetails"]["videoPublishedAt"]
            videos.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published": pub[:10],
                "published_at": pub,
            })
        page = res.get("nextPageToken")
        if not page:
            break
    return videos


def get_recent_videos(max_results=50):
    """アップロード再生リスト先頭ページ（新着順）。新着検知用。"""
    res = _yt_data.playlistItems().list(
        part="snippet,contentDetails", playlistId=uploads_playlist_id(),
        maxResults=max_results,
    ).execute()
    out = []
    for it in res["items"]:
        pub = it["contentDetails"]["videoPublishedAt"]
        out.append({
            "video_id": it["contentDetails"]["videoId"],
            "title": it["snippet"]["title"],
            "published": pub[:10],
            "published_at": pub,
        })
    return out


def get_video_details(video_ids):
    """{id: {title, description, tags, published_at, duration_sec, privacy_status}} をバッチ取得"""
    details = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        res = _yt_data.videos().list(
            part="snippet,contentDetails,status", id=",".join(chunk),
        ).execute()
        for it in res["items"]:
            sn = it["snippet"]
            details[it["id"]] = {
                "title": sn["title"],
                "description": sn.get("description", ""),
                "tags": sn.get("tags", []),
                "published_at": sn["publishedAt"],
                "duration_sec": parse_duration(it["contentDetails"]["duration"]),
                "privacy_status": it.get("status", {}).get("privacyStatus", ""),
            }
    return details


def get_durations(video_ids):
    """{id: 動画長(秒)} をバッチ取得（snapshots用）"""
    durations = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        res = _yt_data.videos().list(part="contentDetails", id=",".join(chunk)).execute()
        for it in res["items"]:
            durations[it["id"]] = parse_duration(it["contentDetails"]["duration"])
    return durations


def get_view_counts(video_ids):
    """{id: 総再生数(viewCount)} をバッチ取得。Data API statistics（約2日遅れの無いリアルタイム値）"""
    counts = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        res = _yt_data.videos().list(part="statistics", id=",".join(chunk)).execute()
        for it in res["items"]:
            counts[it["id"]] = int(it["statistics"].get("viewCount", 0))
    return counts


def get_channel_stats():
    """チャンネル統計 {subscribers, total_views, video_count} を取得（1 unit）"""
    res = _yt_data.channels().list(
        part="statistics", id=config.CHANNEL_ID,
    ).execute()
    s = res["items"][0]["statistics"]
    return {
        "subscribers": int(s.get("subscriberCount", 0)),
        "total_views": int(s.get("viewCount", 0)),
        "video_count": int(s.get("videoCount", 0)),
    }


def get_video_stats(video_ids):
    """{id: {views, likes, comments}} をバッチ取得（Data API statistics, 50件/unit）"""
    stats = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        res = _yt_data.videos().list(part="statistics", id=",".join(chunk)).execute()
        for it in res["items"]:
            st = it["statistics"]
            stats[it["id"]] = {
                "views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
            }
    return stats


def parse_duration(iso):
    """ISO8601 duration (PT#H#M#S) を秒に変換"""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def detect_video_type(video_id, duration_sec):
    """ショート/長尺判定: 動画長で事前フィルタ → /shorts/{id} のリダイレクト有無で最終判定"""
    if duration_sec > config.SHORTS_MAX_SEC:
        return "long"
    try:
        r = requests.get(
            f"https://www.youtube.com/shorts/{video_id}",
            allow_redirects=False, timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        # Short は 200。通常動画は /watch?v= へ 3xx リダイレクト。
        return "short" if r.status_code == 200 else "long"
    except Exception:
        # 判定不能時は安全側（long）に倒す
        return "long"


def _parse_iso(iso):
    return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))


def published_weekday(published_at):
    """公開日時(ISO)を日本時間に直した曜日（月〜日）"""
    return _WEEKDAYS[_parse_iso(published_at).astimezone(_JST).weekday()]


def published_time(published_at):
    """公開日時(ISO)を日本時間に直した時刻 HH:MM"""
    return _parse_iso(published_at).astimezone(_JST).strftime("%H:%M")


def hours_since(published_at):
    """公開からの経過時間（時間, 小数1桁）"""
    delta = datetime.now(timezone.utc) - _parse_iso(published_at)
    return round(delta.total_seconds() / 3600, 1)


def get_traffic_by_source(video_id, start, end):
    """流入元別 [[sourceType, views, minutes, avgDuration], ...]"""
    res = _yt_analytics.reports().query(
        ids=f"channel=={config.CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views,estimatedMinutesWatched,averageViewDuration",
        dimensions="insightTrafficSourceType",
        filters=f"video=={video_id}",
    ).execute()
    return res.get("rows", [])


def get_search_terms(video_id, start, end):
    """検索流入の検索語上位25件 [[keyword, views], ...]"""
    res = _yt_analytics.reports().query(
        ids=f"channel=={config.CHANNEL_ID}",
        startDate=start, endDate=end,
        metrics="views",
        dimensions="insightTrafficSourceDetail",
        filters=f"video=={video_id};insightTrafficSourceType==YT_SEARCH",
        sort="-views", maxResults=25,
    ).execute()
    return res.get("rows", [])


def get_video_metrics(video_id, start, end):
    """動画の総合指標。視聴維持率(%)・平均視聴秒・登録獲得/喪失・期間再生を返す。
    ※ impressions / CTR は YouTube 公式 Analytics API では提供されない（Studio限定）。"""
    res = _yt_analytics.reports().query(
        ids=f"channel=={config.CHANNEL_ID}", startDate=start, endDate=end,
        metrics="views,averageViewPercentage,averageViewDuration,subscribersGained,subscribersLost",
        filters=f"video=={video_id}",
    ).execute()
    rows = res.get("rows", [])
    if not rows:
        return None
    v = rows[0]
    return {"views": v[0], "avg_view_pct": v[1], "avg_dur": v[2],
            "subs_gained": v[3], "subs_lost": v[4]}


def get_retention_curve(video_id, start, end):
    """視聴者維持の離脱曲線。[(再生位置0-1, 維持率, 相対パフォーマンス), ...]"""
    res = _yt_analytics.reports().query(
        ids=f"channel=={config.CHANNEL_ID}", startDate=start, endDate=end,
        metrics="audienceWatchRatio,relativeRetentionPerformance",
        dimensions="elapsedVideoTimeRatio",
        filters=f"video=={video_id}",
    ).execute()
    return [{"pos": r[0], "watch": r[1], "rel": r[2]} for r in res.get("rows", [])]


def days_since(published):
    pub = datetime.strptime(published, "%Y-%m-%d").date()
    return (date.today() - pub).days


def yesterday_str():
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
