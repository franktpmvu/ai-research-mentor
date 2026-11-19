# 同步到 Google Sheet（sheet_sync）

> 目錄：../CLAUDE.md

本機 `論文閱讀.xlsx` 是**主檔**；Google Sheet 是**同列號鏡像**（A–M 欄）。

## 什麼時候用
- `paper_xlsx` 寫入成功之後，且 `profile.md` 裡有「論文閱讀 Google Sheet ID」。沒有就整步略過。

## 怎麼做
1. 取 `paper_xlsx` 印出的列號 N。
2. `python3 sheetsync.py rows N`
3. 把輸出的 `range`、`values` **原封不動**交給 Google Sheets 連接器 `update_values`（spreadsheetId 用 profile 的 ID）。追記也整列覆蓋，不會重複。
- `paper_xlsx` 因 Excel 開著而進佇列 → 那次不同步；下次 `--flush` 補寫成功後，同步補寫的那幾列。
- 整份對帳：`python3 sheetsync.py rows 2-<最後一列>`；同步表頭：`python3 sheetsync.py header`。

## 失敗時
- 連接器失敗或沒連：本機照常完成，在對話裡提醒「Sheet 未同步第 N 列」，下次 done 一併補。

## 驗收標準
- Sheet 第 N 列與本機 xlsx 第 N 列 A–M 欄內容一致。

## 存放位置
- Sheet ID：`profile.md`（個人設定，不上傳 GitHub）。
- 程式：`sheetsync.py`。
