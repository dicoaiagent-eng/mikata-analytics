"""auth.py — 初回OAuth承認。共有アカウント mikata.negi@gmail.com で承認すること。"""
from google_auth_oauthlib.flow import InstalledAppFlow
import config


def main():
    print("=" * 60)
    print(" ブラウザが開きます。")
    print(" 必ず共有アカウント mikata.negi@gmail.com でログインして承認してください。")
    print(" 「確認されていません」表示時は 詳細 → プロジェクトに移動 で続行。")
    print("=" * 60)
    flow = InstalledAppFlow.from_client_secrets_file(config.CLIENT_SECRET, config.SCOPES)
    creds = flow.run_local_server(port=0)
    with open(config.TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print("認証完了: token.json を生成しました。このファイルは機密です。")


if __name__ == "__main__":
    main()
