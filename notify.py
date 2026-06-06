"""notify.py — 通知。send_report(text) のみが公開インターフェース。

通知手段はメール送信（SMTP）。LINE Notify は 2025-03-31 にサービス終了したため不採用。
別手段（LINE Messaging API / Discord / Slack）に切り替える場合も、呼び出し側
(analyze.py) は send_report(text) だけを使うので、このファイルを直せば全体が追従する。

必要な .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO
（Gmail の場合: 2段階認証を有効化し「アプリパスワード」を発行して SMTP_PASS に設定）
"""
import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate
import config

SUBJECT = "【中学受験のミカタ】隔週アナリティクスレポート"


def send_report(text):
    """レポート本文を通知する。失敗してもレポート自体は標準出力に残る。"""
    if not (config.SMTP_USER and config.SMTP_PASS and config.MAIL_TO):
        print("[notify] メール設定 (SMTP_USER/SMTP_PASS/MAIL_TO) 未設定。標準出力のみ。")
        return
    try:
        _send_mail(text)
    except Exception as e:
        print(f"[notify] 送信失敗: {e}")


def _send_mail(text):
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = SUBJECT
    msg["From"] = config.SMTP_USER
    msg["To"] = config.MAIL_TO
    msg["Date"] = formatdate(localtime=True)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASS)
        server.send_message(msg)
    print(f"[notify] 送信完了 -> {config.MAIL_TO}")
