# 寫入 論文閱讀.xlsx（paper_xlsx）

> 目錄：../CLAUDE.md

目的：除了文獻歸類，更要讓使用者**好幾年後回來看，仍讀得懂當時在問什麼、思考怎麼轉彎**。

## 什麼時候用
- done 收尾，且當次**真的有討論某篇論文**（有 `review`／`journal_add`）→ 每篇一次。
- 只有 `light_checkin` 的日子不寫。
- 順序：`journal_add` 之後、`sheet_sync` 之前（`done_closing.md`）。

## 欄位規則
| 欄 | 內容 | 規則 |
|---|---|---|
| A | 日期 | 自動 |
| B | 正式標題 | 程式核實（`refcheck.md`），不是正式標題就不寫 |
| C note | 使用者原話 | **只能是使用者打的字，逐字**；程式從 journal 擷取，禁止手打或改寫、不加標記 |
| D question | 導師的話（可精煉） | 依序：【當時的思考軌跡】（起點→被修正處→推到哪，含走錯的路）→【要解決的問題】【怎麼解】【關鍵機制】→【導師回應】→【未釐清】→【補強文獻】 |
| E／F／G | URL、年份、第一作者 et al. | 程式核實 |
| H–L | 領域、判定（讀 learner.json）、paper_id、背景知識（預設 kg 先修）、journal 檔名 | 自動帶入，可用 flag 覆寫 |
| M 對話脈絡 | 導師提問 ↔ 使用者原話，依順序交錯 | 導師端寫當時實際的提問（可略精簡，保留問句）；使用者端只寫 `{U1}{U2}…` 佔位符，程式代入逐字原文，每段剛好用一次 |
- 【補強文獻】每條必須是「正式英文標題 [arXiv:…]／[doi:…]／[url:…]」，任何一條未核實 → 整筆不寫（`refcheck.md`）。

## 怎麼做
1. 把 D、M 內容寫成暫存檔，放 `$HOME`（**不要**放進專案資料夾）。
2. 執行：
   ```
   python3 mentor.py paper_xlsx --pid <id> --journal <檔名1,檔名2> \
       --question $HOME/q.txt --context $HOME/ctx.txt \
       --title "正式標題" --year 2025 --authors "First Author et al."
   ```
   - `--dry` 預覽；`--replace` 覆寫已存在的列；`--flush` 補寫佇列；`--url`、`--bg` 可覆寫。
3. 記下輸出的「新增／追記／覆寫 → 第 N 列」，交給 `sheet_sync.md`。

## 自動行為
- 同一篇再次討論 → 原列追記，不新增列：C 欄接上新原話；D、M 欄加 `[MM/DD 追記]`。
- 每次寫入前輪替備份到 `archive/xlsx_bak/`（10 格）。
- A 欄舊 `NOW()` 公式自動凍結成固定日期；遇到沒有日期快取的公式就停手不寫。
- Excel 開著這個檔（偵測到 `~$論文閱讀.xlsx`）→ 先存進 `paper_xlsx_pending.json`，下次自動補寫。

## 驗收標準
- 程式回報寫入成功並給出列號（或明確說明進了佇列）。
- C 欄與 journal 原話一字不差；M 欄的每個 `{Un}` 剛好用一次（程式驗證）。

## 存放位置
- 主檔：專案資料夾的 `論文閱讀.xlsx`。
- 備份：`archive/xlsx_bak/`；佇列：`paper_xlsx_pending.json`。
- 程式：`paperlog.py`（由 `mentor.py paper_xlsx` 呼叫）。
