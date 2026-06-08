"""insights.py — ダッシュボード用の分析ロジック（純粋関数）

タイトルからのシリーズ/話数抽出と、各シート(videos_master / snapshots /
search_terms / hourly_views)からの指標計算をまとめる。
Streamlit 非依存・副作用なしなので単体テスト・レポート生成にも再利用できる。
"""
import re
import unicodedata
from datetime import datetime, timezone
import numpy as np
import pandas as pd


# これ未満の n（サンプル数）は「参考値」とし、断定を避けてグレーアウト表示する。
MIN_SAMPLES = 5


def norm(s):
    """Unicode を NFC 合成。YouTube タイトルは濁点が分解(NFD)されている場合があり、
    そのままだと 'インタビュー' の部分一致が効かないため正規化する。
    NFC は丸数字①や全角＃を保持するので話数判定を壊さない。"""
    return unicodedata.normalize("NFC", str(s))

# ───────────────────────── タイトル解析 ─────────────────────────

_BRACKET = re.compile(r"[【［](.+?)[】］]")
# 話数: "#07_Ep.3" / "# 02_Ep.1" / "＃16" / "#10" / "＃番外編"
_EP = re.compile(r"[#＃]\s*(\d+|番外編)\s*(?:[_＿\s]*Ep\.?\s*(\d+))?", re.IGNORECASE)
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
# シリーズ名と判定するキーワード（年号を含む【】内に現れる）
_SERIES_KW = ("インタビュー", "応援", "ひと押し", "RULES", "管理術")


def _circled_num(text):
    """丸数字①②③… を 1,2,3… に。無ければ 0。"""
    for i, c in enumerate(_CIRCLED, 1):
        if c in text:
            return i
    return 0


def parse_episode(title):
    """タイトルから (シリーズ名, 話数ラベル, 並び順キー) を返す。

    例:
      "…【2026ミカタインタビュー # 07_Ep.3】" -> ("2026ミカタインタビュー", "#07 Ep.3", (7,3))
      "【2025ミカタ生インタビュー ＃16】 …"   -> ("2025ミカタ生インタビュー", "#16", (16,0))
      "【2025…＃番外編 ③】…"                  -> ("2025ミカタ生インタビュー", "番外編③", (1000,3))
    """
    title = norm(title)
    ep_label, ep_sort = "", (9999, 9999)

    m = _EP.search(title)
    if m:
        main, sub = m.group(1), m.group(2)
        if main == "番外編":
            c = _circled_num(title)
            ep_label = f"番外編{_CIRCLED[c-1] if c else ''}"
            ep_sort = (1000, c)
        else:
            n = int(main)
            if sub:
                ep_label, ep_sort = f"#{n:02d} Ep.{sub}", (n, int(sub))
            else:
                ep_label, ep_sort = f"#{n:02d}", (n, 0)

    series = ""
    for b in _BRACKET.findall(title):
        if any(kw in b for kw in _SERIES_KW):
            # 【】内から話数・年頭の記号を除いてシリーズ名にする
            s = re.sub(r"[#＃].*$", "", b)
            # 表記ゆれ吸収のため内部空白を除去（"2023 ミカタ生" → "2023ミカタ生"）
            series = re.sub(r"\s+", "", s).strip("　・|")
            break
    return series, ep_label, ep_sort


def short_title(title, width=42):
    """選択UI用の短縮タイトル。シリーズ【】ブロックを除いて読みやすく。"""
    t = norm(title)
    # シリーズ系の【...】は冗長なので除去（教育タグ【理科】等は残す）
    def _strip(m):
        inner = m.group(1)
        return "" if any(kw in inner for kw in _SERIES_KW) else m.group(0)
    t = _BRACKET.sub(_strip, t)
    t = re.sub(r"\s+", " ", t).strip(" 　・|｜")
    return (t[: width - 1] + "…") if len(t) > width else t


def nice_label(title):
    """選択ボックス用の人間可読ラベル。話数があれば先頭に付与。"""
    _, ep, _ = parse_episode(title)
    st = short_title(title)
    return f"{ep}｜{st}" if ep else st


def enrich_master(master):
    """videos_master に シリーズ / 話数 / 話数sort / 表示名 / 動画長(分) を付与。"""
    if master.empty:
        return master
    m = master.copy()
    parsed = m["タイトル"].map(parse_episode)
    m["シリーズ"] = parsed.map(lambda x: x[0] or "—")
    m["話数"] = parsed.map(lambda x: x[1] or "—")
    m["_epsort"] = parsed.map(lambda x: x[2])
    m["表示名"] = m["タイトル"].map(nice_label)
    m["短縮タイトル"] = m["タイトル"].map(short_title)
    m["動画長(秒)"] = pd.to_numeric(m["動画長(秒)"], errors="coerce")
    m["動画長(分)"] = (m["動画長(秒)"] / 60).round(1)
    return m


# ───────────────────────── 数値整形 ─────────────────────────

_SNAP_NUM = ["経過日数", "総再生数", "検索流入数", "ブラウズ流入数",
             "関連流入数", "外部流入数", "広告流入数", "平均視聴時間(秒)"]
TRAFFIC_COLS = ["検索流入数", "ブラウズ流入数", "関連流入数", "外部流入数", "広告流入数"]
TRAFFIC_LABELS = {
    "検索流入数": "検索", "ブラウズ流入数": "ブラウズ", "関連流入数": "関連動画",
    "外部流入数": "外部", "広告流入数": "広告",
}


def clean_snapshots(snapshots):
    """snapshots の数値列を数値化。"""
    if snapshots.empty:
        return snapshots
    s = snapshots.copy()
    for c in _SNAP_NUM:
        if c in s.columns:
            s[c] = pd.to_numeric(s[c], errors="coerce")
    return s


def latest_snapshot(snapshots):
    """各 video_id について経過日数が最大（=最新）の1行を返す。"""
    if snapshots.empty:
        return snapshots
    s = clean_snapshots(snapshots).dropna(subset=["経過日数"])
    if s.empty:
        return s
    idx = s.groupby("video_id")["経過日数"].idxmax()
    return s.loc[idx].reset_index(drop=True)


def with_retention(latest, master):
    """最新snapshotに 動画長・視聴維持率・1日あたり再生 を付与（masterと結合）。"""
    if latest.empty or master.empty:
        return latest
    # snapshots に既にある列(video_type)は master から引かず重複を防ぐ
    cols = ["video_id", "動画長(秒)", "訴求型"]
    if "video_type" not in latest.columns:
        cols.append("video_type")
    m = master[cols].copy()
    m["動画長(秒)"] = pd.to_numeric(m["動画長(秒)"], errors="coerce")
    df = latest.merge(m, on="video_id", how="left")
    df["視聴維持率"] = np.where(
        df["動画長(秒)"].fillna(0) > 0,
        df["平均視聴時間(秒)"] / df["動画長(秒)"],
        np.nan,
    )
    df["1日あたり再生"] = df["総再生数"] / df["経過日数"].clip(lower=1)
    return df


def latest_metrics(video_metrics):
    """video_metrics から各動画の最新（経過日数最大）を取り出し、
    視聴維持率(0-1)・平均視聴秒・登録獲得 を返す。"""
    if video_metrics is None or video_metrics.empty:
        return pd.DataFrame(columns=["video_id", "視聴維持率", "平均視聴秒", "登録獲得"])
    v = video_metrics.copy()
    v["経過日数"] = pd.to_numeric(v["経過日数"], errors="coerce")
    v = v.dropna(subset=["経過日数"])
    if v.empty:
        return pd.DataFrame(columns=["video_id", "視聴維持率", "平均視聴秒", "登録獲得"])
    v = v.loc[v.groupby("video_id")["経過日数"].idxmax()]
    return pd.DataFrame({
        "video_id": v["video_id"].values,
        "視聴維持率": pd.to_numeric(v["視聴維持率"], errors="coerce").values / 100.0,
        "平均視聴秒": pd.to_numeric(v["平均視聴秒"], errors="coerce").values,
        "登録獲得": pd.to_numeric(v["登録獲得"], errors="coerce").values,
    })


def attach_metrics(latest_ret, video_metrics):
    """latest_ret(snapshots由来) に video_metrics の本物の視聴維持率・登録獲得を統合。
    既存の検索由来 視聴維持率/平均視聴時間 を公式値で置き換え、登録転換率を計算。"""
    if latest_ret.empty:
        return latest_ret
    lm = latest_metrics(video_metrics)
    df = latest_ret.copy()
    if not lm.empty:
        df = df.drop(columns=[c for c in ["視聴維持率"] if c in df.columns])
        df = df.merge(lm, on="video_id", how="left")
        # 平均視聴時間は公式値があれば差し替え
        df["平均視聴時間(秒)"] = df["平均視聴秒"].where(df["平均視聴秒"].notna(),
                                                  df.get("平均視聴時間(秒)"))
    else:
        df["登録獲得"] = np.nan
    views = pd.to_numeric(df.get("総再生数"), errors="coerce")
    df["登録転換率"] = np.where(views > 0, df["登録獲得"] / views, np.nan)
    return df


def traffic_breakdown(row):
    """1行(最新snapshot)を {流入元: 数} の DataFrame に。"""
    data = []
    for col, label in TRAFFIC_LABELS.items():
        v = row.get(col, 0)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0
        if v and v > 0:
            data.append({"流入元": label, "流入数": int(v)})
    return pd.DataFrame(data)


def clean_hourly(hourly):
    if hourly.empty:
        return hourly
    h = hourly.copy()
    h["経過時間(h)"] = pd.to_numeric(h["経過時間(h)"], errors="coerce")
    h["viewCount"] = pd.to_numeric(h["viewCount"], errors="coerce")
    return h


# 比較系の代表値は外れ値に強い「中央値」を基本とする（平均のみの棒グラフは廃止）。
def appeal_performance(latest_with_ret):
    """訴求型別の中央値総再生・検索維持率中央値・本数(n)。"""
    df = latest_with_ret
    if df.empty or "訴求型" not in df.columns:
        return pd.DataFrame()
    df = df[df["訴求型"].astype(str).str.strip() != ""]
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("訴求型").agg(
        本数=("video_id", "count"),
        中央値総再生=("総再生数", "median"),
        維持率中央値=("視聴維持率", "median"),
    ).reset_index()
    g["中央値総再生"] = g["中央値総再生"].round(0).astype("Int64")
    g["維持率中央値"] = (g["維持率中央値"] * 100).round(1)
    g["参考値"] = g["本数"] < MIN_SAMPLES
    return g.sort_values("中央値総再生", ascending=False)


def series_performance(latest, master):
    """シリーズ別の本数(n)・中央値総再生・合計再生。"""
    if latest.empty or master.empty:
        return pd.DataFrame()
    m = master[["video_id", "シリーズ"]]
    df = latest.merge(m, on="video_id", how="left")
    g = df.groupby("シリーズ").agg(
        本数=("video_id", "count"),
        中央値総再生=("総再生数", "median"),
        合計再生=("総再生数", "sum"),
    ).reset_index()
    g["中央値総再生"] = g["中央値総再生"].round(0).astype("Int64")
    g["合計再生"] = g["合計再生"].astype("Int64")
    g["参考値"] = g["本数"] < MIN_SAMPLES
    return g.sort_values("合計再生", ascending=False)


# ───────────────────────── サマリー用ペイロード ─────────────────────────

def _thumb(video_id):
    return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"


def build_summary_payload(master, video_stats, channel_now, channel_hist, goal,
                          search_inflow_total=0, is_live=True):
    """リファレンス風サマリー用の JSON シリアライズ可能な dict を組み立てる。

    master              : enrich_master 済み videos_master DataFrame
    video_stats         : {video_id: {views, likes, comments}}（ライブ取得 or フォールバック）
    channel_now         : {subscribers, total_views, video_count}
    channel_hist        : channel_stats シートの DataFrame（取得日, 登録者数, ...）
    goal                : 登録者目標（int・仮値）
    search_inflow_total : 検索流入(累計)。snapshots 最新の検索流入数合計（KPI主役）
    is_live             : True=ライブAPI / False=シート値フォールバック
    """
    now = datetime.now(timezone.utc)
    videos = []
    for _, r in master.iterrows():
        vid = r["video_id"]
        stt = video_stats.get(vid)
        if not stt:
            continue
        pub = pd.to_datetime(r["公開日時"], errors="coerce", utc=True)
        if pd.isna(pub):
            continue
        days = max((now - pub.to_pydatetime()).total_seconds() / 86400.0, 0.5)
        views = stt["views"]
        videos.append({
            "id": vid,
            "title": norm(r["タイトル"]),
            "short_title": r.get("短縮タイトル", "") or norm(r["タイトル"]),
            "series": r.get("シリーズ", "—"),
            "episode": r.get("話数", "—"),
            "type": r["video_type"],
            "appeal": r.get("訴求型", ""),
            "published": pub.strftime("%Y-%m-%d"),
            "published_ms": int(pub.timestamp() * 1000),
            "days_since": round(days, 1),
            "views": views,
            "likes": stt["likes"],
            "comments": stt["comments"],
            "velocity": int(round(views / days)),
            "thumb": _thumb(vid),
            "url": f"https://youtu.be/{vid}",
        })

    videos.sort(key=lambda v: v["published_ms"])

    # 最新動画と「速度 N位/10」
    latest = None
    if videos:
        recent = sorted(videos, key=lambda v: v["published_ms"], reverse=True)[:10]
        latest = recent[0]
        ranked = sorted(recent, key=lambda v: v["velocity"], reverse=True)
        rank = next((i + 1 for i, v in enumerate(ranked) if v["id"] == latest["id"]), 1)
        latest = {**latest, "velocity_rank": rank, "velocity_pool": len(recent)}

    # 登録者28日差分。28日前以前の履歴が無い間は「蓄積中」とし 0 と誤読させない。
    subs = int(channel_now.get("subscribers", 0))
    delta_28d = 0
    subs_status = "accruing"   # "ok" | "accruing"
    accrue_start = ""
    if channel_hist is not None and not channel_hist.empty and "登録者数" in channel_hist.columns:
        h = channel_hist.copy()
        h["d"] = pd.to_datetime(h["取得日"], errors="coerce")
        h["登録者数"] = pd.to_numeric(h["登録者数"], errors="coerce")
        h = h.dropna(subset=["d", "登録者数"]).sort_values("d")
        if not h.empty:
            cutoff = pd.Timestamp(now.replace(tzinfo=None)) - pd.Timedelta(days=28)
            old = h[h["d"] <= cutoff]
            if not old.empty:
                delta_28d = int(subs - old.iloc[-1]["登録者数"])
                subs_status = "ok"
            else:
                accrue_start = h.iloc[0]["d"].strftime("%m/%d")

    channel = {
        "name": "中学受験のミカタ",
        "subscribers": subs,
        "subs_delta_28d": delta_28d,
        "subs_status": subs_status,
        "accrue_start": accrue_start,
        "search_inflow": int(search_inflow_total),
        "total_views": int(channel_now.get("total_views", 0)),
        "video_count": int(channel_now.get("video_count", len(master))),
        "likes_sum": int(sum(v["likes"] for v in videos)),
        "comments_sum": int(sum(v["comments"] for v in videos)),
        "goal": int(goal),
        "remaining": max(int(goal) - subs, 0),
        "goal_pct": round(min(subs / goal * 100, 100), 1) if goal else 0,
        "is_live": bool(is_live),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {"channel": channel, "videos": videos, "latest": latest}


# ───────────────────────── 年度・シリーズ比較 ─────────────────────────

def video_stats_df(master, video_stats):
    """master にライブ統計(views/likes/comments)を結合し、エンゲージ率・年度を付与。
    公開60日超の旧動画(2025等)も対象になる（ライブ統計は全公開動画で取得可）。"""
    if master.empty or not video_stats:
        return pd.DataFrame()
    rows = []
    for _, r in master.iterrows():
        s = video_stats.get(r["video_id"])
        if not s:
            continue
        views = s.get("views", 0) or 0
        rows.append({
            "video_id": r["video_id"],
            "短縮タイトル": r.get("短縮タイトル", ""),
            "シリーズ": r.get("シリーズ", "—"),
            "話数": r.get("話数", "—"),
            "_epsort": r.get("_epsort", (9999, 9999)),
            "公開日時": r.get("公開日時", ""),
            "video_type": r.get("video_type", ""),
            "views": int(views),
            "likes": int(s.get("likes", 0) or 0),
            "comments": int(s.get("comments", 0) or 0),
            "高評価率": (s.get("likes", 0) / views) if views else 0.0,
            "コメント率": (s.get("comments", 0) / views) if views else 0.0,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    yr = df["シリーズ"].astype(str).str.extract(r"(20\d{2})")[0]
    pub_yr = pd.to_datetime(df["公開日時"], errors="coerce").dt.year
    df["年度"] = yr.fillna(pub_yr.astype("Int64").astype(str)).fillna("—")
    df["サムネ"] = "https://i.ytimg.com/vi/" + df["video_id"] + "/mqdefault.jpg"
    return df


def series_summary(df):
    """シリーズ別の本数・中央値再生・合計再生・平均エンゲージ率（年度付き）。"""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("シリーズ").agg(
        年度=("年度", "first"),
        本数=("video_id", "count"),
        中央値再生=("views", "median"),
        合計再生=("views", "sum"),
        平均高評価率=("高評価率", "mean"),
        平均コメント率=("コメント率", "mean"),
    ).reset_index()
    g["中央値再生"] = g["中央値再生"].round(0).astype("Int64")
    g["合計再生"] = g["合計再生"].astype("Int64")
    g["平均高評価率%"] = (g["平均高評価率"] * 100).round(2)
    g["平均コメント率%"] = (g["平均コメント率"] * 100).round(2)
    return g.drop(columns=["平均高評価率", "平均コメント率"]).sort_values(
        ["年度", "合計再生"], ascending=[False, False])


# ───────────────────────── まとめ素材バンク ─────────────────────────
# 勝ちテンプレ「保護者まとめ型」へ再編集できる自社インタビュー素材のテーマ定義。
# (テーマ, 検出キーワード, まとめ動画タイトル案)
COMPILATION_THEMES = [
    ("続けた習慣", ["習慣", "ルーティン", "毎日", "続けた"],
     "【保護者へ】合格家庭が“密かに続けた習慣”7選"),
    ("親子関係/距離感", ["親子関係", "距離感", "信頼", "反抗", "喧嘩"],
     "伸びる親子は“距離感”が違う｜合格家庭の関係づくり"),
    ("声かけ/接し方", ["声かけ", "接し方", "かけた言葉", "言葉", "励まし"],
     "【中学受験】落ちる子の親がやりがちなNG声かけ／効く声かけ"),
    ("親の役割分担", ["役割分担", "父親", "母親", "夫婦", "分担", "父の役割", "母の役割"],
     "合格家庭の“親の役割分担”ベスト"),
    ("取捨選択/捨てる勇気", ["取捨選択", "やめた", "減らす", "捨て", "カスタマイズ", "戦略"],
     "【捨てる勇気】合格家庭が“やめた・減らした”こと5選"),
    ("直前期/1月校", ["直前", "1月", "一月", "本番", "前日", "当日"],
     "1月校・直前期を乗り切った家庭のリアル TOP5"),
    ("逆転/番狂わせ", ["逆転", "番狂わせ", "リベンジ", "D判定", "E判定", "想定外", "連敗"],
     "D・E判定から逆転した家庭に共通した分岐点"),
    ("学校選び/併願", ["学校選び", "志望校", "併願", "選び方"],
     "学校選び・併願の決め手｜合格家庭のリアル"),
    ("スランプ/メンタル", ["スランプ", "不調", "落ち込", "停滞", "メンタル", "立ち直", "やる気"],
     "スランプを抜けた家庭の実例5選"),
    ("自走/自立", ["自走", "自立", "自分で", "主体"],
     "“自走できる子”に育った家庭の共通点"),
]


def compilation_bank(master):
    """テーマ → 該当インタビュー動画(DataFrame) の辞書を返す。"""
    if master.empty or "シリーズ" not in master.columns:
        return {}
    iv = master[master["シリーズ"].astype(str).str.contains("インタビュー", na=False)].copy()
    if iv.empty:
        return {}
    blob = (iv["タイトル"].astype(str) + " " + iv.get("説明文", "").astype(str)).map(norm)
    out = {}
    for theme, kws, _ in COMPILATION_THEMES:
        pat = "|".join(re.escape(k) for k in kws)
        mask = blob.str.contains(pat, regex=True, na=False)
        out[theme] = iv[mask][["video_id", "短縮タイトル", "話数", "シリーズ", "公開日時"]].copy()
    return out
