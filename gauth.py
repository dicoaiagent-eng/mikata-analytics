"""gauth.py — 認証情報のデュアルモード取得。

ローカル実行（cron/手元）: service_account.json / token.json のファイルを使用。
クラウド実行（Streamlit Community Cloud 等）: st.secrets から読み込む。
これにより同一コードでローカルとクラウドの両方を動かせる。

Streamlit secrets の例（.streamlit/secrets.toml.example 参照）:
  [gcp_service_account] … service_account.json の中身
  [youtube_token]       … token.json の中身
"""
import config


def _from_secrets(name):
    """st.secrets[name] を dict で返す。無い/Streamlit外なら None。"""
    try:
        import streamlit as st
        if name in st.secrets:
            return dict(st.secrets[name])
    except Exception:
        pass
    return None


def gspread_client():
    """Google Sheets 用 gspread クライアント（Secrets優先・無ければファイル）。"""
    import gspread
    sa = _from_secrets("gcp_service_account")
    if sa:
        return gspread.service_account_from_dict(sa)
    return gspread.service_account(filename=config.SERVICE_ACCOUNT)


def open_sheet():
    """設定のスプレッドシートを開く。"""
    return gspread_client().open(config.SHEET_NAME)


def youtube_credentials():
    """YouTube API 用 OAuth 認証情報（Secrets優先・無ければファイル）。
    どちらも refresh_token を含むためトークンは自動更新される。"""
    from google.oauth2.credentials import Credentials
    tok = _from_secrets("youtube_token")
    if tok:
        return Credentials.from_authorized_user_info(tok, config.SCOPES)
    return Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
