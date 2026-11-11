# 資料更新流程（INGEST）

> 新資料進來時怎麼更新整個系統。一句話：**丟進 `input_raw/inbox/`，跑 `python update.py`。**

## 日常使用

```bash
# 1. 新資料丟進 inbox（PDF、zip、整個資料夾都可以）
# 2. 先看看會發生什麼
python update.py --dry-run
# 3. 正式執行
python update.py
```

跑完看 `data/derived/update_log.md` 的最後一段，就知道這次新增了什麼、補了哪些洞。

## 流程

| 步驟 | 做什麼 | 只處理變動的部分？ |
|---|---|---|
| ⓪ 下載 | `input_raw/url_queue.txt` 每行一個網址（arXiv abs/pdf 或 PDF 直連）→ 下載到 `inbox/`；成功的從佇列移除，失敗的留著下次再試 | — |
| ① 收件 | `inbox/` → `batches/YYMMDD_名稱/`；zip 原檔放 `_original/`，旁邊解壓 | — |
| ② 盤點 | 掃 `batches/` 和 `corpus/*_refs/pdf/`，記錄 hash、頁數、標題、arXiv、DOI → `registry.csv` | ✅ 大小與修改時間沒變就不重算 |
| ③ 去重 | 同檔案（hash）、同 arXiv 編號、同 DOI 歸成一組；每組選一份 canonical | 每次重算（很快） |
| ④ 補洞 | corpus 裡缺 PDF 的參考文獻，若新資料裡有 → 複製過去、更新筆記 | ✅ 已補過的跳過 |
| ⑤ 解析 | PDF → 帶頁碼、章節、段落的 JSON（`data/derived/parsed/`） | ✅ 只解析新的或解析器版本不同的 |
| ⑥ 索引 | 解析結果寫進 SQLite FTS5（`data/derived/index/papers.db`）；已移除的文件刪掉；引用關係表整張重建 | ✅ 只處理新的或版本不同的 |
| ⑦ 發布 | `index_version.json` 版本號 +1、寫 `update_log.md` | 沒變動就不加版本號 |

常用參數：

| 參數 | 用途 |
|---|---|
| `--workers 2` | 同時解析 2 份（每份約 0.7 GB 記憶體） |
| `--minutes 2` | 解析最多跑 2 分鐘就先停，沒做完的下次接著做 |
| `--doc-timeout 90` | 單份超過 90 秒就跳過（預設 300），記成 `TIMEOUT` |
| `--retry-failed` | 重試先前失敗（`ERR`）或逾時（`TIMEOUT`）的文件 |

中途被中止也沒關係：每份解析結果檔都記著解析器版本，下次會認得、不重做。

## 什麼時候要「全部重建」

只處理變動的部分，前提是處理方式沒變。下面三種情況要全部重做：

| 改了什麼 | 怎麼做 |
|---|---|
| PDF 解析方式（換解析器或改解析規則） | 改 `src/paper_kb/ingest/pdf.py` 的 `PARSER_VERSION` → 自動重新解析＋重新索引全部 |
| 索引結構或斷詞方式 | 改 `src/paper_kb/index.py` 的 `INDEX_VERSION` → 自動重新索引全部（不用重新解析，約 30 秒） |
| 不確定、或索引壞了 | `python update.py --rebuild` |

每份文件都記錄了它是用哪個版本處理的（`registry.csv` 的 `parsed_ver`、`indexed_ver`），所以改版本號就會只重做「版本不符」的文件。

## MCP server 要不要動？

**不用。** MCP server 只讀索引：
- server 每次收到查詢時，先看 `data/derived/index_version.json` 的版本號；和記憶體裡的不同就重新載入索引。
- 所以跑完 `update.py`，**不用重啟 server**，下一次查詢就會用到新資料。

只有兩種情況要改 MCP：
1. 加了**新類型**的資料，需要新的查詢方式（例如決策紀錄要能依日期查 → 新增 filter 或工具）。
2. registry 新增了欄位，想讓工具能用它過濾。

## 資料夾

```
paper-rag-mcp/
├── update.py                 # 更新流程（本文件）
├── input_raw/
│   ├── inbox/                # ← 新資料丟這裡
│   └── batches/              # 收件後的原始資料（只搬不改）
│       └── 261105_downloaded_paper/
│           ├── _original/downloaded_paper.zip
│           └── ...（解壓後的 PDF）
├── corpus/                   # 你論文的參考文獻（筆記＋PDF）
└── data/derived/             # 全部是衍生資料，可整個刪掉重建
    ├── registry.csv          # 每個 PDF 一列：hash、標題、重複群組、canonical、處理版本
    ├── index_version.json    # MCP server 用來判斷要不要重新載入
    ├── update_log.md         # 每次更新的紀錄
    ├── parsed/<doc_id>.json  # 解析結果：每段有頁碼、章節、para_id
    └── index/papers.db       # FTS5 全文索引＋文件清單＋引用關係
```

## 目前狀態（2026-11-05 第一次執行）
- 288 個 PDF → 去重後 248 份 canonical（40 份重複不索引）
- corpus 從收藏補上 21 篇參考文獻（第一批 19 篇手動確認，第二批 2 篇由 `update.py` 自動補上）
- `data/derived/_to_delete/`：第一次手動盤點的舊檔（manifest.csv 等）與測試檔，可以整個刪掉

## 2026-11-10 第一次完整解析
- 247 份解析＋索引完成（4.7 萬段，其中 1.2 萬段是參考文獻區）；1 份逾時跳過：整本 LNCS 論文集
- 在 VM（2 核、3 GB）上 `--workers 2`，每份平均約 5 秒

## 已知限制
- 去重只看 hash、arXiv 編號、DOI。同一篇論文的不同版本，若檔名和側邊標記都沒有 arXiv 編號、內文也沒有 DOI，會被當成兩篇（例如會議版 vs 期刊版）。
- 補洞用標題比對；標題很短（少於 15 個字母）的參考文獻不會自動補，以免誤配。
- 需要 Python 3.11+（pymupdf4llm 2.1）與 poppler（`pdftotext`、`pdfinfo`）。Windows 上可以用 conda 安裝：`conda install -c conda-forge poppler`。
