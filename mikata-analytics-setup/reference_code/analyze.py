"""analyze.py — 隔週レポート生成（経過日数別の推移分析）"""
import gspread
import anthropic
import config
import notify

PROMPT_TEMPLATE = """中学受験チャンネル「中学受験のミカタ」の動画別・経過日数別スナップショットです。
経過日数1/3/7/14/28日の節目データのみ抽出しています。

{data}

次の観点で簡潔に分析し、改善提案を添えてください（過度な数字断定や再現性を誤解させる訴求は禁止）：
1. 検索流入(YT_SEARCH)が立ち上がる動画と、初速だけで失速する動画の違い
2. 経過日数ごとの流入元構成変化（初期=登録者/ブラウズ → 後期=検索 への移行度）
3. 検索流入CTR・視聴時間シェアが高い動画の傾向

判定軸: 視聴時間シェア(主)・検索流入CTR(副)。
注: 少数の検索語は(other)に丸められるため網羅は完全ではない。"""


def load_milestone_rows():
    gc = gspread.service_account(filename=config.SERVICE_ACCOUNT)
    rows = gc.open(config.SHEET_NAME).worksheet("snapshots").get_all_records()
    return [r for r in rows if r.get("経過日数") in config.MILESTONES]


def generate_report(data):
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(data=data)}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def run():
    data = load_milestone_rows()
    if not data:
        print("対象データなし。スキップ。")
        return
    report = generate_report(data)
    print(report)
    notify.send_report(report)


if __name__ == "__main__":
    run()
