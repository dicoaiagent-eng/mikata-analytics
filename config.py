"""config.py — 定数と環境変数の集約"""
import os
from dotenv import load_dotenv

# override=True: 実行環境(例: Claude Desktop)が空の ANTHROPIC_API_KEY 等を
# 注入していても、.env の値を常に優先する。
load_dotenv(override=True)


def _env(key, default=""):
    """環境変数(.env)優先。無ければ Streamlit secrets（クラウド実行用）。"""
    v = os.environ.get(key)
    if v not in (None, ""):
        return v
    try:  # Streamlit Cloud では secrets から取得（cron等の非Streamlit環境では無視）
        import streamlit as st
        return str(st.secrets.get(key, default))
    except Exception:
        return default


CHANNEL_ID = _env("CHANNEL_ID", "")
SHEET_NAME = _env("SHEET_NAME", "ミカタ_アナリティクス台帳")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# メール通知 (notify.py)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
MAIL_TO = os.environ.get("MAIL_TO", "")

# 経過日数の節目
MILESTONES = [1, 3, 7, 14, 28]
# 追跡対象は公開後この日数以内
MAX_TRACK_DAYS = 60
# レポート生成モデル
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- 新着監視 (watch_new.py) ---
# 毎時の総再生数追跡対象は公開後この日数以内（伸びカーブ用）
WATCH_DAYS = 7
# ショート判定の事前フィルタ閾値（秒）。これ超は即 long
SHORTS_MAX_SEC = 180
# 訴求型6分類に使うモデル（分類は安価なモデルで十分）
CLASSIFY_MODEL = "claude-haiku-4-5"
# 公開日時を日本時間に変換するオフセット（曜日・時刻の算出用）
JST_OFFSET_HOURS = 9

# --- ダッシュボード ---
# 登録者数の目標（目標達成度メーター用）
# ※オーナー確認前の仮値。確定後にこの値を更新する（UI上も「(仮)」と表示）。
SUBSCRIBER_GOAL = 10000
# 外部共有時の閲覧パスワード（.env / secrets の DASH_PASSWORD）。未設定なら認証なし。
DASHBOARD_PASSWORD = _env("DASH_PASSWORD", "")

# 競合比較の対象チャンネル（中学受験系・公開指標で比較）。自由に追加/削除可。
COMPETITOR_CHANNEL_IDS = [
    "UCLMmcT54e-pAIg80atX440g",  # にしむら先生 受験指導専門家
    "UCpmIx1eakUt4zHDLTzUF7eA",  # 中学受験に向けた子育てch【伸学会菊池洋匡】
    "UCVxg1EE8Efu6M2WyYg6zYPA",  # こばちゃん塾
    "UCMsGJLObNXr1D85bOQRTwRQ",  # 佐藤ママチャンネル
    "UCrzGSHJCmwNmFvfpveN1I-w",  # 中学受験のrestart
    "UC3LgVYRHHKxo0RkziCsgp6g",  # けいたくチャンネル
    "UC35PZPRvt3OBQ10dYj2k61w",  # ホンネで中学受験
    "UC4l3tsbEKsVMQZGinyNrX7Q",  # 中学受験コベツバ
    "UC42OqT3RNzSgOtvj27m0tRg",  # りゅうりゅうりゅう中学受験
    "UCobcUEocQ90C4C3uZfqxGyg",  # テスティー中学受験チャンネル
]

# 認証ファイル
CLIENT_SECRET = "client_secret.json"
TOKEN_FILE = "token.json"
SERVICE_ACCOUNT = "service_account.json"

SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
