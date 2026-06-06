"""reclassify_master.py — videos_master の「訴求型」が空の行だけを再分類して更新。

backfill 時に ANTHROPIC_API_KEY 未解決で分類が全件失敗したケースの復旧用。
- J列(訴求型)が空の行を対象に classify.classify_title を実行
- 成功した行だけ J列をバッチ更新（既存の分類済み行・他カラムには触れない）

実行: ./venv/bin/python reclassify_master.py
"""
import write_to_sheets as ws
import classify

# videos_master の列番号（1始まり）。VIDEOS_MASTER_HEADER と対応。
COL_VIDEO_ID = 1
COL_TITLE = 2
COL_APPEAL = 10  # J列「訴求型」


def run():
    vm_ws, _ = ws.open_watch_sheets()
    values = vm_ws.get_all_values()
    if len(values) <= 1:
        print("データ行なし。終了。")
        return

    rows = values[1:]  # ヘッダー除く
    targets = []  # (sheet_row_index, title)
    for i, row in enumerate(rows, start=2):  # シート行番号は2始まり
        title = row[COL_TITLE - 1] if len(row) >= COL_TITLE else ""
        appeal = row[COL_APPEAL - 1] if len(row) >= COL_APPEAL else ""
        if title and not appeal.strip():
            targets.append((i, title))

    print(f"全 {len(rows)} 行中、未分類 {len(targets)} 行を再分類")
    if not targets:
        print("再分類対象なし。終了。")
        return

    updates = []  # gspread batch_update 形式
    ok = 0
    for n, (row_idx, title) in enumerate(targets, 1):
        appeal = classify.classify_title(title)
        if appeal:
            updates.append({"range": f"J{row_idx}", "values": [[appeal]]})
            ok += 1
            print(f"  [{n}/{len(targets)}] {appeal:　<8} {title[:36]}")
        else:
            print(f"  [{n}/{len(targets)}] (失敗・スキップ) {title[:36]}")

    if updates:
        vm_ws.batch_update(updates, value_input_option="RAW")
    print(f"完了: {ok}/{len(targets)} 行の訴求型を更新")


if __name__ == "__main__":
    run()
