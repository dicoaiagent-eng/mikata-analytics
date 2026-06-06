"""config.py — 定数と環境変数の集約"""
import os
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
SHEET_NAME = os.environ.get("SHEET_NAME", "ミカタ_アナリティクス台帳")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LINE_TOKEN = os.environ.get("LINE_TOKEN", "")

# 経過日数の節目
MILESTONES = [1, 3, 7, 14, 28]
# 追跡対象は公開後この日数以内
MAX_TRACK_DAYS = 60
# レポート生成モデル
CLAUDE_MODEL = "claude-sonnet-4-6"

# 認証ファイル
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.json"
SERVICE_ACCOUNT = "service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
