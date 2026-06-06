"""cleanup_nonpublic.py — videos_master から public 以外(unlisted/private)の行を削除。

privacy フィルタ実装前の毎時 cron が混入させた限定公開動画の除去用。
- 各 video_id の現在の privacy_status を Data API で取得
- public 以外の行をシートから削除（行番号 降順で一括 batchUpdate）
- 削除後の件数を報告

実行: ./venv/bin/python cleanup_nonpublic.py
"""
import fetch_analytics as fa
import write_to_sheets as ws


def run():
    vm_ws, _ = ws.open_watch_sheets()
    rows = vm_ws.get_all_values()
    data = rows[1:]  # ヘッダー除く
    ids = [r[0] for r in data if r and r[0]]
    det = fa.get_video_details(ids)

    # 削除対象のシート行番号(2始まり) を収集
    to_delete = []  # (row_index, video_id, status, title)
    for i, r in enumerate(data, start=2):
        vid = r[0]
        status = det.get(vid, {}).get("privacy_status", "MISSING")
        if status != "public":
            to_delete.append((i, vid, status, r[1] if len(r) > 1 else ""))

    print(f"全 {len(data)} 行中、public 以外 {len(to_delete)} 行を削除対象とする")
    for i, vid, st, t in to_delete:
        print(f"  row{i} | {st} | {vid} | {t[:36]}")
    if not to_delete:
        print("削除対象なし。終了。")
        return

    sheet_id = vm_ws.id
    # 行番号 降順で deleteDimension リクエストを作成（インデックスは0始まり）
    requests = []
    for i, _, _, _ in sorted(to_delete, key=lambda x: x[0], reverse=True):
        requests.append({
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": i - 1,  # 0始まり
                    "endIndex": i,        # 排他
                }
            }
        })
    vm_ws.spreadsheet.batch_update({"requests": requests})

    remaining = len(vm_ws.get_all_values()) - 1
    print(f"完了: {len(to_delete)} 行を削除。残り {remaining} 行")


if __name__ == "__main__":
    run()
