# MANUAL_STEPS.md — 人間（濱岡）が手動で行う操作

セキュリティ上、自動化できない・すべきでない操作だけをここに集約した。
Claude Code はこの3点に到達したら作業を止め、オーナーに依頼すること。それ以外は自走してよい。

---

## 手動① OAuthクライアントID（client_secret.json）の取得

Google Auth Platform（旧OAuth同意画面）でデスクトップアプリのクライアントを作る。

1. https://console.cloud.google.com を開く（プロジェクト `mikata-analytic` を選択）
2. 左メニュー「Google Auth Platform」→「クライアント」
3. 「+ クライアントを作成」
4. アプリケーションの種類: **デスクトップアプリ**
5. 名前: 例 `mikata-desktop` → 「作成」
6. 作成後ダイアログ、または一覧の⬇アイコンから **JSONをダウンロード**
7. ダウンロードした JSON を `~/mikata-analytics/client_secret.json` にリネームして配置

```bash
mv ~/Downloads/client_secret_*.json ~/mikata-analytics/client_secret.json
```

### 併せて: 3つのAPIの有効化（Claudeが gcloud で実行可。手動でやる場合のみ以下）
コンソール上部の検索窓で各APIを開き「有効にする」:
- YouTube Data API v3
- YouTube Analytics API
- Google Sheets API

---

## 手動② auth.py の初回ブラウザ承認（★共有アカウントで）

`client_secret.json` 配置後、ターミナルで:

```bash
cd ~/mikata-analytics
./venv/bin/python auth.py
```

1. ブラウザが自動で開く
2. **必ず `mikata.negi@gmail.com`（共有アカウント）でログイン**（仕事用と取り違えない）
3. 「このアプリは Google で確認されていません」と出たら →「詳細」→「(プロジェクト名)に移動」
4. 権限（YouTube/Analytics の読み取り）を許可
5. `token.json` が生成されれば完了

※ 共有アカウントに2段階認証がある場合、その場で認証コードの入力が必要。
※ `token.json` は実質チャンネルへのアクセス鍵。Drive同期・共有・git管理しないこと。

---

## 手動③ Google Sheets の作成とサービスアカウント共有

1. サービスアカウントのキー JSON を取得（Claudeが gcloud で作成可。手動の場合は Cloud Console「IAMと管理」→「サービスアカウント」→ キーを追加 → JSON）→ `~/mikata-analytics/service_account.json` に配置
2. ブラウザで Google スプレッドシートを新規作成、名前を **`ミカタ_アナリティクス台帳`** にする
3. そのシートを、`service_account.json` 内の `client_email`（`xxx@xxx.iam.gserviceaccount.com`）に **編集者** で共有
   - サービスアカウントのメールは次で確認できる:
     ```bash
     grep client_email ~/mikata-analytics/service_account.json
     ```
4. シートのオーナーは仕事用・共有どちらのアカウントでも可（共有さえすれば動く）

※ ヘッダー行や2枚目のシート（`search_terms`）は Claude Code がスクリプトで自動作成してよい。

---

## 完了後

上記3点が終わったら Claude Code に「手動部分完了」と伝える。
以降の動作確認（main.py 実行 → Sheets書き込み確認 → analyze.py → cron登録）は Claude が自走する。
