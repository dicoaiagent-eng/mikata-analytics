# 中学受験のミカタ アナリティクス自動化 — 運用 README

YouTube チャンネル「中学受験のミカタ」の動画パフォーマンスを **公開日からの経過日数別** に
毎日自動収集し、隔週で AI レポート化する仕組みの運用手順書。

- **実行ホスト**: 自宅で常時稼働の **MacBook Pro (Apple M1 Max / 64GB)**。AC給電・**フタは開けたまま**運用する。
- **MacBook Air は持ち出し用。自動化には一切使わない（対象外）。**
- 配置場所: `~/mikata-analytics`（**Google Drive 配下は厳禁** — `token.json`/`venv` の同期事故防止）

---

## 1. 構成

| ファイル | 役割 |
|---|---|
| `auth.py` | 初回 OAuth 承認。`token.json` を生成（**ブランドアカウントで承認**） |
| `main.py` | 毎日の収集オーケストレーション（Data/Analytics → Sheets 追記） |
| `watch_new.py` | **毎時の新着監視**。新着検知→メタ記録(`videos_master`)＋公開7日以内の総再生数を `hourly_views` に追記 |
| `classify.py` | 新着タイトルの**訴求型6分類**（Claude `claude-haiku-4-5`） |
| `dashboard.py` | **ダッシュボード**（Streamlit）。各シートを5分キャッシュで可視化 |
| `fetch_analytics.py` | YouTube Data / Analytics API からの取得 |
| `write_to_sheets.py` | Google Sheets 書き込み（シート/ヘッダー自動作成） |
| `analyze.py` | 隔週レポート生成（Anthropic API）→ `notify` で通知 |
| `notify.py` | 通知。`send_report(text)` が公開IF。現状はメール(SMTP)／未設定時は標準出力 |
| `config.py` + `.env` | 設定・環境変数（`.env` は機密、git/同期しない） |
| `cron_collect.sh` | 毎日収集の cron ラッパー（caffeinate + ログ） |
| `cron_watch.sh` | **毎時の新着監視**の cron ラッパー（caffeinate + `logs/watch.log`） |
| `cron_report.sh` | 隔週レポートの cron ラッパー（偶数ISO週のみ実行＝隔週） |
| `run_dashboard.sh` | ダッシュボード起動（`0.0.0.0` バインド＝LAN内の他端末から閲覧可） |

### 確定設定値

| 項目 | 値 |
|---|---|
| 対象チャンネル | 中学受験の ミカタ ちゃんねる（ブランドアカウント） |
| `CHANNEL_ID` | `UCe5B8u9xJAqcvK91peXey5Q` |
| Google Cloud プロジェクト | `mikata-analytic`（番号 `423007589947`） |
| OAuth 承認アカウント | `mikata.negi@gmail.com` → **選択画面で「中学受験のミカタちゃんねる」を選ぶ** |
| サービスアカウント | `mikata-sheets@mikata-analytic.iam.gserviceaccount.com` |
| スプレッドシート名 | `ミカタ_アナリティクス台帳`（シート: `snapshots` / `search_terms` / `videos_master` / `hourly_views`） |
| レポートモデル | `claude-sonnet-4-6` |
| 必須API | YouTube Data API v3 / YouTube Analytics API / Google Sheets API / **Google Drive API** |

### 認証ファイル（すべて機密・git/同期しない）

- `client_secret.json` … OAuth クライアント（デスクトップアプリ）
- `token.json` … OAuth 承認結果（実質チャンネルのアクセス鍵）
- `service_account.json` … Sheets 書き込み用サービスアカウント鍵

---

## 2. 自動実行（cron）

```cron
# 毎日 6:00 — データ収集
0 6 * * * /Users/kazukihamaoka_macbookpro/mikata-analytics/cron_collect.sh
# 毎週月曜 6:10 — レポート（スクリプト内で偶数ISO週のみ実行＝隔週）
10 6 * * 1 /Users/kazukihamaoka_macbookpro/mikata-analytics/cron_report.sh
# 毎時 10分 — 新着監視 + 公開7日以内の総再生数追跡
10 * * * * /Users/kazukihamaoka_macbookpro/mikata-analytics/cron_watch.sh
```

- 確認: `crontab -l`
- **隔週レポート**: 毎週月曜に起動するが `cron_report.sh` が **ISO週番号が偶数の週だけ** `analyze.py` を実行する。
  奇数週は `logs/report.log` に「skip」とだけ記録。初回発火は **2026-06-08（週24）**、以降 週26, 28 …。
  ※ 年末年始（週52→週1）は週番号の連続性が崩れ、まれにレポート間隔が1週ずれることがある。
- 各ジョブは `caffeinate -i` でラップ済み（**実行中**のアイドルスリープを防止。ただし寝ているMacを起こす機能はない）。

### 手動で実行したいとき

```bash
cd ~/mikata-analytics
./venv/bin/python main.py        # 収集を今すぐ
./venv/bin/python watch_new.py   # 新着監視を今すぐ（videos_master / hourly_views を更新）
./venv/bin/python analyze.py     # レポートを今すぐ（隔週ゲートを無視して実行される）
./cron_collect.sh                # cron と同じ経路で収集（ログにも残る）
./cron_watch.sh                  # cron と同じ経路で新着監視（logs/watch.log に残る）
./cron_report.sh                 # 偶数週のみ実行。奇数週は skip ログのみ
```

---

## 3. ログの見方

```bash
cd ~/mikata-analytics
tail -n 40 logs/collect.log      # 毎日収集のログ
tail -n 40 logs/watch.log        # 毎時の新着監視のログ
tail -n 40 logs/report.log       # 隔週レポートのログ
tail -f  logs/collect.log        # リアルタイム追従
```

- 各実行は `==== YYYY-MM-DD HH:MM:SS collect start ====` 〜 `end (exit N)` で囲まれる（`watch` も同形式）。
- `exit 0` が正常終了。`main.py` 正常時は末尾に `完了: snapshot N本 / term N行 を追記`。
- `watch_new.py` 正常時は末尾に `完了: 新着 N本 / hourly N行 を追記`。
- レポートは `analyze.py` の本文がそのままログに出る。メール未設定なら `[notify] … 標準出力のみ。`

---

## 4. トラブル対処

### A. cron が動かない（ログに何も出ない）
1. **スリープ中だった**（最有力）: 6:00/6:10 にMacが寝ていると cron は発火しない。下記「H. スリープ」参照。
2. **フルディスクアクセス未許可**: 下記「C」参照。
3. **crontab が消えている**: `crontab -l` で確認。空なら §2 の内容で再登録。
4. **パス間違い**: ラッパーは絶対パスで登録済み。`ls -l ~/mikata-analytics/cron_*.sh` で実行権限(x)を確認、無ければ `chmod +x cron_collect.sh cron_report.sh`。

### B. token が失効した（`logs` に `invalid_grant` / `RefreshError` / 401 等）
原因: 承認の取り消し、長期未使用、パスワード変更、テスト公開ステータスのトークン期限 等。
対処（**必ずブランドアカウントで再承認**）:
```bash
cd ~/mikata-analytics
rm -f token.json
./venv/bin/python auth.py
```
ブラウザで `mikata.negi@gmail.com` ログイン → **「中学受験のミカタちゃんねる」を選択** → 権限許可 → `token.json` 再生成。

### C. フルディスクアクセス（cron がファイルにアクセスできない / 初回ダイアログ）
`システム設定 → プライバシーとセキュリティ → フルディスクアクセス` に **`cron`（`/usr/sbin/cron`）** を追加して有効化。
（追加には `+` → `Cmd+Shift+G` で `/usr/sbin/cron` を指定）。追加後、次回 6:00 から有効。

### D. チャンネルの取り違え（再生数/動画数が 0、Analytics が 403）
症状: `mine=true` 系で名前は合っているのに登録者・動画・再生が全部 0、Analytics API が **403 Forbidden**。
原因: 承認時に **空のチャンネル側** を選んでいる（本物はブランドアカウント `UCe5B8u9xJAqcvK91peXey5Q`）。
対処: 上記「B」と同じ手順で `token.json` を作り直し、選択画面で **「中学受験のミカタちゃんねる」** を選ぶ。
検証の目安: Analytics の `views` が 200 で返れば権限OK。

### E. Sheets 共有のやり直し（`SpreadsheetNotFound` / アクセス可能シート 0 件）
原因: スプレッドシートがサービスアカウントに共有されていない／別アドレスに共有した／シート名不一致。
対処:
1. スプレッドシート名が **`ミカタ_アナリティクス台帳`** ちょうどか確認（`.env` の `SHEET_NAME` と一致必須）。
2. シート右上「共有」に下記を **編集者** で追加（タイプミス注意）:
   `mikata-sheets@mikata-analytic.iam.gserviceaccount.com`
3. サービスアカウントが見えているシートを確認:
   ```bash
   ./venv/bin/python -c "import gspread,config; gc=gspread.service_account(filename=config.SERVICE_ACCOUNT); print([f['name'] for f in gc.list_spreadsheet_files()])"
   ```
   0件なら共有が届いていない。正しいアドレスで共有し直す。
4. サービスアカウントのメールを確認したいとき:
   ```bash
   grep client_email service_account.json
   ```

### F. Google Drive API 未有効（`Drive API has not been used … or it is disabled`）
`gspread` はシートを名前で開く際に Drive API を使う。
対処: https://console.cloud.google.com でプロジェクト `mikata-analytic` を選び、**Google Drive API** を「有効にする」。反映に1〜2分。
（あわせて Sheets / YouTube Data / YouTube Analytics の各APIも有効である必要がある）

### G. Anthropic API エラー（レポートが生成されない）
- `.env` の `ANTHROPIC_API_KEY`（`sk-ant-…`）が設定済みか、残高があるか確認。
- 存在確認（値は表示しない）:
  ```bash
  ./venv/bin/python -c "import config; k=config.ANTHROPIC_API_KEY; print('set' if k else 'EMPTY', len(k))"
  ```

### H. スリープで cron が止まる（ラップトップ運用の要点）
- **大前提: フタを開けたまま・AC給電。** MacBook はフタを閉じると `pmset` 設定に関わらずスリープする（例外は外部ディスプレイ＋給電のクラムシェル運用のみ）。
- 現状はスリープ対策（pmset）を入れていない（普段その時間帯は起動している前提）。取りこぼしが続く場合は以下を検討（いずれも `sudo` 必要）:
  ```bash
  sudo pmset -c sleep 0 disksleep 0                       # AC給電中はスリープさせない（推奨・本命）
  sudo pmset repeat wakeorpoweron MTWRFSU 05:55:00        # 毎日5:55に自動起動（保険）
  ```
  確認: `pmset -g | grep sleep` / `pmset -g sched`
- cron ジョブ自体は `caffeinate -i` ラップ済みなので、**実行が始まれば**途中スリープで中断はしない。

---

## 5. 通知（メール）を有効にする（任意）

現状レポートは標準出力＋`logs/report.log` のみ。メールで受け取るには `.env` に設定:

| キー | 値 |
|---|---|
| `SMTP_HOST` | `smtp.gmail.com`（既定） |
| `SMTP_PORT` | `587`（既定） |
| `SMTP_USER` | 送信元 Gmail アドレス |
| `SMTP_PASS` | Gmail **アプリパスワード**（2段階認証を有効化し https://myaccount.google.com/apppasswords で発行。スペースは詰める） |
| `MAIL_TO` | 受信先アドレス |

設定後のテスト:
```bash
./venv/bin/python -c "import notify; notify.send_report('テスト送信です')"
```
`[notify] 送信完了 -> <宛先>` が出れば成功。LINE Notify はサービス終了済みのため不採用。
別手段（Discord/Slack Webhook 等）に変える場合も `notify.py` の `send_report(text)` だけ差し替えれば全体が追従する。

---

## 6. 分析の核（仕様メモ）

動画ごとに公開日からの経過日数（`day_since_publish`）軸でスナップショットを蓄積し、
**1 / 3 / 7 / 14 / 28 日** の節目で「流入元」「流入キーワード（YT_SEARCH）」「再生数の伸び」を比較する。
追跡対象は公開後 `MAX_TRACK_DAYS`（=60日）以内の動画（`config.py`）。

---

## 7. 新着監視（watch_new.py / 毎時）

- **対象は公開(public)動画のみ**: オーナーOAuthのuploads再生リストには限定公開(unlisted)・非公開(private)も含まれるため、`videos.list` の `status.privacyStatus` で **public のみ** に絞って記録する（`watch_new.py` / `backfill_master.py` 共通）。
- **新着検知**: uploads再生リスト先頭ページと `videos_master` の差分。uploadsリストIDは `UC…`→`UU…` 変換で導出（API節約）。
- **初回バックフィル `backfill_master.py`**: 既存の全公開動画を `videos_master` に一括登録（記録済みIDはスキップ＝毎時cronと重複しない）。`./venv/bin/python backfill_master.py`。
- **記録先 `videos_master`（1動画1行）**: `video_id / タイトル / 公開日時 / 公開曜日 / 公開時刻 / video_type / 動画長(秒) / タグ / 説明文 / 訴求型 / 初回記録日時`
- **ショート/長尺判定 `video_type`**: 動画長 > `SHORTS_MAX_SEC`(=180秒) は即 `long`。180秒以下のみ `https://www.youtube.com/shorts/{id}` へリクエストし、**200=short / 3xxリダイレクト=long**。判定不能時は安全側で `long`。
- **訴求型6分類**（`classify.py` / `claude-haiku-4-5`）: 逆説フック型 / 感情セリフ型 / 数字インパクト型 / 情緒物語性型 / 親サポート軸型 / 時代性脱常識型。失敗時は空欄。
- **伸びカーブ `hourly_views`**: 公開後 `WATCH_DAYS`(=7日) 以内の動画（長尺・ショート両方）について、毎時の**総再生数（Data API `viewCount`）**を追記。`取得時刻 / video_id / video_type / 経過時間(h) / viewCount`。
- **オーナー方針**: Analytics API は約2日遅れのため毎時追跡には**使わない**。毎時は Data API の `viewCount` のみ。
- 既存 `snapshots` にも `公開曜日 / 公開時刻 / video_type` 列を追加済み（**新規行から値が入る**。既存行は空欄のまま）。
- **初回実行の注意**: 初回は先頭ページの既存動画がまとめて新着扱いになり、その本数ぶん訴求型分類（Claude）が走る（一度きり）。

## 8. ダッシュボード（dashboard.py / Streamlit）

```bash
cd ~/mikata-analytics
./run_dashboard.sh               # 0.0.0.0:8501 で起動
ipconfig getifaddr en0           # このMacのLAN IPを確認（Wi-Fiは en0、有線は en0/en1）
```

- **閲覧URL**: 同じMacからは `http://localhost:8501`、**自宅LAN内の他端末（スマホ/別PC）からは `http://<上記LAN IP>:8501`**。
- 各シートを **5分キャッシュ**（`ttl=300`）で読み込み。右上「🔄 キャッシュを更新」で即時再取得。
- 表示: ①直近動画一覧（長尺/ショートのバッジ・訴求型・公開日時）②公開後の伸びカーブ（動画選択＋長尺/ショート切替）③曜日×公開時間帯の初動比較 ④訴求型別パフォーマンス ⑤検索流入KWランキング。
- **断定回避**: ③④はサンプル数(n)を併記し、n が少ないうちは「傾向の示唆に留める」注記を表示（オーナー方針）。
- 停止は起動ターミナルで `Ctrl+C`。LANの他端末から見えない場合は同一Wi-Fi接続とMacのファイアウォール設定（受信接続の許可）を確認。
