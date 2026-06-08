"""dashboard.py — 中学受験のミカタ アナリティクス・ダッシュボード (Streamlit / ライトテーマ)

タブ: サマリー / カタログ / ディープダイブ / 伸び比較 / 分析 / 検索キーワード

確定デザイン要件:
  ライトテーマ（背景#FAFAFA/カード#FFFFFF/罫線#EAEAEA/本文#1A1A1A/補助#8A8A8A）。
  アクセントは3色固定（#E9965B オレンジ主役 / #82B5F6 ブルー補助 / #D50403 アラート専用）。
  グレー以外の新規色は導入しない。
  ※訴求型(タイトル分類)は「サムネ要因が主」という判断で現状UIから除外（データは保持）。
分析方針:
  ノイズ流入(外部)はデフォルト除外（サイドバーで切替）。比較系の代表値は中央値。
  サンプル数 n を常時併記し n<5 は参考値（グレーアウト）。維持率は「検索流入」基準。
"""
import altair as alt
import gspread
import pandas as pd
import streamlit as st

import config
import insights as ins
import summary_view as sv

MIN_SAMPLES = ins.MIN_SAMPLES
WEEKDAY_ORDER = ["月", "火", "水", "木", "金", "土", "日"]

# 配色体系（オレンジ基調）。役割で色を固定し、この範囲外の色は新規導入しない。
#   オレンジ = ブランド/主役・ポジティブ（検索流入・選択・目標・長尺・増加・伸びカーブ主系列）
#   ブルー   = 補助・中立データ（短尺・流入元・比較副系列）
#   レッド   = アラート専用（減少デルタ・警告のみ）
PRIMARY, PRIMARY_D, PRIMARY_SOFT = "#E9965B", "#C9742F", "#F2C4A0"   # オレンジ系
SECONDARY, SECONDARY_D = "#82B5F6", "#3D7BD9"                        # ブルー系
ALERT, INK, MUTED, BRD = "#D50403", "#1A1A1A", "#8A8A8A", "#EAEAEA"
FONT = '"Hiragino Sans","Noto Sans JP",sans-serif'
APPEAL_DOMAIN = ["逆説フック型", "感情セリフ型", "数字インパクト型",
                 "情緒物語性型", "親サポート軸型", "時代性脱常識型"]
# 訴求型6色（暖色先導＋寒色アクセント＋グレー。赤はアラート専用のため不使用）
APPEAL_RANGE = ["#E9965B", "#C9742F", "#F2C4A0", "#82B5F6", "#B8D4FA", "#8A8A8A"]
TYPE_DOMAIN, TYPE_RANGE = ["長尺", "ショート"], [PRIMARY, SECONDARY]
# 複数系列比較で使う色（暖色→寒色の順。アラート赤は使わない）
SERIES_CYCLE = [PRIMARY, SECONDARY, PRIMARY_D, SECONDARY_D, PRIMARY_SOFT, "#B8D4FA"]
RETENTION_HELP = "視聴維持率（YouTube公式 averageViewPercentage）＝平均して動画全体の何％が視聴されたか。"

st.set_page_config(page_title="ミカタ アナリティクス", page_icon="📊", layout="wide")

_GLOBAL_CSS = """
<style>
/* 立体感のある明るい背景（オレンジの淡いグロー） */
.stApp{background:
  radial-gradient(1100px 520px at 82% -8%, #FCEBDD 0%, rgba(252,235,221,0) 55%),
  radial-gradient(900px 460px at -5% 8%, #EAF1FB 0%, rgba(234,241,251,0) 50%),
  linear-gradient(180deg,#FBFBFC,#F4F5F7);}
header[data-testid="stHeader"]{height:0;background:transparent;pointer-events:none}
#MainMenu,footer{visibility:hidden}
.block-container{padding-top:2.4rem;max-width:2100px}
h1,h2,h3,h4,h5,p,span,label,div{color:#1A1A1A}

/* タブ: 広い間隔・大きいヒット領域・立体的な選択状態 */
.stTabs [data-baseweb="tab-list"]{gap:10px;background:#FFFFFF;padding:8px;border-radius:16px;
  border:1px solid #EAEAEA;flex-wrap:wrap;position:sticky;top:0;z-index:50;
  box-shadow:0 6px 20px rgba(20,20,40,.07)}
.stTabs [data-baseweb="tab"]{height:48px;padding:0 26px;border-radius:12px;color:#6B6B6B;
  font-weight:800;font-size:15px;white-space:nowrap;cursor:pointer;
  transition:transform .12s,background .15s,color .15s,box-shadow .15s}
.stTabs [data-baseweb="tab"]:hover{background:#FBEAD9;color:#C9742F;transform:translateY(-1px)}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#F2A66A,#E9965B);color:#fff;
  box-shadow:0 6px 16px rgba(233,150,91,.45)}
.stTabs [aria-selected="true"]:hover{color:#fff;transform:translateY(-1px)}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}

/* セクションを立体的な白カードで区切る（多層シャドウ＋ホバーで浮く） */
div[data-testid="stVerticalBlockBorderWrapper"]{background:#FFFFFF;border:1px solid #EFEFEF;
  border-radius:18px;padding:8px 20px 16px;
  box-shadow:0 1px 2px rgba(20,20,40,.04), 0 10px 30px rgba(20,20,40,.06);
  transition:transform .15s ease, box-shadow .15s ease;}
div[data-testid="stVerticalBlockBorderWrapper"]:hover{transform:translateY(-2px);
  box-shadow:0 2px 4px rgba(20,20,40,.05), 0 16px 40px rgba(20,20,40,.10);}
[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid #EAEAEA}
[data-testid="stMetricValue"]{font-weight:800}

/* スマホ最適化: 横並びカラムを縦積み・余白とタブを縮小 */
@media (max-width: 640px){
  .block-container{padding-left:.6rem;padding-right:.6rem;padding-top:3.4rem;max-width:100%}
  .stTabs [data-baseweb="tab-list"]{gap:6px;padding:6px}
  .stTabs [data-baseweb="tab"]{height:40px;padding:0 14px;font-size:13px}
  [data-testid="stHorizontalBlock"]{flex-direction:column;gap:.5rem}
  [data-testid="stColumn"],[data-testid="column"]{width:100%!important;flex:1 1 100%!important}
  div[data-testid="stVerticalBlockBorderWrapper"]{padding:6px 12px 12px}
}
</style>
"""


def _inject_css():
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def _check_password():
    """外部共有用の簡易パスワード認証。DASH_PASSWORD 未設定ならスルー（ローカル）。"""
    pw = getattr(config, "DASHBOARD_PASSWORD", "")
    if not pw or st.session_state.get("auth_ok"):
        return True
    st.title("📊 中学受験のミカタ アナリティクス")
    st.caption("閲覧にはパスワードが必要です。")
    entered = st.text_input("パスワード", type="password")
    if entered == pw:
        st.session_state["auth_ok"] = True
        st.rerun()
    elif entered:
        st.error("パスワードが違います。")
    st.stop()


def _style(chart):
    """全チャート共通のライトテーマ整形（不要なグリッド/枠線を除去）。"""
    return (chart
            .configure_view(strokeWidth=0)
            .configure_axis(grid=False, domainColor=BRD, tickColor=BRD,
                            labelColor=MUTED, titleColor=INK,
                            labelFont=FONT, titleFont=FONT,
                            labelFontSize=11, titleFontSize=12)
            .configure_legend(labelColor=INK, titleColor=INK,
                              labelFont=FONT, titleFont=FONT)
            .configure_text(font=FONT))


# ───────────────────────── ライブ取得（10分キャッシュ） ─────────────────────────

@st.cache_data(ttl=600)
def fetch_live(video_ids):
    """チャンネル統計と動画別 views/likes/comments をライブ取得（10分キャッシュ）。

    Data API クォータ見積り（上限 10,000 units/日）:
      1更新 = channels.list(1) + videos.list(≈152本/50=4) ≒ 5 units。
      タブを24h開きっぱなしでも 6回/h × 24h × 5 = 720 units/日 ≒ 上限の約7%。
      毎時 watch_new / 日次 main を足しても十分余裕。
    失敗時は (None, {}) を返し、呼び出し側でシート値にフォールバックする。
    """
    import fetch_analytics as fa
    if not config.CHANNEL_ID:
        st.warning("ライブ取得スキップ: CHANNEL_ID が空です。SecretsのCHANNEL_ID（[gcp_service_account]より上）を確認し、Save→再起動してください。")
        return None, {}
    try:
        return fa.get_channel_stats(), fa.get_video_stats(list(video_ids))
    except Exception as e:  # noqa: BLE001
        st.warning(f"ライブ取得に失敗（{type(e).__name__}: {e}）。シート値(日次)へフォールバックします。")
        return None, {}


@st.cache_data(ttl=21600)
def fetch_competitors():
    """自社＋競合チャンネルの公開指標をまとめて取得（6時間キャッシュ）。
    クォータ: channels.list(1) + 各ch playlistItems(1)+videos.list(1) ≒ 2×ch数。約25 units。"""
    import fetch_analytics as fa
    try:
        ids = [config.CHANNEL_ID] + list(config.COMPETITOR_CHANNEL_IDS)
        stats = fa.get_channels_stats(ids)
        rows = []
        for cid in ids:
            c = stats.get(cid)
            if not c:
                continue
            rec = fa.get_recent_channel_videos(c["uploads"], n=20)
            rows.append({
                "チャンネル": c["title"][:22],
                "自社": cid == config.CHANNEL_ID,
                "登録者": c["subs"], "総再生": c["views"], "本数": c["videos"],
                "直近中央値再生": int(rec.get("median_views", 0) or 0),
                "直近平均再生": int(rec.get("avg_views", 0) or 0),
                "高評価率%": round(rec.get("like_rate", 0) * 100, 2),
                "コメント率%": round(rec.get("comment_rate", 0) * 100, 3),
                "投稿/月": round(rec.get("uploads_per_month", 0), 1),
            })
        return pd.DataFrame(rows)
    except Exception as e:  # noqa: BLE001
        st.warning(f"競合データの取得に失敗: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_retention(video_id, start, end):
    """離脱曲線をライブ取得（10分キャッシュ）。失敗時は空リスト。"""
    import fetch_analytics as fa
    try:
        return fa.get_retention_curve(video_id, start, end)
    except Exception:  # noqa: BLE001
        return []


@st.cache_data(ttl=300)
def load_sheet(name):
    import gauth
    sh = gauth.open_sheet()  # ローカルはファイル / クラウドは st.secrets
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    return pd.DataFrame(ws.get_all_records())


def _type_badge(t):
    return "長尺" if t == "long" else ("ショート" if t == "short" else "—")


def _thumb(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def _fmt_int(x):
    try:
        return f"{int(round(float(x))):,}"
    except (TypeError, ValueError):
        return "—"


# ───────────────────────── メイン ─────────────────────────

def main():
    _inject_css()
    _check_password()
    master = ins.enrich_master(load_sheet("videos_master"))
    snapshots = load_sheet("snapshots")
    terms = load_sheet("search_terms")
    hourly = ins.clean_hourly(load_sheet("hourly_views"))
    channel_hist = load_sheet("channel_stats")
    video_metrics = load_sheet("video_metrics")

    if master.empty:
        st.title("中学受験のミカタ アナリティクス")
        st.info("videos_master がまだありません。データ収集後に表示されます。")
        return

    valid_ids = set(master["video_id"])
    snap = ins.clean_snapshots(snapshots)
    if not snap.empty:
        snap = snap[snap["video_id"].isin(valid_ids)]
    if not hourly.empty:
        hourly = hourly[hourly["video_id"].isin(valid_ids)]
    if not terms.empty:
        terms = terms[terms["video_id"].isin(valid_ids)]

    include_noise = _sidebar(master, snap)

    latest = ins.latest_snapshot(snap)
    # ノイズ除外（デフォルト）: 外部流入＋広告(有料)を総再生数から差し引いてオーガニック化
    if not include_noise and not latest.empty:
        latest = latest.copy()
        noise = latest.get("外部流入数", 0).fillna(0) if "外部流入数" in latest else 0
        ads = latest.get("広告流入数", 0).fillna(0) if "広告流入数" in latest else 0
        latest["総再生数"] = (latest["総再生数"] - noise - ads).clip(lower=0)
    latest_ret = ins.with_retention(latest, master) if not latest.empty else pd.DataFrame()
    # 本物の視聴維持率(averageViewPercentage)・登録獲得・登録転換率を統合
    if not latest_ret.empty:
        latest_ret = ins.attach_metrics(latest_ret, video_metrics)

    # 検索流入(累計): KPI主役。snapshots 最新の検索流入数合計（外部の影響を受けない）
    search_inflow_total = int(latest["検索流入数"].fillna(0).sum()) if not latest.empty else 0

    tabs = st.tabs(
        ["サマリー", "カタログ", "ディープダイブ", "伸び比較", "年度比較", "競合比較", "分析", "検索キーワード"]
    )
    with tabs[0]:
        _tab_summary(master, channel_hist, search_inflow_total)
    with tabs[1]:
        _tab_catalog(master, latest_ret, include_noise)
    with tabs[2]:
        _tab_deepdive(master, snap, latest_ret, hourly, terms)
    with tabs[3]:
        _tab_growth(master, snap, hourly, latest_ret)
    with tabs[4]:
        _tab_year(master)
    with tabs[5]:
        _tab_competitors()
    with tabs[6]:
        _tab_analysis(master, latest_ret, include_noise)
    with tabs[7]:
        _tab_keywords(terms, master)


def _sidebar(master, snap):
    """サイドバー: データ状況 + ノイズ流入トグル。include_noise を返す。"""
    with st.sidebar:
        st.markdown("### データ状況")
        st.metric("公開動画数", f"{len(master):,} 本")
        if not snap.empty:
            st.caption(f"日次データ最終取得: {snap['取得日'].max()}")
        st.divider()
        include_noise = st.toggle(
            "ノイズ流入を含める", value=False,
            help="外部流入（他サイト/共有リンク）と広告（有料）を集計に含める。"
                 "OFF（既定）ではこれらを除外したオーガニック値を標準表示します。",
        )
        st.caption("既定では**外部流入と広告（有料）を除外**＝オーガニックで集計しています。")
        st.divider()
        if st.button("データを再取得（キャッシュ更新）", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.caption(
            "・シート値は5分キャッシュ。\n"
            "・サマリーのKPIは Data API をライブ取得（10分キャッシュ・自動更新）。\n"
            "・流入元/維持率は Analytics（約2日遅れ・公開60日以内が対象）。"
        )
    return include_noise


# ───────────────────────── サマリー ─────────────────────────

@st.fragment(run_every=600)
def _tab_summary(master, channel_hist, search_inflow_total):
    """ライブAPIで10分ごとに自動更新するサマリー。

    自動更新(run_every)はこのセッション（タブを開いている間）だけ server 側で動く。
    タブを閉じる/離脱するとセッション終了で更新は止まる（クォータも消費しない）想定。
    ブラウザのバックグラウンドでも websocket 接続が生きていれば更新は継続する。
    """
    ids = list(master["video_id"])
    chan, stats = fetch_live(tuple(ids))
    is_live = chan is not None and bool(stats)

    if not stats:  # フォールバック: snapshots 最新の総再生数（like/comment は0）
        snap = ins.latest_snapshot(ins.clean_snapshots(load_sheet("snapshots")))
        if not snap.empty:
            stats = {r["video_id"]: {"views": int(r["総再生数"] or 0), "likes": 0, "comments": 0}
                     for _, r in snap.iterrows() if r["video_id"] in set(ids)}
    if chan is None:
        h = channel_hist
        if not h.empty:
            last = h.iloc[-1]
            chan = {"subscribers": int(last.get("登録者数", 0) or 0),
                    "total_views": int(last.get("総再生数", 0) or 0),
                    "video_count": int(last.get("総本数", len(master)) or len(master))}
        else:
            chan = {"subscribers": 0, "total_views": 0, "video_count": len(master)}

    payload = ins.build_summary_payload(
        master, stats, chan, channel_hist, config.SUBSCRIBER_GOAL,
        search_inflow_total=search_inflow_total, is_live=is_live)
    # height="content": 内容の高さに自動フィット（PC/スマホ両対応・内部スクロール回避）
    st.iframe(sv.render_summary(payload), height="content")


# ───────────────────────── カタログ ─────────────────────────

def _tab_catalog(master, latest_ret, include_noise):
    with st.container(border=True):
        st.subheader("動画カタログ")
        suffix = "（外部・広告を含む）" if include_noise else "（外部・広告を除外）"
        st.caption(f"サムネイル付き一覧。シリーズ・話数で絞り込み、列ヘッダで並べ替え可能。実績は最新日次{suffix}。")

        f = st.columns(2)
        sel_series = f[0].selectbox("シリーズ", ["すべて"] + sorted(master["シリーズ"].unique()))
        sel_type = f[1].selectbox("種別", ["すべて", "長尺", "ショート"])

        m = master.copy()
        if sel_series != "すべて":
            m = m[m["シリーズ"] == sel_series]
        if sel_type != "すべて":
            m = m[m["video_type"] == ("long" if sel_type == "長尺" else "short")]

        cols_pull = ["video_id", "総再生数", "視聴維持率", "1日あたり再生"]
        if "登録獲得" in latest_ret.columns:
            cols_pull.append("登録獲得")
        if not latest_ret.empty:
            m = m.merge(latest_ret[cols_pull], on="video_id", how="left")
        else:
            for c in ["総再生数", "視聴維持率", "1日あたり再生", "登録獲得"]:
                m[c] = pd.NA
        if "登録獲得" not in m.columns:
            m["登録獲得"] = pd.NA

        m["サムネ"] = m["video_id"].map(_thumb)
        m["種別"] = m["video_type"].map(_type_badge)
        m["視聴維持率%"] = (pd.to_numeric(m["視聴維持率"], errors="coerce") * 100).round(1)
        m = m.sort_values("公開日時", ascending=False)

        disp = (m[["サムネ", "種別", "シリーズ", "話数", "短縮タイトル", "公開日時",
                   "動画長(分)", "総再生数", "1日あたり再生", "視聴維持率%", "登録獲得"]]
                .rename(columns={"短縮タイトル": "タイトル"}))
        st.caption(f"該当 {len(m)} 本")
        st.dataframe(
            disp, width="stretch", hide_index=True, height=560,
            column_config={
                "サムネ": st.column_config.ImageColumn("サムネ", width="small"),
                "タイトル": st.column_config.TextColumn("タイトル", width="large"),
                "総再生数": st.column_config.NumberColumn(format="%d"),
                "1日あたり再生": st.column_config.NumberColumn(format="%.0f"),
                "視聴維持率%": st.column_config.NumberColumn(format="%.1f%%", help=RETENTION_HELP),
                "登録獲得": st.column_config.NumberColumn(format="%d", help="この動画から得た登録者数"),
                "動画長(分)": st.column_config.NumberColumn(format="%.1f"),
            },
        )


# ───────────────────────── ディープダイブ（横並び比較） ─────────────────────────

def _dd_short(master, vid):
    r = master[master["video_id"] == vid].iloc[0]
    ep = "" if r["話数"] == "—" else f"{r['話数']}｜"
    return f"{ep}{r['短縮タイトル']}"


def _tab_deepdive(master, snap, latest_ret, hourly, terms):
    st.subheader("動画ディープダイブ（横並び比較）")

    with st.container(border=True):
        f = st.columns([1, 1])
        sel_series = f[0].selectbox("シリーズで絞り込み", ["すべて"] + sorted(master["シリーズ"].unique()),
                                    key="dd_series")
        only_tracked = f[1].checkbox("実績データあり優先", value=True,
                                     help="日次の流入元/維持率が取れている動画を上に")
        m = master.copy()
        if sel_series != "すべて":
            m = m[m["シリーズ"] == sel_series]
        tracked_ids = set(latest_ret["video_id"]) if not latest_ret.empty else set()
        m["_has"] = m["video_id"].isin(tracked_ids)
        m = (m.sort_values(["_has", "公開日時"], ascending=[False, False]) if only_tracked
             else m.sort_values("公開日時", ascending=False))
        ids = list(m["video_id"])
        if not ids:
            st.info("該当動画なし。")
            return
        id2label = dict(zip(m["video_id"], m.apply(
            lambda r: f"{'● ' if r['_has'] else '○ '}{r['表示名']}", axis=1)))
        picked = st.multiselect("比較する動画（最大3本まで横並び表示）", ids, default=ids[:2],
                                format_func=lambda v: id2label.get(v, v),
                                max_selections=3, key="dd_pick")
    if not picked:
        st.info("比較する動画を1〜3本選んでください。")
        return

    # ① ヘッダー（サムネ＋主要指標）を横並び
    cols = st.columns(len(picked))
    for col, vid in zip(cols, picked):
        with col:
            with st.container(border=True):
                _dd_header(master, latest_ret, vid)

    # ② 指標くらべ（指標=行 / 動画=列の転置テーブル）
    with st.container(border=True):
        st.markdown("#### 指標くらべ")
        st.dataframe(_dd_compare_table(master, latest_ret, picked), width="stretch")
        st.caption("視聴維持率＝" + RETENTION_HELP)

    # ③ 伸びカーブ（横並び）
    with st.container(border=True):
        st.markdown("#### 伸びカーブ（横並び）")
        cols = st.columns(len(picked))
        for col, vid in zip(cols, picked):
            with col:
                st.caption(_dd_short(master, vid))
                _deepdive_growth(vid, snap, hourly, compact=True)

    # ④ 離脱曲線（横並び・ライブ取得）
    with st.container(border=True):
        st.markdown("#### 離脱曲線（視聴者維持・横並び）")
        st.caption("横軸＝動画内の位置(0→終),縦軸＝その地点を見ている割合。"
                   "急降下する箇所が離脱ポイント。100%超は再視聴(ループ)。")
        cols = st.columns(len(picked))
        for col, vid in zip(cols, picked):
            with col:
                st.caption(_dd_short(master, vid))
                _deepdive_retention(vid, master)

    # ⑤ 流入元（横並び）
    with st.container(border=True):
        st.markdown("#### 流入元の内訳（横並び・最新日次）")
        cols = st.columns(len(picked))
        for col, vid in zip(cols, picked):
            with col:
                st.caption(_dd_short(master, vid))
                _deepdive_traffic(vid, snap, compact=True)

    # ⑥ 検索キーワード（横並び）
    with st.container(border=True):
        st.markdown("#### 検索流入キーワード（横並び）")
        cols = st.columns(len(picked))
        for col, vid in zip(cols, picked):
            with col:
                st.caption(_dd_short(master, vid))
                _deepdive_keywords(vid, terms, compact=True)

    # ⑦ 説明文・タグ
    with st.container(border=True):
        st.markdown("#### 説明文・タグ")
        for vid in picked:
            row = master[master["video_id"] == vid].iloc[0]
            with st.expander(_dd_short(master, vid)):
                if row.get("タグ"):
                    st.markdown("**タグ:** " + row["タグ"])
                st.text(ins.norm(row.get("説明文", "")) or "（説明文なし）")


def _dd_header(master, latest_ret, vid):
    r = master[master["video_id"] == vid].iloc[0]
    st.image(_thumb(vid))
    st.markdown(f"**{_dd_short(master, vid)}**")
    chips = [_type_badge(r["video_type"])]
    if r["シリーズ"] != "—":
        chips.append(r["シリーズ"])
    chips.append(str(r["公開日時"])[:10])
    st.caption(" ・ ".join(chips))
    st.markdown(f"[YouTubeで開く](https://youtu.be/{vid})")
    vl = latest_ret[latest_ret["video_id"] == vid] if not latest_ret.empty else pd.DataFrame()
    if vl.empty:
        st.caption("実績データなし（公開60日以内のみ日次追跡）")
        return
    x = vl.iloc[0]
    a, b = st.columns(2)
    a.metric("総再生数", _fmt_int(x["総再生数"]))
    b.metric("1日あたり", _fmt_int(x["1日あたり再生"]))
    ret = x["視聴維持率"]
    a.metric("視聴維持率", f"{ret*100:.1f}%" if pd.notna(ret) else "—", help=RETENTION_HELP)
    b.metric("経過日数", f"{int(x['経過日数'])}日")
    sg = x.get("登録獲得")
    cv = x.get("登録転換率")
    a.metric("登録獲得", _fmt_int(sg) + "人" if pd.notna(sg) else "—",
             help="この動画から得た登録者数（subscribersGained）")
    b.metric("登録転換率", f"{cv*100:.2f}%" if pd.notna(cv) else "—",
             help="登録獲得 ÷ 総再生数。登録への効きやすさ。")


def _dd_compare_table(master, latest_ret, picked):
    # 転置テーブルは Arrow 直列化のため全セルを文字列に整形しておく
    rows = []
    for vid in picked:
        r = master[master["video_id"] == vid].iloc[0]
        vl = latest_ret[latest_ret["video_id"] == vid] if not latest_ret.empty else pd.DataFrame()
        dur = r["動画長(分)"]
        d = {"動画": _dd_short(master, vid),
             "種別": _type_badge(r["video_type"]),
             "公開日": str(r["公開日時"])[:10],
             "公開曜日/時刻": f"{r['公開曜日']} {r['公開時刻']}",
             "動画長(分)": f"{dur:.1f}" if pd.notna(dur) else "—",
             "総再生数": "—", "1日あたり再生": "—", "視聴維持率": "—",
             "平均視聴時間": "—", "登録獲得": "—", "登録転換率": "—", "経過日数": "—"}
        if not vl.empty:
            x = vl.iloc[0]
            d["総再生数"] = f"{int(x['総再生数']):,}"
            d["1日あたり再生"] = f"{int(round(x['1日あたり再生'])):,}"
            d["視聴維持率"] = f"{x['視聴維持率']*100:.1f}%" if pd.notna(x["視聴維持率"]) else "—"
            d["平均視聴時間"] = f"{int(x['平均視聴時間(秒)'])}秒" if pd.notna(x["平均視聴時間(秒)"]) else "—"
            sg, cv = x.get("登録獲得"), x.get("登録転換率")
            d["登録獲得"] = f"{int(sg):,}人" if pd.notna(sg) else "—"
            d["登録転換率"] = f"{cv*100:.2f}%" if pd.notna(cv) else "—"
            d["経過日数"] = f"{int(x['経過日数'])}日"
        rows.append(d)
    # 指標=行 / 動画=列 に転置して横並び比較しやすく（全て文字列）
    return pd.DataFrame(rows).set_index("動画").T


def _deepdive_growth(vid, snap, hourly, compact=False):
    if not compact:
        st.markdown("**伸びカーブ**")
    h = hourly[hourly["video_id"] == vid] if not hourly.empty else pd.DataFrame()
    height = 220 if compact else 300
    if not h.empty and h["経過時間(h)"].notna().sum() >= 2:
        chart = (alt.Chart(h).mark_line(point=True, color=PRIMARY_D)
                 .encode(x=alt.X("経過時間(h):Q", title="経過(時間)"),
                         y=alt.Y("viewCount:Q", title="総再生数"),
                         tooltip=["経過時間(h)", "viewCount"]).properties(height=height))
        st.altair_chart(_style(chart), width="stretch")
        st.caption("毎時の総再生数（公開直後の立ち上がり）")
        return
    s = snap[snap["video_id"] == vid].sort_values("経過日数") if not snap.empty else pd.DataFrame()
    if not s.empty:
        chart = (alt.Chart(s).mark_line(point=True, color=PRIMARY_D)
                 .encode(x=alt.X("経過日数:Q", title="経過(日)"),
                         y=alt.Y("総再生数:Q", title="総再生数"),
                         tooltip=["取得日", "経過日数", "総再生数"]).properties(height=height))
        st.altair_chart(_style(chart), width="stretch")
        st.caption("日次の総再生数（点1つは追跡開始直後）")
    else:
        st.info("伸びカーブ用データなし")


def _deepdive_retention(vid, master):
    row = master[master["video_id"] == vid]
    if row.empty:
        st.info("動画情報なし")
        return
    start = str(row.iloc[0]["公開日時"])[:10]
    end = (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    curve = fetch_retention(vid, start, end)
    if not curve:
        st.info("離脱曲線データなし（公開60日以内・一定再生数が必要）")
        return
    df = pd.DataFrame(curve)
    df["位置%"] = df["pos"] * 100
    df["維持率"] = df["watch"]
    chart = (alt.Chart(df).mark_area(
        line={"color": PRIMARY_D}, color=alt.Gradient(
            gradient="linear",
            stops=[alt.GradientStop(color="#FCEEE2", offset=0),
                   alt.GradientStop(color=PRIMARY, offset=1)],
            x1=1, x2=1, y1=1, y2=0))
        .encode(x=alt.X("位置%:Q", title="動画内の位置(%)"),
                y=alt.Y("維持率:Q", title="維持率", axis=alt.Axis(format="%")),
                tooltip=[alt.Tooltip("位置%:Q", format=".0f"),
                         alt.Tooltip("維持率:Q", format=".0%")])
        .properties(height=220))
    st.altair_chart(_style(chart), width="stretch")
    avg = df["維持率"].mean()
    st.caption(f"平均維持 {avg*100:.0f}%。序盤(最初の10%)維持 {df[df['pos']<=0.1]['維持率'].mean()*100:.0f}%")


def _deepdive_traffic(vid, snap, compact=False):
    if not compact:
        st.markdown("**流入元の内訳（最新日次）**")
    s = snap[snap["video_id"] == vid].sort_values("経過日数") if not snap.empty else pd.DataFrame()
    if s.empty:
        st.info("流入元データなし")
        return
    bd = ins.traffic_breakdown(s.iloc[-1])
    if bd.empty:
        st.info("流入はまだ記録なし")
        return
    height = 200 if compact else 260
    chart = (alt.Chart(bd).mark_bar(color=SECONDARY)  # 流入元=中立データはブルー
             .encode(x=alt.X("流入数:Q"), y=alt.Y("流入元:N", sort="-x"),
                     tooltip=["流入元", "流入数"]).properties(height=height))
    st.altair_chart(_style(chart), width="stretch")
    total = int(bd["流入数"].sum())
    top = bd.sort_values("流入数", ascending=False).iloc[0]
    st.caption(f"合計 {total:,}・最多「{top['流入元']}」（{top['流入数']/total*100:.0f}%）")


def _deepdive_keywords(vid, terms, compact=False):
    if not compact:
        st.markdown("**この動画の検索流入キーワード**")
    if terms.empty:
        st.info("検索KWデータなし")
        return
    t = terms[terms["video_id"] == vid].copy()
    if t.empty:
        st.info("検索流入の記録なし")
        return
    t["流入数"] = pd.to_numeric(t["流入数"], errors="coerce").fillna(0)
    topk = 8 if compact else 15
    rk = (t.groupby("検索キーワード")["流入数"].sum()
          .sort_values(ascending=False).head(topk).reset_index())
    height = 200 if compact else 280
    chart = (alt.Chart(rk).mark_bar(color=PRIMARY)  # 検索＝オレンジ
             .encode(x=alt.X("流入数:Q"), y=alt.Y("検索キーワード:N", sort="-x"),
                     tooltip=["検索キーワード", "流入数"]).properties(height=height))
    st.altair_chart(_style(chart), width="stretch")


# ───────────────────────── 伸び比較 ─────────────────────────

def _tab_growth(master, snap, hourly, latest_ret):
    st.subheader("伸び比較")
    _growth_ranking(master, latest_ret)
    _growth_compare(master, snap, hourly, latest_ret)


def _growth_ranking(master, latest_ret):
    """伸びランキング（1日あたり再生＝伸びの速さ／総再生数）。"""
    with st.container(border=True):
        st.markdown("#### 伸びランキング")
        if latest_ret.empty:
            st.info("ランキングに使える日次実績データがまだありません。")
            return
        metric = st.radio("指標", ["1日あたり再生（伸びの速さ）", "総再生数"],
                          horizontal=True, key="grow_rank_metric")
        col = "1日あたり再生" if metric.startswith("1日") else "総再生数"
        # latest_ret には既に video_type があるため重複させない
        r = latest_ret.merge(master[["video_id", "短縮タイトル", "話数"]],
                             on="video_id", how="left")
        r["サムネ"] = r["video_id"].map(_thumb)
        r["種別"] = r["video_type"].map(_type_badge)
        r = r.sort_values(col, ascending=False).head(15).reset_index(drop=True)
        r.insert(0, "順位", r.index + 1)
        show = r[["順位", "サムネ", "短縮タイトル", "話数", "種別",
                  "1日あたり再生", "総再生数"]].rename(columns={"短縮タイトル": "タイトル"})
        st.dataframe(
            show, width="stretch", hide_index=True,
            column_config={
                "順位": st.column_config.NumberColumn(width="small"),
                "サムネ": st.column_config.ImageColumn("サムネ", width="small"),
                "タイトル": st.column_config.TextColumn("タイトル", width="large"),
                "1日あたり再生": st.column_config.NumberColumn(format="%.0f"),
                "総再生数": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.caption("「1日あたり再生」= 総再生数 ÷ 経過日数。日次データ（外部流入の扱いはサイドバー設定に従う）。")


def _growth_compare(master, snap, hourly, latest_ret):
    """伸びカーブ比較（精査版）。端点ラベル・要約表・相対比較で読み取りやすく。"""
    with st.container(border=True):
        st.markdown("#### 伸びカーブ比較")
        st.caption("選んだ動画の「公開からの経過 × 累計再生」を重ね描き。"
                   "日次は数点のみのため折れ線は短め。『相対比較』で開始点を0に揃えると"
                   "伸びの傾き（速さ）を比べやすくなります。")

        c = st.columns([1.4, 1.2, 1])
        mode = c[0].radio("見方", ["日次：公開からの日数で比較", "毎時：公開直後の立ち上がりで比較"],
                          key="grow_mode")
        use_hourly = mode.startswith("毎時")
        data = hourly if use_hourly else snap
        xcol = "経過時間(h)" if use_hourly else "経過日数"
        xtitle = "公開からの経過（時間）" if use_hourly else "公開からの経過（日）"
        ycol = "viewCount" if use_hourly else "総再生数"
        if data is None or data.empty:
            st.info("この見方のデータがまだありません。")
            return

        avail = set(data["video_id"])
        mm = master[master["video_id"].isin(avail)].copy()
        if mm.empty:
            st.info("該当データのある動画がありません。")
            return
        id2label = dict(zip(mm["video_id"], mm["表示名"]))
        id2short = {v: _dd_short(master, v) for v in mm["video_id"]}

        sel_series = c[1].selectbox("シリーズで絞り込み",
                                    ["すべて"] + sorted(mm["シリーズ"].unique()), key="grow_series")
        relative = c[2].checkbox("相対比較（開始を0に）", value=True, key="grow_rel",
                                 help="各動画の追跡開始を0に揃え、伸びの傾きを比較しやすくします。")

        cand = mm if sel_series == "すべて" else mm[mm["シリーズ"] == sel_series]
        cand_ids = list(cand["video_id"])
        if not cand_ids:
            st.info("条件に合う動画がありません。")
            return

        c2 = st.columns([1, 3])
        auto = c2[0].checkbox("上位N本を自動選択", value=True, key="grow_auto")
        if auto:
            topn = c2[1].slider("本数（視聴数の多い順）", 2, 6, 3, key="grow_topn")
            rank = (latest_ret[latest_ret["video_id"].isin(cand_ids)]
                    .sort_values("総再生数", ascending=False)["video_id"].tolist())
            rank += [v for v in cand.sort_values("公開日時", ascending=False)["video_id"]
                     if v not in rank]
            picked = rank[:topn]
            st.caption(f"視聴数の多い順に {len(picked)} 本を自動選択中（手動選択はチェックを外す）。")
        else:
            picked = c2[1].multiselect(
                "比較する動画（推奨 2〜4本）", cand_ids,
                default=cand.sort_values("公開日時", ascending=False)["video_id"].head(3).tolist(),
                format_func=lambda v: id2label.get(v, v), key="grow_pick")
        if not picked:
            st.info("動画を選択してください。")
            return

        sub = data[data["video_id"].isin(picked)].copy()
        sub[xcol] = pd.to_numeric(sub[xcol], errors="coerce")
        sub[ycol] = pd.to_numeric(sub[ycol], errors="coerce")
        sub = sub.dropna(subset=[xcol, ycol])
        if sub.empty:
            st.info("描画できるデータ点がありません。")
            return
        sub["動画"] = sub["video_id"].map(id2short)

        # 要約表（生データから。相対化の影響を受けない）
        summ = (sub.groupby("動画")
                .agg(データ点数=(ycol, "count"), 最新総再生=(ycol, "max")).reset_index())
        vel = latest_ret[["video_id", "1日あたり再生"]].copy()
        vel["動画"] = vel["video_id"].map(id2short)
        summ = summ.merge(vel[["動画", "1日あたり再生"]], on="動画", how="left")
        summ["1日あたり再生"] = summ["1日あたり再生"].round(0).astype("Int64")

        ycol_title = "累計再生数"
        if relative:
            sub["_min"] = sub.groupby("video_id")[ycol].transform("min")
            sub[ycol] = sub[ycol] - sub["_min"]
            ycol_title = "累計再生数（開始0に揃え）"

        order = [id2short[v] for v in picked if id2short.get(v) in set(sub["動画"])]
        cscale = alt.Scale(domain=order, range=SERIES_CYCLE)
        base = alt.Chart(sub)
        line = base.mark_line(point=alt.OverlayMarkDef(size=70, filled=True), strokeWidth=3).encode(
            x=alt.X(f"{xcol}:Q", title=xtitle),
            y=alt.Y(f"{ycol}:Q", title=ycol_title),
            color=alt.Color("動画:N", scale=cscale, legend=alt.Legend(orient="bottom", columns=1)),
            tooltip=["動画", alt.Tooltip(f"{xcol}:Q", title=xtitle),
                     alt.Tooltip(f"{ycol}:Q", title=ycol_title, format=",")])
        # 端点ラベル（各線の終点に動画名）
        last = sub.sort_values(xcol).groupby("動画", as_index=False).tail(1).copy()
        last["ラベル"] = last["動画"].str.slice(0, 16)
        labels = (alt.Chart(last).mark_text(align="left", dx=8, fontWeight="bold", fontSize=11)
                  .encode(x=f"{xcol}:Q", y=f"{ycol}:Q", text="ラベル:N",
                          color=alt.Color("動画:N", scale=cscale, legend=None)))
        chart = (line + labels).properties(height=440)
        st.altair_chart(_style(chart), width="stretch")

        st.dataframe(
            summ.sort_values("最新総再生", ascending=False),
            width="stretch", hide_index=True,
            column_config={
                "最新総再生": st.column_config.NumberColumn(format="%d"),
                "1日あたり再生": st.column_config.NumberColumn(format="%d"),
                "データ点数": st.column_config.NumberColumn(
                    help="蓄積された観測点の数。多いほどカーブが滑らかになります。"),
            },
        )


# ───────────────────────── 年度・シリーズ比較 ─────────────────────────

def _year_compare_table(df, a, b):
    rows = []
    for s in (a, b):
        d = df[df["シリーズ"] == s]
        v = d["views"]
        rows.append({
            "シリーズ": s,
            "本数": f"{len(d)}",
            "合計再生": f"{int(v.sum()):,}",
            "中央値再生": f"{int(v.median()):,}" if len(d) else "—",
            "平均再生": f"{int(v.mean()):,}" if len(d) else "—",
            "最高再生": f"{int(v.max()):,}" if len(d) else "—",
            "平均高評価率": f"{d['高評価率'].mean()*100:.2f}%" if len(d) else "—",
            "平均コメント率": f"{d['コメント率'].mean()*100:.2f}%" if len(d) else "—",
        })
    return pd.DataFrame(rows).set_index("シリーズ").T


def _tab_year(master):
    st.subheader("年度・シリーズ比較")
    st.caption("YouTube公式のライブ統計（再生/高評価/コメント）でシリーズを年度横断比較。"
               "高評価率・コメント率は年度をまたいで比べられる公開エンゲージ指標です。")
    ids = list(master["video_id"])
    chan, stats = fetch_live(tuple(ids))
    if not stats:
        st.info("ライブ統計を取得できませんでした（Secrets / CHANNEL_ID を確認）。")
        return
    df = ins.video_stats_df(master, stats)
    if df.empty:
        st.info("対象データがありません。")
        return

    # ① シリーズ別サマリー（年度順）
    with st.container(border=True):
        st.markdown("#### シリーズ別サマリー（年度順）")
        summ = ins.series_summary(df)
        st.dataframe(
            summ[["年度", "シリーズ", "本数", "中央値再生", "合計再生", "平均高評価率%", "平均コメント率%"]],
            width="stretch", hide_index=True,
            column_config={
                "中央値再生": st.column_config.NumberColumn(format="%d"),
                "合計再生": st.column_config.NumberColumn(format="%d"),
                "平均高評価率%": st.column_config.NumberColumn(format="%.2f%%"),
                "平均コメント率%": st.column_config.NumberColumn(format="%.2f%%"),
            })

    # ② シリーズ年度 直接対比
    with st.container(border=True):
        st.markdown("#### シリーズ年度 直接対比")
        opts = [s for s in summ["シリーズ"].tolist() if s and s != "—"]
        if len(opts) < 2:
            st.info("比較できるシリーズが不足しています。")
            return
        defA = next((s for s in opts if "2026" in s), opts[0])
        defB = next((s for s in opts if "2025" in s and s != defA), None) \
            or next((s for s in opts if s != defA), opts[0])
        c = st.columns(2)
        selA = c[0].selectbox("シリーズA", opts, index=opts.index(defA), key="yr_a")
        selB = c[1].selectbox("シリーズB", opts, index=opts.index(defB), key="yr_b")
        if selA == selB:
            st.info("異なる2つのシリーズを選んでください。")
            return

        st.dataframe(_year_compare_table(df, selA, selB), width="stretch")

        sub = df[df["シリーズ"].isin([selA, selB])].copy()
        sub["公開順"] = (sub.sort_values("公開日時").groupby("シリーズ").cumcount() + 1)
        chart = (alt.Chart(sub).mark_line(point=alt.OverlayMarkDef(size=70, filled=True),
                                          strokeWidth=3)
                 .encode(x=alt.X("公開順:Q", title="シリーズ内の公開順（1本目→）"),
                         y=alt.Y("views:Q", title="再生数"),
                         color=alt.Color("シリーズ:N",
                                         scale=alt.Scale(domain=[selA, selB],
                                                         range=[PRIMARY, SECONDARY]),
                                         legend=alt.Legend(orient="bottom")),
                         tooltip=["シリーズ", "公開順", "短縮タイトル", "views", "likes", "comments"])
                 .properties(height=380))
        st.altair_chart(_style(chart), width="stretch")
        st.caption("各年度シリーズの『N本目』の再生を重ね描き。年度ごとの立ち上がり・失速の違いが見えます。")


# ───────────────────────── 競合比較 ─────────────────────────

def _tab_competitors():
    st.subheader("競合比較（公開指標）")
    st.caption("中学受験系チャンネルの公開指標で比較。直近20本から中央値/平均再生・エンゲージ率・投稿頻度を算出。"
               "※競合の視聴維持率・流入元・CTR・登録転換は非公開のため取得不可（自社のみ）。対象は config で編集可。")
    df = fetch_competitors()
    if df.empty:
        st.info("競合データを取得できませんでした（CHANNEL_ID / クォータを確認）。")
        return

    with st.container(border=True):
        st.markdown("#### 一覧（登録者順）")
        show = df.sort_values("登録者", ascending=False).copy()
        show["区分"] = show["自社"].map(lambda x: "★自社" if x else "競合")
        st.dataframe(
            show[["区分", "チャンネル", "登録者", "総再生", "本数",
                  "直近中央値再生", "高評価率%", "コメント率%", "投稿/月"]],
            width="stretch", hide_index=True,
            column_config={
                "登録者": st.column_config.NumberColumn(format="%d"),
                "総再生": st.column_config.NumberColumn(format="%d"),
                "本数": st.column_config.NumberColumn(format="%d"),
                "直近中央値再生": st.column_config.NumberColumn(format="%d"),
                "高評価率%": st.column_config.NumberColumn(format="%.2f%%"),
                "コメント率%": st.column_config.NumberColumn(format="%.3f%%"),
                "投稿/月": st.column_config.NumberColumn(format="%.1f"),
            })

    cc = st.columns(2)
    with cc[0]:
        with st.container(border=True):
            st.markdown("#### ポジショニング（登録者 × 直近中央値再生）")
            d = df.copy()
            d["区分"] = d["自社"].map(lambda x: "自社" if x else "競合")
            pts = (alt.Chart(d).mark_circle(size=150, opacity=0.8)
                   .encode(x=alt.X("登録者:Q", scale=alt.Scale(type="log"), title="登録者数（対数）"),
                           y=alt.Y("直近中央値再生:Q", title="直近中央値 再生"),
                           color=alt.Color("区分:N",
                                           scale=alt.Scale(domain=["自社", "競合"], range=[PRIMARY, SECONDARY])),
                           tooltip=["チャンネル", "登録者", "直近中央値再生", "高評価率%", "投稿/月"]))
            label = (alt.Chart(d[d["自社"]]).mark_text(dy=-14, fontWeight="bold", color=PRIMARY_D)
                     .encode(x=alt.X("登録者:Q", scale=alt.Scale(type="log")),
                             y="直近中央値再生:Q", text="チャンネル"))
            st.altair_chart(_style(pts + label), width="stretch")
            st.caption("自社=オレンジ。左下から右上へ伸ばすのが成長。")
    with cc[1]:
        with st.container(border=True):
            st.markdown("#### エンゲージ率（高評価率）")
            d = df.sort_values("高評価率%", ascending=False)
            chart = (alt.Chart(d).mark_bar()
                     .encode(x=alt.X("高評価率%:Q"), y=alt.Y("チャンネル:N", sort="-x"),
                             color=alt.condition("datum.自社", alt.value(PRIMARY), alt.value(SECONDARY)),
                             tooltip=["チャンネル", "高評価率%", "コメント率%"]))
            st.altair_chart(_style(chart), width="stretch")
            st.caption("登録者が少なくてもエンゲージ率では上回れる余地。自社=オレンジ。")


# ───────────────────────── 分析 ─────────────────────────

def _tab_analysis(master, latest_ret, include_noise):
    if latest_ret.empty:
        st.info("分析に使える実績データがまだありません。")
        return
    st.caption(("外部・広告を含む集計" if include_noise else "外部・広告を除外した集計（既定）")
               + "。代表値は中央値、各比較に n を併記し n<5 は参考値。")
    if len(latest_ret) < MIN_SAMPLES:
        st.warning(f"実績データが {len(latest_ret)} 本と少ないため、以下は傾向の示唆としてご覧ください。")

    # 登録転換ランキング（登録に効く動画）
    with st.container(border=True):
        st.markdown("#### 登録転換ランキング（登録に効く動画）")
        rk = latest_ret.merge(master[["video_id", "短縮タイトル", "話数"]], on="video_id", how="left")
        rk = rk.dropna(subset=["登録獲得"]).copy() if "登録獲得" in rk.columns else pd.DataFrame()
        if rk.empty:
            st.info("登録獲得データがまだありません（video_metrics 収集後に表示）。")
        else:
            rk["サムネ"] = rk["video_id"].map(_thumb)
            rk["登録転換率%"] = (pd.to_numeric(rk["登録転換率"], errors="coerce") * 100).round(2)
            rk = rk.sort_values("登録獲得", ascending=False).head(15).reset_index(drop=True)
            rk.insert(0, "順位", rk.index + 1)
            show = rk[["順位", "サムネ", "短縮タイトル", "話数", "登録獲得", "総再生数",
                       "登録転換率%"]].rename(columns={"短縮タイトル": "タイトル"})
            st.dataframe(
                show, width="stretch", hide_index=True,
                column_config={
                    "順位": st.column_config.NumberColumn(width="small"),
                    "サムネ": st.column_config.ImageColumn("サムネ", width="small"),
                    "タイトル": st.column_config.TextColumn("タイトル", width="large"),
                    "登録獲得": st.column_config.NumberColumn(format="%d"),
                    "総再生数": st.column_config.NumberColumn(format="%d"),
                    "登録転換率%": st.column_config.NumberColumn(format="%.2f%%"),
                })
            st.caption("登録獲得＝subscribersGained。登録転換率＝登録獲得÷総再生数。"
                       "目標（登録1万人）への寄与が大きい＝量産候補。")

    # サムネ/タイトル診断（発見力 × 視聴維持率）
    with st.container(border=True):
        st.markdown("#### サムネ/タイトル診断（発見力 × 視聴維持率）")
        st.caption("発見力＝ブラウズ＋関連の流入数（フィードで選ばれた量の代理指標）。"
                   "右上=勝ち／右下=釣れるが中身改善／左上=良作だが未発見(サムネ余地)／左下=要見直し。"
                   "※実CTRはAPI非提供のためYouTube Studio参照。")
        q = latest_ret.copy()
        q["発見流入"] = (pd.to_numeric(q.get("ブラウズ流入数"), errors="coerce").fillna(0)
                       + pd.to_numeric(q.get("関連流入数"), errors="coerce").fillna(0))
        q = q.merge(master[["video_id", "表示名"]], on="video_id", how="left")
        q = q.dropna(subset=["視聴維持率"])
        if q.empty:
            st.info("診断に使えるデータがまだありません。")
        else:
            mx, my = q["発見流入"].median(), q["視聴維持率"].median()
            q["種別"] = q["video_type"].map({"long": "長尺", "short": "ショート"})
            pts = (alt.Chart(q).mark_circle(size=120, opacity=0.8)
                   .encode(x=alt.X("発見流入:Q", title="発見流入（ブラウズ＋関連）"),
                           y=alt.Y("視聴維持率:Q", title="視聴維持率", axis=alt.Axis(format="%")),
                           color=alt.Color("種別:N",
                                           scale=alt.Scale(domain=TYPE_DOMAIN, range=TYPE_RANGE)),
                           tooltip=["表示名", "発見流入",
                                    alt.Tooltip("視聴維持率:Q", format=".0%"), "登録獲得"]))
            rx = alt.Chart(pd.DataFrame({"x": [mx]})).mark_rule(strokeDash=[4, 4], color=MUTED).encode(x="x:Q")
            ry = alt.Chart(pd.DataFrame({"y": [my]})).mark_rule(strokeDash=[4, 4], color=MUTED).encode(y="y:Q")
            st.altair_chart(_style(pts + rx + ry), width="stretch")

    # 曜日 × 時間帯（中央値・白→オレンジ単色グラデ）
    with st.container(border=True):
        st.markdown("#### 曜日 × 公開時間帯（中央値 総再生）")
        hm = (latest_ret.drop(columns=[c for c in ["公開曜日", "公開時刻"] if c in latest_ret.columns])
              .merge(master[["video_id", "公開曜日", "公開時刻"]], on="video_id", how="left"))
        hm["時間帯"] = hm["公開時刻"].astype(str).str.slice(0, 2) + "時台"
        hm = hm.dropna(subset=["公開曜日"])
        if not hm.empty:
            heat = (alt.Chart(hm).mark_rect(stroke=BRD)
                    .encode(x=alt.X("時間帯:N", sort=None),
                            y=alt.Y("公開曜日:N", sort=WEEKDAY_ORDER),
                            color=alt.Color("median(総再生数):Q", title="中央値総再生",
                                            scale=alt.Scale(range=["#FFFFFF", PRIMARY])),
                            tooltip=[alt.Tooltip("公開曜日:N"), alt.Tooltip("時間帯:N"),
                                     alt.Tooltip("median(総再生数):Q", title="中央値総再生", format=".0f"),
                                     alt.Tooltip("count():Q", title="本数")]))
            text = (alt.Chart(hm).mark_text(baseline="middle", color=MUTED)
                    .encode(x="時間帯:N", y=alt.Y("公開曜日:N", sort=WEEKDAY_ORDER),
                            text=alt.Text("count():Q", format="d")))
            st.altair_chart(_style(heat + text), width="stretch")
            st.caption("セル内の数字は本数(n)。色が濃いほど中央値総再生が高い。n が小さいセルは参考値。")

    cc = st.columns(2)
    with cc[0]:
        with st.container(border=True):
            st.markdown("#### 種別比較（中央値）")
            tb = latest_ret.copy()
            tb["種別"] = tb["video_type"].map({"long": "長尺", "short": "ショート"})
            g = tb.groupby("種別").agg(本数=("video_id", "count"),
                                      中央値総再生=("総再生数", "median"),
                                      維持率中央値=("視聴維持率", "median")).reset_index()
            g["中央値総再生"] = g["中央値総再生"].round(0).astype("Int64")
            g["維持率中央値"] = (g["維持率中央値"] * 100).round(1)
            g["信頼度"] = g["本数"].map(lambda n: "参考値(n<5)" if n < MIN_SAMPLES else "")
            st.dataframe(g, width="stretch", hide_index=True,
                         column_config={"維持率中央値": st.column_config.NumberColumn(
                             format="%.1f%%", help=RETENTION_HELP)})
    with cc[1]:
        with st.container(border=True):
            st.markdown("#### シリーズ別（合計再生 上位）")
            sp = ins.series_performance(latest_ret, master)
            if not sp.empty:
                sp = sp.copy()
                sp["信頼度"] = sp["参考値"].map(lambda x: "参考値(n<5)" if x else "")
                st.dataframe(sp[["シリーズ", "本数", "中央値総再生", "合計再生", "信頼度"]].head(10),
                             width="stretch", hide_index=True)

    with st.container(border=True):
        st.markdown("#### 動画長 × パフォーマンス")
        sc = latest_ret.merge(master[["video_id", "動画長(分)", "表示名"]], on="video_id", how="left")
        sc = sc.dropna(subset=["動画長(分)"])
        if not sc.empty:
            metric = st.radio("縦軸", ["総再生数", "視聴維持率"], horizontal=True, key="scatter_y")
            ycol = "総再生数" if metric == "総再生数" else "視聴維持率"
            sc2 = sc.dropna(subset=[ycol]).copy()
            sc2["種別"] = sc2["video_type"].map({"long": "長尺", "short": "ショート"})
            chart = (alt.Chart(sc2).mark_circle(size=90, opacity=0.75)
                     .encode(x=alt.X("動画長(分):Q"),
                             y=alt.Y(f"{ycol}:Q",
                                     axis=alt.Axis(format="%" if ycol == "視聴維持率" else "d")),
                             color=alt.Color("種別:N",
                                             scale=alt.Scale(domain=TYPE_DOMAIN, range=TYPE_RANGE)),
                             tooltip=["表示名", "動画長(分)", "総再生数",
                                      alt.Tooltip("視聴維持率:Q", title="視聴維持率", format=".1%")]))
            st.altair_chart(_style(chart), width="stretch")
            if ycol == "視聴維持率":
                st.caption(RETENTION_HELP)


# ───────────────────────── 検索KW ─────────────────────────

def _tab_keywords(terms, master):
    with st.container(border=True):
        st.subheader("検索流入キーワード")
        if terms.empty:
            st.info("search_terms がまだありません。")
            return
        t = terms.copy()
        t["流入数"] = pd.to_numeric(t["流入数"], errors="coerce").fillna(0)

        topn = st.slider("表示件数", 10, 50, 25, step=5)
        rk = (t.groupby("検索キーワード")["流入数"].sum()
              .sort_values(ascending=False).head(topn).reset_index())
        chart = (alt.Chart(rk).mark_bar(color=PRIMARY)
                 .encode(x=alt.X("流入数:Q"), y=alt.Y("検索キーワード:N", sort="-x"),
                         tooltip=["検索キーワード", "流入数"]))
        st.altair_chart(_style(chart), width="stretch")

        with st.expander("キーワード × 動画の内訳テーブル"):
            id2title = dict(zip(master["video_id"], master["表示名"]))
            tt = t.copy()
            tt["動画"] = tt["video_id"].map(id2title).fillna(tt["video_id"])
            pivot = (tt.groupby(["検索キーワード", "動画"])["流入数"].sum()
                     .sort_values(ascending=False).head(100).reset_index())
            st.dataframe(pivot, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
