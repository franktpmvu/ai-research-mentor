# 論文知識庫 paper-kb

> 目錄：../CLAUDE.md

paper-kb 是使用者自己讀過／收藏的論文全文庫（PDF 解析成帶頁碼、章節、段落編號的索引）。**沒裝 paper-kb 不影響導師系統**：下面指令會印一行提示然後略過。

## 什麼時候用
1. 深讀、辯證、順帶驗收時，要講一篇論文「怎麼算、為什麼成立」之前 → 先核對原文。
2. done 收尾時（`paper_xlsx` 之後）→ 把當次討論過的論文排進知識庫。

## 怎麼做
**核對原文**
1. `python3 mentor.py kb_search "<論文裡會出現的英文關鍵字>" [--k 5]` → 找段落與頁碼。關鍵字要用英文、用論文原字（搜 "occlusion" 找不到只寫 "blocked" 的段落）。
2. `python3 mentor.py kb_read <doc_id 或 arXiv 編號> --pages 3,4`（或 `--section Method`；不帶範圍只印章節大綱）。
3. 回覆引用時附頁碼（例：「原文 p.4 寫…」）。
4. 找不到就照常講，不要卡住。

**排進知識庫**
- `python3 mentor.py kb_queue --url <arXiv abs/pdf 連結或 PDF 直連>`：只把網址寫進佇列，已在庫的 arXiv 論文自動略過。
- 真正下載、解析、索引由 paper-kb 維護時做（使用者電腦上跑 `maintain.bat` 或 `python update.py`）。下載失敗的網址留在佇列，健康檢查會提示。

## 怎麼找到 paper-kb
依序：環境變數 `PAPER_KB_ROOT` → 本專案旁的 `paper-kb/` → 旁邊的 `paper-rag-mcp/`。直接唯讀它的 SQLite 索引，不需要 MCP、不需要開 Claude Desktop。

## 驗收標準
- 講機制時若論文在庫裡，回覆中有附頁碼的原文依據。
- done 後，當次討論過且有網址的論文都已 `kb_queue`（或已在庫）。

## 存放位置
- 索引：paper-kb 資料夾的 SQLite（唯讀）。
- 佇列：paper-kb 的 `input_raw/url_queue.txt`。
