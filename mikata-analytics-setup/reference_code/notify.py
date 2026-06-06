"""notify.py — 通知。send_report(text) のみが公開インターフェース。

LINE Notify はサービス終了の経緯があるため、実装着手時に現行手段を確認すること。
使えない場合は send_report の中身を差し替える（Discord/Slack Webhook, メール等）。
呼び出し側 (analyze.py) は send_report(text) だけを使うので、ここを直せば全体が追従する。
"""
import urllib.request
import urllib.parse
import config


def send_report(text):
    """レポート本文を通知する。失敗してもレポート自体は標準出力に残る。"""
    if not config.LINE_TOKEN:
        print("[notify] 通知トークン未設定。標準出力のみ。")
        return
    try:
        _send_line_notify(text)
    except Exception as e:
        print(f"[notify] 送信失敗: {e}")


def _send_line_notify(text):
    """旧LINE Notify方式。終了済みなら別関数に差し替える。"""
    req = urllib.request.Request(
        "https://notify-api.line.me/api/notify",
        data=urllib.parse.urlencode({"message": "\n" + text}).encode(),
        headers={"Authorization": f"Bearer {config.LINE_TOKEN}"},
    )
    urllib.request.urlopen(req, timeout=15)
    print("[notify] 送信完了")


# --- 代替案（必要時にコメント解除して send_report から呼ぶ） ---
# def _send_discord(text):
#     req = urllib.request.Request(
#         config.LINE_TOKEN,  # ここをDiscord Webhook URLにする
#         data=json.dumps({"content": text[:1900]}).encode(),
#         headers={"Content-Type": "application/json"},
#     )
#     urllib.request.urlopen(req, timeout=15)
