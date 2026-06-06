# SIDEBAR_PIN.md — ローカルフォルダを Finder サイドバーに固定

自動化スクリプトは **ローカルの `~/mikata-analytics`（Drive外）** に置く。
このローカルフォルダをサイドバーに固定しておくと日々アクセスしやすい。

## 方法A: ドラッグで固定（最も簡単）
1. Finder で `command + shift + H` → ホームフォルダを開く
2. `mikata-analytics` フォルダを見つける
3. それを Finder 左の「よく使う項目」セクションへ**ドラッグ＆ドロップ**

## 方法B: メニューから固定
1. `mikata-analytics` フォルダを選択
2. メニューバー「ファイル」→「サイドバーに追加」（`control + command + T`）

## 方法C: ターミナルから（任意）
ローカルフォルダが存在することの確認だけ:
```bash
open ~/mikata-analytics
```
開いた Finder ウィンドウで上記Aを行う。

---

注意: 先に Google Drive 内に作ってしまった `mikata-analytics` は使わない。
Drive内のものは中身が無ければ削除してよい（token.json等を入れる前提なので空のはず）。
サイドバーに固定するのは必ず**ローカルの `~/mikata-analytics`** のほう。
