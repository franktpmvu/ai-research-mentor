# 論文知識庫整合（paper-kb）— docs/paper_kb.md

> 入口：../CLAUDE.md。paper-kb 是使用者自己讀過／收藏的論文全文庫（PDF 解析成帶頁碼、章節、段落編號的全文索引）。
> 導師系統用它做兩件事：**講機制前先核對原文**、**讀完的論文自動收進知識庫**。
> **沒有安裝 paper-kb 也完全不影響導師系統**：下面三個指令會印一行提示然後略過。

## 怎麼找到 paper-kb
依序：環境變數 `PAPER_KB_ROOT` → 本專案旁邊的 `paper-kb/`（GitHub repo 版面）→ 旁邊的 `paper-rag-mcp/`。
直接讀它的 SQLite 索引（唯讀），**不需要** MCP 套件，也不需要開 Claude Desktop。

## 1. 講機制前先核對原文（深讀、辯證、順帶驗收時）
- 要講一篇論文「怎麼算、為什麼成立」之前，若它在 paper-kb 裡：
  1. `python3 mentor.py kb_search "<論文裡會出現的英文關鍵字>"` → 找到段落與頁碼；
  2. `python3 mentor.py kb_read <doc_id 或 arXiv 編號> --pages <頁>`（或 `--section Method`）讀原文；
  3. 回覆裡引用時附頁碼（例：「原文 p.4 寫…」）。這能直接減少「框架直覺對、機制細節偏差」的錯誤（雙方都適用）。
- 只比對關鍵字：用英文、用論文裡的原字（搜 "occlusion" 找不到只寫 "blocked" 的段落）。
- 找不到就照常講，不要卡住。

## 2. 讀完的論文收進知識庫（done 收尾）
- done 收尾寫完 `paper_xlsx` 後，對當次討論過、有網址的論文執行：
  `python3 mentor.py kb_queue --url <arXiv abs/pdf 連結或 PDF 直連>`
- 指令只把網址寫進 paper-kb 的 `input_raw/url_queue.txt`；已經在庫裡的 arXiv 論文會自動略過。
- 真正的下載、解析、索引在 paper-kb 下次維護時做（`maintain.bat`，或 `python update.py`；在使用者電腦上跑，網路才通）。下載失敗的網址會留在佇列，健康檢查會提示。

## 指令
```
kb_search "<英文關鍵字>" [--k 5]
kb_read <doc_id|arXiv編號> [--pages 3,4] [--section 關鍵字]   不帶 --pages/--section 時只印章節大綱
kb_queue --url <論文網址>
```
