"""deep_youtube_audit.py — YouTube Analytics 徹底分析（国/広告/コホート/デバイス）

期間: 2024-06 〜 2026-06（月次系は月初締めのため 2026-05 まで）
出力: ga4-audit/output/youtube/deep/ に各CSV + deep_analysis.md

APIの制約（プローブで確認済み）:
- month ディメンションは endDate を「月初(YYYY-MM-01)」に揃える必要がある
- country/deviceType/video × insightTrafficSourceType==ADVERTISING フィルタは「非対応」
  → 広告の国/デバイス内訳は直接取得不可。広告濃淡(月次ad share)からの【推定】で代替
- insightTrafficSourceDetail × ADVERTISING は取得可 → 広告フォーマット名が得られる
- 動画別の広告視聴は filters=video==X, dimensions=insightTrafficSourceType から ADVERTISING 行を抽出
"""
import calendar
import csv
import os
from collections import defaultdict

import pandas as pd

import config
import fetch_analytics as fa
import gauth
import insights as ins

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "ga4-audit", "output", "youtube", "deep")
os.makedirs(OUT, exist_ok=True)
CID = config.CHANNEL_ID
_Q = fa._yt_analytics.reports().query

WIN_START = "2024-06-01"
WIN_END_DAY = "2026-06-10"     # 日次締め（非month系）
WIN_END_MONTH = "2026-06-01"   # month系（=2026-05まで含む）

# 暦年バケット（窓内）。2024はH2のみ・2026は年央までの部分期間。
YEARS = [
    ("2024", "2024-06-01", "2024-12-31"),
    ("2025", "2025-01-01", "2025-12-31"),
    ("2026", "2026-01-01", WIN_END_DAY),
]
NATURAL_EXCLUDE = {"ADVERTISING", "EXT_URL"}  # コホートの「自然流入」から除外


def q(metrics, dimensions=None, filters=None, start=WIN_START, end=WIN_END_DAY,
      sort=None, maxResults=None):
    kw = dict(ids=f"channel=={CID}", startDate=start, endDate=end, metrics=metrics)
    if dimensions:
        kw["dimensions"] = dimensions
    if filters:
        kw["filters"] = filters
    if sort:
        kw["sort"] = sort
    if maxResults:
        kw["maxResults"] = maxResults
    return _Q(**kw).execute().get("rows", [])


def write_csv(name, header, rows):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  -> {name} ({len(rows)} 行)")


def load_meta():
    sh = gauth.open_sheet()
    m = ins.enrich_master(pd.DataFrame(sh.worksheet("videos_master").get_all_records()))
    meta = {}
    for _, r in m.iterrows():
        meta[r["video_id"]] = {
            "title": str(r.get("タイトル", "")),
            "published": str(r.get("公開日時", ""))[:10],
            "duration": float(r.get("動画長(秒)") or 0),
            "series": str(r.get("シリーズ", "—")),
            "year": str(r.get("公開日時", ""))[:4],
        }
    return meta


# ───────────────────────── 1. 国別分析 ─────────────────────────

def analyze_country(meta):
    print("[1] 国別分析")
    notes = []

    # 1-a 月次×国
    rows = q("views,estimatedMinutesWatched", "month,country",
             end=WIN_END_MONTH, sort="month")
    write_csv("country_monthly_views.csv",
              ["month", "country", "views", "minutes"], rows)
    month_country = defaultdict(lambda: defaultdict(int))  # month -> country -> views
    for mo, c, v, _mins in rows:
        month_country[mo][c] += int(v)

    # 1-b 年別 国別トップ + 日本vs海外
    top_rows, jp_rows = [], []
    for year, s, e in YEARS:
        cr = q("views", "country", start=s, end=e, sort="-views")
        total = sum(int(r[1]) for r in cr) or 1
        for c, v in cr[:15]:
            top_rows.append([year, c, int(v), round(int(v) / total * 100, 2)])
        jp = sum(int(v) for c, v in cr if c == "JP")
        ov = total - jp
        jp_rows.append([year, jp, round(jp / total * 100, 2),
                        ov, round(ov / total * 100, 2), total])
    write_csv("country_top_by_year.csv",
              ["year", "country", "views", "share_%"], top_rows)
    write_csv("country_jp_vs_overseas_by_year.csv",
              ["year", "jp_views", "jp_%", "overseas_views", "overseas_%", "total"], jp_rows)
    for r in jp_rows:
        notes.append(f"  {r[0]}: 日本 {r[2]}% / 海外 {r[4]}%（総再生 {r[5]:,}）")

    # 1-c 広告の国別構成【推定】: country×ADV も month×ADV も非対応
    #     → 月ごとに insightTrafficSourceType をループして広告月次を取得し、ad share の濃淡で推定
    all_m = {r[0]: int(r[1]) for r in q("views", "month", end=WIN_END_MONTH, sort="month")}
    adv_m = {}
    for mo in all_m:  # mo = 'YYYY-MM'
        y, mm = int(mo[:4]), int(mo[5:7])
        s, e = f"{mo}-01", f"{mo}-{calendar.monthrange(y, mm)[1]:02d}"
        try:
            tb = q("views", "insightTrafficSourceType", start=s, end=e)
            adv_m[mo] = next((int(r[1]) for r in tb if r[0] == "ADVERTISING"), 0)
        except Exception:
            adv_m[mo] = 0
    share_rows = []
    for mo in sorted(all_m):
        a, t = adv_m.get(mo, 0), all_m[mo]
        share_rows.append([mo, t, a, round(a / t * 100, 2) if t else 0])
    write_csv("monthly_adv_share.csv",
              ["month", "total_views", "adv_views", "adv_share_%"], share_rows)

    shares = sorted(r[3] for r in share_rows)
    med = shares[len(shares) // 2] if shares else 0
    heavy = {r[0] for r in share_rows if r[3] >= med and r[2] > 0}
    light = {r[0] for r in share_rows if r[3] < med}
    def country_share(months):
        agg = defaultdict(int)
        tot = 0
        for mo in months:
            for c, v in month_country.get(mo, {}).items():
                agg[c] += v
                tot += v
        return agg, (tot or 1)
    h_agg, h_tot = country_share(heavy)
    l_agg, l_tot = country_share(light)
    inf = []
    for c in set(h_agg) | set(l_agg):
        hs = h_agg.get(c, 0) / h_tot * 100
        ls = l_agg.get(c, 0) / l_tot * 100
        inf.append([c, round(hs, 2), round(ls, 2), round(hs - ls, 2)])
    inf.sort(key=lambda x: -x[3])
    write_csv("adv_country_inference.csv",
              ["country", "ad_heavy_months_share_%", "ad_light_months_share_%", "delta_pt"], inf)
    notes.append("  広告国別は直接取得不可→推定。広告濃い月で構成比が上がる国（delta上位）="
                 + ", ".join(f"{r[0]}(+{r[3]})" for r in inf[:3]))
    return notes


# ───────────────────────── 2. 広告フォーマット分析 ─────────────────────────

def analyze_ad_format():
    print("[2] 広告フォーマット分析")
    notes = []
    out_rows = []
    year_format = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))  # year->fmt->[views,min,durxviews]
    for year, s, e in YEARS:
        try:
            # insightTrafficSourceDetail は sort と maxResults の両方が必須
            rows = q("views,estimatedMinutesWatched,averageViewDuration",
                     "insightTrafficSourceDetail",
                     filters="insightTrafficSourceType==ADVERTISING", start=s, end=e,
                     sort="-views", maxResults=25)
        except Exception as ex:  # noqa: BLE001
            print(f"     {year} 広告フォーマット取得失敗（スキップ）: {str(ex)[:60]}")
            continue
        for fmt, v, mins, dur in rows:
            acc = year_format[year][fmt]
            acc[0] += int(v)
            acc[1] += int(mins)
            acc[2] += float(dur) * int(v)
    for year in [y for y, _, _ in YEARS]:
        fmts = year_format[year]
        yr_total = sum(a[0] for a in fmts.values()) or 1
        for fmt, a in sorted(fmts.items(), key=lambda x: -x[1][0]):
            avgdur = round(a[2] / a[0], 0) if a[0] else 0
            out_rows.append([year, fmt, a[0], a[1], int(avgdur),
                             round(a[0] / yr_total * 100, 1)])
    write_csv("ad_format_by_year.csv",
              ["year", "format", "views", "minutes", "avg_dur_sec", "share_of_year_ad_%"], out_rows)

    # 2025 vs 2026 構成変化
    def comp(year):
        fmts = year_format[year]
        tot = sum(a[0] for a in fmts.values()) or 1
        return {f: a[0] / tot * 100 for f, a in fmts.items()}
    c25, c26 = comp("2025"), comp("2026")
    notes.append("  フォーマット構成（views比）:")
    for f in sorted(set(c25) | set(c26), key=lambda x: -(c25.get(x, 0) + c26.get(x, 0))):
        notes.append(f"    {f}: 2025 {c25.get(f,0):.1f}% → 2026 {c26.get(f,0):.1f}%")
    return notes


# ───────────────────────── 3. 広告対象動画 ─────────────────────────

def analyze_ad_target_videos(meta):
    print("[3] 広告対象動画（動画ループでADVERTISING抽出）")
    windows = [("2025_02-08", "2025-02-01", "2025-08-31"),
               ("2026_02-06", "2026-02-01", WIN_END_DAY)]
    out = []
    for label, s, e in windows:
        recs = []
        for vid, mt in meta.items():
            if mt["published"] and mt["published"] > e:
                continue  # 窓終了後に公開＝データ無し
            try:
                tb = fa.get_traffic_by_source(vid, s, e)
            except Exception:
                continue
            adv = next((r for r in tb if r[0] == "ADVERTISING"), None)
            if not adv:
                continue
            views = int(adv[1])
            if views <= 0:
                continue
            mins = int(adv[2])
            dur = float(adv[3])
            length = mt["duration"] or 0
            pct = round(dur / length * 100, 2) if length else 0
            recs.append([label, vid, mt["title"], mt["published"], int(length),
                         views, mins, int(dur), pct])
        recs.sort(key=lambda x: -x[5])
        out.extend(recs[:30])
        print(f"     {label}: 広告検出 {len(recs)} 本")
    write_csv("ad_target_videos_top.csv",
              ["window", "video_id", "title", "published", "duration_sec",
               "adv_views", "adv_minutes", "adv_avg_dur_sec", "adv_avg_view_pct"], out)
    return [f"  広告対象動画 上位を2窓で抽出（計{len(out)}行）"]


# ───────────────────────── 4. 動画別 登録者獲得 ─────────────────────────

def analyze_subs_by_video(meta):
    print("[4] 動画別 登録者獲得")
    out = []
    for year, s, e in YEARS:
        rows = q("subscribersGained", "video", start=s, end=e,
                 sort="-subscribersGained", maxResults=200)
        for vid, subs in rows[:30]:
            mt = meta.get(vid, {})
            out.append([year, vid, mt.get("title", ""), mt.get("published", ""), int(subs)])
    write_csv("subs_gained_by_video.csv",
              ["year", "video_id", "title", "published", "subs_gained"], out)
    return [f"  登録者獲得 上位を年別に抽出（{len(out)}行）"]


# ───────────────────────── 5. コホート比較 ─────────────────────────

def analyze_cohort(meta):
    print("[5] コホート比較（2026公開=新インタビュアー vs それ以前／自然流入）")
    subs_all = {r[0]: int(r[1]) for r in q("subscribersGained", "video",
                start=WIN_START, end=WIN_END_DAY, sort="-subscribersGained", maxResults=200)}
    per_video = []
    for vid, mt in meta.items():
        try:
            tb = fa.get_traffic_by_source(vid, WIN_START, WIN_END_DAY)
        except Exception:
            continue
        nv = nm = 0
        for src, v, mins, _dur in tb:
            if src in NATURAL_EXCLUDE:
                continue
            nv += int(v)
            nm += int(mins)
        if nv <= 0:
            continue
        length = mt["duration"] or 0
        nat_dur = nm * 60 / nv
        pct = round(nat_dur / length * 100, 2) if length else 0
        cohort = "2026公開(新)" if mt["year"] == "2026" else "〜2025公開(旧)"
        per_video.append([cohort, vid, mt["title"], mt["published"], nv,
                          int(nat_dur), pct, subs_all.get(vid, 0)])
    write_csv("cohort_per_video.csv",
              ["cohort", "video_id", "title", "published", "natural_views",
               "natural_avg_dur_sec", "natural_avg_view_pct", "subs_gained"], per_video)

    agg = defaultdict(list)
    for r in per_video:
        agg[r[0]].append(r)
    summ = []
    for cohort, rs in agg.items():
        n = len(rs)
        pcts = [r[6] for r in rs if r[6]]
        durs = [r[5] for r in rs if r[5]]
        navs = sorted(r[4] for r in rs)
        subs = sum(r[7] for r in rs)
        summ.append([cohort, n,
                     round(sum(pcts) / len(pcts), 2) if pcts else 0,
                     round(sum(durs) / len(durs), 0) if durs else 0,
                     round(subs / n, 1) if n else 0,
                     navs[len(navs) // 2] if navs else 0])
    summ.sort(key=lambda x: x[0])
    write_csv("cohort_compare.csv",
              ["cohort", "videos", "avg_view_pct_natural", "avg_view_dur_sec_natural",
               "subs_per_video", "median_natural_views"], summ)
    notes = ["  コホート（自然流入＝広告/外部除く）:"]
    for r in summ:
        notes.append(f"    {r[0]}: n={r[1]} 維持率{r[2]}% 平均視聴{r[3]}秒 "
                     f"登録/本{r[4]} 中央自然再生{r[5]:,}")
    return notes


# ───────────────────────── 6. デバイス別 ─────────────────────────

def analyze_device():
    print("[6] デバイス別")
    # month×deviceType は非対応 → day×deviceType を取得し月次に集計
    drows = q("views,estimatedMinutesWatched", "day,deviceType", end=WIN_END_DAY, sort="day")
    agg = defaultdict(lambda: [0, 0])  # (month,dev) -> [views,minutes]
    for day, dev, v, mins in drows:
        key = (day[:7], dev)
        agg[key][0] += int(v)
        agg[key][1] += int(mins)
    month_rows = [[mo, dev, vm[0], vm[1]] for (mo, dev), vm in sorted(agg.items())]
    write_csv("device_monthly.csv", ["month", "deviceType", "views", "minutes"], month_rows)
    yr_rows = []
    for year, s, e in YEARS:
        dr = q("views", "deviceType", start=s, end=e, sort="-views")
        tot = sum(int(r[1]) for r in dr) or 1
        for dev, v in dr:
            yr_rows.append([year, dev, int(v), round(int(v) / tot * 100, 1)])
    write_csv("device_by_year.csv", ["year", "deviceType", "views", "share_%"], yr_rows)
    return ["  デバイス別 月次・年別を出力（広告×デバイスは非対応のため割愛）"]


# ───────────────────────── レポート ─────────────────────────

def main():
    print(f"出力先: {OUT}")
    meta = load_meta()
    print(f"動画メタ: {len(meta)} 本\n")
    sections = []
    for title, fn in [
        ("1. 国別分析", lambda: analyze_country(meta)),
        ("2. 広告フォーマット分析", analyze_ad_format),
        ("3. 広告対象動画", lambda: analyze_ad_target_videos(meta)),
        ("4. 動画別 登録者獲得", lambda: analyze_subs_by_video(meta)),
        ("5. コホート比較", lambda: analyze_cohort(meta)),
        ("6. デバイス別", analyze_device),
    ]:
        try:
            notes = fn()
        except Exception as e:  # noqa: BLE001
            notes = [f"  [ERROR] {type(e).__name__}: {e}"]
            print("  !!", notes[0])
        sections.append((title, notes))

    md = ["# YouTube 徹底分析 所見（2024-06 〜 2026-06）", "",
          f"対象チャンネル: {config.CHANNEL_ID}", "",
          "> 注: YouTube Analytics APIの制約により、**広告×国 / 広告×デバイス / 広告×動画(直接)** は"
          "取得不可。広告の国/デバイス内訳は月次の広告濃淡からの【推定】、広告対象動画は動画ごとの"
          "流入元内訳からADVERTISING行を抽出して算出。月次系は月初締めのため2026-05まで。", ""]
    for title, notes in sections:
        md.append(f"## {title}")
        md.extend(notes)
        md.append("")
    with open(os.path.join(OUT, "deep_analysis.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n完了: deep_analysis.md + 各CSV を出力しました。")


if __name__ == "__main__":
    main()
