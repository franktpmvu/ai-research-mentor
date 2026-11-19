# paper-rag-mcp 指引｜目錄

> 這份是**索引**：每件事只寫一行，要做那件事時去讀對應的細則。
> 細則只寫「目前最新」的規則；改了什麼、為什麼改，寫在 `guide/changelog/`。
> 本機（專案根目錄）與雲端（claude.ai Project「rag_paper_proj」）保持同一份內容，規則見 R00。

## 專案一句話
做一個「**MCP server＋可替換 encoder**」的搜尋系統，目前內容是論文，但骨架不限論文。
- encoder 可以是全文搜尋、RAG，或其他技術，可以並存：
  - 全文搜尋（BM25）的強項：**真實來源**，命中的字一定在原文裡。
  - RAG（向量）的強項：**語意比對、模糊搜尋**，用詞不一樣也找得到。
- 不論用哪種 encoder，最後回給 AI 的都是**原文段落＋para_id＋頁碼**。

## 開工前必讀
1. 先讀這份目錄，再依任務讀對應的細則。
2. 不確定屬於哪一條時，先讀 R01 架構。
3. 改了任何細則，照 R00 更新變更紀錄，並同步到兩邊。

## 目錄

| # | 要做的事 | 細則 |
|---|---|---|
| R00 | 修改指引、寫變更紀錄、本機／雲端同步 | 請至 `guide/rules/R00_guide-maintenance.md` |
| R01 | 了解專案目標、架構分層、設計原則（不限論文的骨架） | 請至 `guide/rules/R01_architecture.md` |
| R02 | 加入新資料（PDF、網址、Zotero）、跑更新流程 | 請至 `guide/rules/R02_ingest-update.md` |
| R03 | 修改或更換 PDF 解析器、新增其他文件類型 | 請至 `guide/rules/R03_parsing.md` |
| R04 | 全文搜尋 encoder（SQLite FTS5／BM25）的使用與修改 | 請至 `guide/rules/R04_encoder-fulltext.md` |
| R05 | 新增向量（RAG）或混合 encoder | 請至 `guide/rules/R05_encoder-vector-hybrid.md` |
| R06 | 使用、修改或新增 MCP 工具；接上 Claude Desktop | 請至 `guide/rules/R06_mcp-tools.md` |
| R07 | 建立評估集、跑評估、比較 encoder | 請至 `guide/rules/R07_evaluation.md` |
| R08 | 日常維運：maintain.bat、健康檢查、排程、故障處理 | 請至 `guide/rules/R08_maintenance.md` |
| R09 | 公開 GitHub repo、隱私與不上傳清單 | 請至 `guide/rules/R09_public-repo.md` |

## 其他既有文件（給人看的說明，非規則）
- `README.md`：使用說明。`PLAN.md`：早期設計紀錄。`INGEST.md`：更新流程說明。
- `HANDOFF_from_resume.md` 是另一個專案（frank_resume）寫來的交接單，**不是本專案的目標**，不要依照它做事。
- 這些文件和細則衝突時，**以細則為準**，並把該文件修正（見 R00）。

## 目前進度（2026-11-18）
- ✅ 解析、FTS5 全文 encoder、引用關係、update.py、maintain.bat、接上 Claude Desktop
- ✅ 評估題目 63 題（從 atomic_habit 擷取、語意改寫）、代理評估腳本
- ✅ 向量 encoder（Ollama qwen3-embedding 0.6b／4b）＋混合（RRF）＋MCP `semantic_search`（共 6 個工具）
- ⬜ 在 Windows 算好向量、跑三組比較 ⬜ 候選池＋標註＋正式評估 ⬜ README 更新 ⬜ 公開 repo
