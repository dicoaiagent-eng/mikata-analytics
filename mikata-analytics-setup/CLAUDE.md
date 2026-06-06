# CLAUDE.md — 中学受験のミカタ アナリティクス自動化プロジェクト

このファイルは Claude Code がこのプロジェクトで作業する際の最上位の指示書です。
作業開始時に必ず全文を読み、`docs/` 配下の各仕様書も参照してください。

---

## 0. このプロジェクトの目的（1行）

YouTubeチャンネル「中学受験のミカタ」の動画パフォーマンスを、**公開日からの経過日数別**に自動収集・蓄積し、隔週でAIレポート化してLINEに通知する仕組みを、自宅で常時稼働させているMacBook Pro (M1 Max) 上に構築する。

---

## 1. 作業の進め方（重要・自動進行ルール）

オーナー（濱岡）は確認の手間を最小化したいと明確に希望している。以下を厳守すること。

- **自走を優先する。** 判断に迷ったら、本ファイルと `docs/REQUIREMENTS.md` の方針に沿って自分で決めて進める。逐一確認を求めない。
- **確認を求めてよい例外は次の3点のみ：**
  1. 不可逆な破壊的操作（既存ファイルの大量削除、`rm -rf` を伴う操作）
  2. 課金が発生しうる操作
  3. `docs/MANUAL_STEPS.md` に記載された「人間が手動で行う必要がある操作」に到達したとき
- 上記以外（ファイル生成・編集、pip install、venv作成、ローカルでのスクリプト実行、テスト実行、gcloud の有効化コマンド等）は**確認なしで実行**してよい。
- 作業はサブエージェント（`.claude/agents/`）に適切に委譲し、メインスレッドは進行管理に徹する。
- 各フェーズ完了時に、何をしたか1〜3行で簡潔に報告する。長い説明は不要。

---

## 2. 絶対に守る制約（セキュリティ・配置）

- **配置場所はローカルのホーム直下 `~/mikata-analytics` 固定。** Google Drive（マイドライブ）配下には絶対に置かない。`token.json` や `venv` がクラウド同期されると事故になるため。
- `token.json` / `client_secret.json` / `service_account.json` は**機密**。これらをログ出力・git管理・クラウド同期させない。`.gitignore` に必ず含める。
- 認証情報の中身（キー文字列等）をターミナルに表示しない。
- APIキー等は環境変数で渡す（`.env` を使い、`.env` も `.gitignore` 対象）。

---

## 3. 確定済みの技術仕様（詳細は docs/REQUIREMENTS.md）

- 実行ホスト: 自宅で常時稼働の MacBook Pro (Apple M1 Max / 64GB)。AC給電・フタを開けたまま運用する（ラップトップのためフタを閉じるとスリープする点に注意）。持ち出し用の MacBook Air は自動化には使わない。
- 言語: Python 3 / venv
- 主要ライブラリ: `google-api-python-client` `google-auth-oauthlib` `gspread` `anthropic` `python-dotenv`
- データ収集: YouTube Data API v3 + YouTube Analytics API
- 蓄積先: Google Sheets（`gspread` + サービスアカウント）
- レポート生成: Anthropic API（モデル: `claude-sonnet-4-6`）
- 通知: LINE（※下記注意。実装前に最新の通知手段を確認すること）
- 自動実行: crontab（毎日のデータ収集 + 隔週のレポート）

### 分析の核（必ず実装すること）
動画ごとに「公開日からの経過日数（day_since_publish）」を軸にスナップショットを蓄積し、
経過日数 **1 / 3 / 7 / 14 / 28 日** の節目で以下3点を比較分析できるようにする：
1. 流入元の違いと流入件数（`insightTrafficSourceType`）
2. 流入キーワードの違い（`insightTrafficSourceDetail` を `YT_SEARCH` でフィルタ）
3. 再生数の伸び方の違い（スナップショット差分カーブ）

---

## 4. アカウント方針（確定）

- Google Cloud プロジェクト名: `mikata-analytic`（作成済み）
- OAuth同意画面: 作成済み・公開ステータス「テスト中」・ユーザー種類「外部」
- テストユーザー登録済み: `mikata.negi@gmail.com`（= 対象YouTubeチャンネルを操作できる共有アカウント）
- **OAuth承認は共有アカウント `mikata.negi@gmail.com` で行う**（auth.py 実行時のブラウザ承認。これは人間の手動操作 = MANUAL_STEPS）。
- Cloud Console のプロジェクト管理自体は濱岡の仕事用アカウントでよい。

---

## 5. LINE通知に関する注意（実装前に必ず確認）

LINE Notify はサービス終了が告知された経緯がある。実装着手前に現行で使える通知手段を確認し、
使えない場合は代替（LINE Messaging API / Discord Webhook / Slack Webhook / メール送信）に切り替える。
通知部分は差し替えやすいよう `notify.py` として独立させ、関数 `send_report(text)` のインターフェースを固定する。

---

## 6. 想定コスト（参考・超過時は報告）

- Anthropic API: 約 $0.06/月
- 電気代: 約 ¥250/月
- Google API / Sheets: 無料枠内

---

## 7. 完成の定義（Definition of Done）

1. `~/mikata-analytics` にローカル構築されている（Drive外）
2. `auth.py` で共有アカウント承認 → `token.json` 生成済み（※人間が実施）
3. `main.py` 手動実行で Sheets にスナップショット行が追記される
4. `analyze.py` 手動実行で経過日数別レポートが生成され `notify.py` で通知が飛ぶ
5. crontab に毎日収集 + 隔週レポートが登録されている
6. README に運用手順（手動でやること・トラブル時の対処）がまとまっている

---

## 8. 着手順（推奨）

1. `docs/` を全部読む
2. `setup.sh` の内容を確認し、ローカル環境を構築（venv・pip）
3. Pythonファイル一式を生成（`config.py` `fetch_analytics.py` `write_to_sheets.py` `main.py` `analyze.py` `notify.py` `auth.py`）
4. LINE通知の現行手段を確認 → `notify.py` 確定
5. `MANUAL_STEPS.md` をオーナーに提示し、手動部分（クライアントID取得・auth.py承認・Sheets共有）を依頼
6. 手動部分完了後、`main.py` をテスト実行 → Sheets書き込み確認
7. `analyze.py` テスト → crontab 登録
