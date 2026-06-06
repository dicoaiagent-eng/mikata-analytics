"""make_secrets.py — ローカルの認証ファイルから Streamlit Cloud 用 secrets.toml を生成。

実行: ./venv/bin/python make_secrets.py
  → .streamlit/secrets.generated.toml を出力（.gitignore対象）。
    中身を Streamlit Cloud の App settings > Secrets に貼り付ける。
"""
import json
import os
import config


def _toml_table(name, data):
    lines = [f"[{name}]"]
    for k, v in data.items():
        if isinstance(v, list):
            inner = ", ".join(json.dumps(x, ensure_ascii=False) for x in v)
            lines.append(f"{k} = [{inner}]")
        else:
            lines.append(f"{k} = {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines)


def main():
    parts = []
    parts.append(f'CHANNEL_ID = {json.dumps(config.CHANNEL_ID)}')
    parts.append(f'SHEET_NAME = {json.dumps(config.SHEET_NAME, ensure_ascii=False)}')
    parts.append('DASH_PASSWORD = "CHANGE_ME"  # 共有時の閲覧パスワードに変更')
    parts.append("")
    with open(config.SERVICE_ACCOUNT, encoding="utf-8") as f:
        parts.append(_toml_table("gcp_service_account", json.load(f)))
    parts.append("")
    with open(config.TOKEN_FILE, encoding="utf-8") as f:
        parts.append(_toml_table("youtube_token", json.load(f)))
    content = "\n".join(parts) + "\n"

    os.makedirs(".streamlit", exist_ok=True)
    out = ".streamlit/secrets.generated.toml"
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"生成しました: {out}")
    print("→ この中身を Streamlit Cloud の Secrets に貼り付けてください（DASH_PASSWORD は変更）。")
    print("※ 機密情報です。リポジトリにコミットしないでください（.gitignore 済み）。")


if __name__ == "__main__":
    main()
