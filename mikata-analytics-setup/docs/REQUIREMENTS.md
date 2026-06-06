# REQUIREMENTS.md — 要件・設計仕様

「中学受験のミカタ」アナリティクス自動化の確定要件。CLAUDE.md と併せて参照する。

---

## 1. 分析の目的

公開した各動画が「公開直後 → 数日後 → 数週間後」とどう推移するかを、動画間で**同じ経過タイミングどうし**で比較できるようにする。カレンダー日付ではなく、各動画の**公開日からの経過日数**を軸にする。

### 確認したい3点
| # | 観点 | 取得方法 |
|---|---|---|
| 1 | 流入元の違い・流入件数 | dimension `insightTrafficSourceType` |
| 2 | 流入キーワードの違い | dimension `insightTrafficSourceDetail` を `insightTrafficSourceType==YT_SEARCH` でフィルタ |
| 3 | 再生数の伸び方の違い | 経過日数別スナップショットの差分カーブ |

### 計測する経過日数の節目
1 / 3 / 7 / 14 / 28 日。
（検索流入は立ち上がりが遅いため 14・28 日も必須。7日だけだと検索の実力を過小評価する。）

---

## 2. なぜ YouTube API か（vidIQ 不採用の理由）

- 経過時間別（公開日基準）の自動蓄積・再加工は vidIQ では不可。
- データを自前で Sheets に貯めて自由に分析したい → API が必須。
- vidIQ は「これから何を作るか」の企画前KW調査用として併用は可。本パイプラインには組み込まない。

---

## 3. データ収集設計

### 収集方針
- **毎日1回**、全動画（公開後60日以内のものに限定）について収集する。
- 毎日貯めておけば、経過日数 1/3/7/14/28 は後から自由に切り出せる。
- 集計期間は各動画の「公開日 〜 前日」の累計で取得（前日分が確定するため朝に実行）。

### insightTrafficSourceType の主な値
| 値 | 意味 | KPI上の扱い |
|---|---|---|
| YT_SEARCH | YouTube検索 | **真のKPI（最重要）** |
| BROWSE | ブラウズ（ホーム等） | 健全指標 |
| SUGGESTED_VIDEO | 関連動画 | 健全指標 |
| EXT_URL | 外部サイト | ノイズ（約10秒離脱）→ 集計分離 |
| SUBSCRIBER | 登録者・通知 | 初速指標 |

### KPI判断基準（既存の運用方針を踏襲）
- 真のKPIは検索流入・ブラウズ流入。外部流入・管理共有流入は約10秒で離脱するノイズとして分離する。
- 変換率の分母には総視聴ではなく**検索流入ビュー**を使う。
- 判定指標: 視聴時間シェア（主）、検索流入CTR（副）、インプレッションCTR（参考）。

---

## 4. Google Sheets スキーマ

スプレッドシート名: `ミカタ_アナリティクス台帳`（サービスアカウントに編集者で共有）

### シート1: `snapshots`
| 列 | 内容 |
|---|---|
| 取得日 | スクリプト実行日 |
| video_id | 動画ID |
| 動画タイトル | タイトル |
| 公開日 | YYYY-MM-DD |
| 経過日数 | 公開日からの日数 |
| 総再生数 | 全流入合計 |
| 検索流入数 | YT_SEARCH |
| ブラウズ流入数 | BROWSE |
| 関連流入数 | SUGGESTED_VIDEO |
| 外部流入数 | EXT_URL |
| 登録者流入数 | SUBSCRIBER |
| 平均視聴時間(秒) | 検索流入の averageViewDuration |

### シート2: `search_terms`
| 列 | 内容 |
|---|---|
| 取得日 | 実行日 |
| video_id | 動画ID |
| 経過日数 | 公開日からの日数 |
| 検索キーワード | insightTrafficSourceDetail |
| 流入数 | views |

注: 件数の少ない検索語は `(other)` に丸められることがある。網羅は完璧ではない旨をレポートに注記。

---

## 5. レポート設計（analyze.py）

- 隔週実行。`snapshots` から経過日数が 1/3/7/14/28 の行を抽出して Claude API に渡す。
- モデル: `claude-sonnet-4-6`、max_tokens 1500 程度。
- 分析観点:
  1. 検索流入が立ち上がる動画 vs 初速だけで失速する動画の違い
  2. 経過日数ごとの流入元構成変化（初期=登録者/ブラウズ → 後期=検索 への移行度）
  3. 検索流入CTR・視聴時間シェアが高い動画の傾向
- 出力は簡潔に、改善提案つき。判定軸は視聴時間シェア（主）・検索流入CTR（副）。
- **禁止事項（オーナー方針）**: 根拠のない数字断定（「視聴率が○%上がる」等）、再現性を誤解させる数字訴求はしない。

---

## 6. ファイル構成（生成物）

```
~/mikata-analytics/
├ .env                  # APIキー等（gitignore）
├ .gitignore
├ client_secret.json    # 手動取得（gitignore）
├ token.json            # auth.py生成・機密（gitignore）
├ service_account.json  # 手動取得（gitignore）
├ requirements.txt
├ config.py             # CHANNEL_ID・定数・節目日数など
├ auth.py               # 初回OAuth承認（共有アカウントで実行）
├ fetch_analytics.py    # API取得ロジック
├ write_to_sheets.py    # Sheets書き込み
├ main.py               # 毎日の収集オーケストレーション
├ analyze.py            # 隔週レポート生成
├ notify.py             # 通知（send_report(text)）
├ log.txt               # cronログ
└ README.md             # 運用手順
```

---

## 7. crontab 設計

```
# 毎日 朝9時: データ収集
0 9 * * * cd ~/mikata-analytics && ./venv/bin/python main.py >> log.txt 2>&1
# 隔週（第2・第4月曜）朝10時: レポート
0 10 8-14,22-28 * 1 cd ~/mikata-analytics && ./venv/bin/python analyze.py >> log.txt 2>&1
```

スリープ中は cron が止まるため対策する。実行ホストはラップトップ（MacBook Pro M1 Max）なので、**フタを開けたまま・AC給電**で運用すること（フタを閉じると `pmset` 設定に関わらずスリープする。例外は外部ディスプレイ＋給電のクラムシェル運用時のみ）。スリープ自体を止めるには AC給電中スリープ無効化（`sudo pmset -c sleep 0`）、確実に起こすには予約起動（`sudo pmset repeat wakeorpoweron …`）、実行中のスリープ防止には各 cron ジョブの `caffeinate` 併用を用いる。
