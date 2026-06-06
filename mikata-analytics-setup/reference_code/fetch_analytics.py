"""fetch_analytics.py — YouTube Data/Analytics API からデータを取得"""
from datetime import datetime, date, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import config

_creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
_yt_data = build("youtube", "v3", credentials=_creds)
_yt_analytics = build("youtubeAnalytics", "v2", credentials=_creds)


def get_all_videos():
    """全動画の id / title / published(YYYY-MM-DD) を返す"""
    videos = []
    ch = _yt_data.channels().list(part="contentDetails", id=config.CHANNEL_ID).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    page = None
    while True:
        res = _yt_data.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads,
            maxResults=50, pageToken=page,
        ).execute()
        for it in res["items"]:
            videos.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": it["snippet"]["title"],
                "published": it["contentDetails"]["videoPublishedAt"][:10],
            })
        page = res.get("nextPageToken")
        if not page:
            break
    return videos


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


def days_since(published):
    pub = datetime.strptime(published, "%Y-%m-%d").date()
    return (date.today() - pub).days


def yesterday_str():
    return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
