# ダッシュボードの常時公開（Streamlit Community Cloud）

外出先・先方と**固定URL・常時稼働**で共有するための手順。URLは変わりません。
（ローカルの一時共有は `./share.sh`＝Cloudflareトンネル。こちらは起動毎にURLが変わる簡易版）

## 仕組み
- データ収集（cron: main.py / watch_new.py）は**手元のMacのまま**でOK（Google Sheets に蓄積）。
- 公開するのは**ダッシュボード（読み取り専用）**だけ。Streamlit Cloud が Sheets と YouTube API を
  Secrets の認証情報で読み、常時表示する。
- コードは `gauth.py` によりローカル=ファイル / クラウド=Secrets を自動切替（同一コードで両対応）。

## 手順
### 1. Secrets を生成
```
./venv/bin/python make_secrets.py
```
→ `.streamlit/secrets.generated.toml` ができる（機密・コミット禁止）。`DASH_PASSWORD` を任意の合言葉に編集。

### 2. GitHub に push（**非公開リポジトリ**推奨）
`.gitignore` で認証情報は除外済み。
```
git init && git add . && git commit -m "mikata analytics dashboard"
gh repo create mikata-analytics --private --source=. --push   # gh CLI 利用時
```
（コミット前に `git status` で `.env` `*.json` `secrets*.toml` が含まれないことを確認）

### 3. Streamlit Community Cloud でデプロイ
1. https://share.streamlit.io にGitHubでサインイン
2. 「New app」→ リポジトリ `mikata-analytics`、ブランチ `main`、Main file `dashboard.py`
3. 「Advanced settings > Secrets」に **手順1で生成した toml の中身を貼り付け**
4. Deploy → `https://<アプリ名>.streamlit.app` が固定URLとして発行

### 4. 共有
- 発行URLを外出先の自分／先方に共有。`DASH_PASSWORD` で閲覧保護。
- 数値は10分キャッシュで自動更新。データ自体は手元cronが日次/毎時で更新。

## 注意
- Secrets（service_account / token）は**絶対に公開リポジトリに置かない**。必ず非公開＋Secrets経由。
- token は refresh_token を含むため Cloud 側で自動更新される（再ログイン不要）。
- 無料枠はリソース上限あり。重い場合は閲覧者を限定（Streamlit の Viewer 制限）も可能。
