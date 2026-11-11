# paper-rag-mcp：地端論文知識系統（MCP server）

> **v3（2026-11-10）**：不以向量 RAG 為地基。改成「解析得很好的論文庫＋全文搜尋＋讓 AI 自己讀」。向量檢索是之後視評估結果才加的選配。
> v2（11-05）的切段／embedding／reranker／`find_evidence` 已移除；v1（週末面試版）已作廢。
> 一句話：**底層是論文全文，MCP 提供查詢與閱讀工具，判斷交給 AI。** server 不綁定任何模型。

---

## 1. 要解決的問題

1. **引用核實**：草稿裡一句話加上引用 → 讀被引論文全文 → 找出支持或反駁的原文段落與頁碼。
   - 不需要「檢索」：被引的是哪一篇本來就知道，直接讀那篇最準。
2. **研究記憶延伸**：「我讀過的論文裡，哪些跟 X 有關？」→ 全文關鍵字搜尋找候選，再讀相關頁面。
3. **研究決策回溯**（第二版）：從決策紀錄找出當時的理由。

## 2. 為什麼不用向量 RAG 當地基

- 論文約 250 篇，一篇 1–2 萬 token：AI 一次讀整篇沒問題，讀幾篇也來得及。
- 切段會把論點切碎；「語意相似」不等於「能回答問題」。
- 向量 RAG 要維護切段規則、embedding 模型、向量庫、reranker，出錯點多。
- 研究顯示：資料解析品質是 RAG 效果的主因；自動建的知識圖譜（GraphRAG）比基本 RAG 還差。
- **何時加回向量檢索**：評估集顯示「關鍵字常找不到、但其實有相關內容」時，加成一個新的 MCP 工具即可，其他層不用改。

## 3. 架構

```
          任何 AI（Claude、地端模型…）
                     │ 呼叫工具
┌────────────────────▼─────────────────────┐
│ ④ 查詢層：MCP server（官方 SDK v2）       │
│   search / get_document / get_citations / list_documents
├──────────────────────────────────────────┤
│ ③ 搜尋索引：SQLite FTS5（BM25）            │
│   （選配：向量檢索）                       │
├──────────────────────────────────────────┤
│ ② 解析層：PDF → 每頁、每段有編號的文字     │
├──────────────────────────────────────────┤
│ ① 資料層（唯讀）：收藏、參考文獻、你的論文 │
└──────────────────────────────────────────┘
   update.py：新資料丟進 inbox 就跑（見 INGEST.md）
```

### 設計原則
- **server 只回傳原文**，每段附 `doc_id`、`page`、`para_id`；判斷交給 client 端的 AI。
- **原始資料只搬不改**；衍生資料都在 `data/derived/`，可整個刪掉重建。
- **增量更新**：依檔案 hash 與管線版本（解析器、索引）判斷要重做什麼。
- **全部地端**：不需要 GPU 也能跑（解析器選型時列為條件之一）。

## 4. 資料層（✅ 已完成）

| 類別 | 位置 | 數量 |
|---|---|---|
| 你的論文收藏 | `input_raw/batches/` | 181 個 PDF |
| 參考文獻（你 4 篇已發表論文） | `corpus/*_refs/`（筆記＋`pdf/`） | 158 篇筆記、107 個 PDF |
| 清單 | `data/derived/registry.csv` | 去重後 248 份 canonical |
| 第二版再加 | 自己的論文草稿（tex）、決策紀錄、導師系統（✅ 2026-11-11 已串接：kb_search / kb_read / kb_queue） | — |

## 5. 解析層（✅ 選定 PyMuPDF4LLM 2.1）

- 5 篇不同版型實測（ECCV 單欄、IEEE TPAMI 雙欄、Elsevier、Nature、1997 年舊論文）：
  - 雙欄閱讀順序正確；5 篇都抓到 References；每頁 0.3–1 秒、約 0.7 GB 記憶體、免 GPU。
  - 修正：LaTeX PDF 字黏在一起（依字距補空白）、行尾斷字（同篇有 cross-validation 就保留連字號）、
    Nature 的 Methods 在參考文獻後面（下一個標題就結束參考文獻區）、1997 論文排版順序錯亂（依條目樣式判斷）。
  - 弱點：公式會亂、表頭偶爾被切碎。
- Docling 沒有比完：模型權重放在 `cdn.hf.co`（網路被擋），而且在 VM（2 核、3 GB、無 GPU）上跑 248 份要好幾小時。
  之後要換：寫一個同輸出格式的 `parse_pdf`，改 `PARSER_VERSION`，`update.py` 會自動全部重新解析。
- 輸出：`data/derived/parsed/<doc_id>.json`
  ```json
  {"doc_id": "...", "title": "...", "pages": 12,
   "blocks": [{"para_id": "<doc_id>:p3:2", "page": 3, "section": "3.1 Method", "kind": "text|heading|table|caption|reference", "text": "..."}]}
  ```
- 參考文獻區塊標成 `reference`，搜尋時預設排除（避免搜到「只是被引用」的論文）。

## 6. 搜尋索引（✅）

- SQLite **FTS5**（內建 BM25），一個檔案 `data/derived/index/papers.db`，不用另外架服務。
- 一列一段：`para_id, doc_id, page, section, kind, text`；另一張表放文件 metadata（標題、年份、來源、arXiv、DOI、是否為你的論文）。
- 引用關係表：`citing_doc, cited_doc, context_sentence, section`（已發表論文的部分在 `corpus/_work/` 已抽好）。

## 7. MCP 工具（✅ 官方 Python SDK v2.3：`mcp.server.mcpserver.MCPServer`，stdio）

| 工具 | 輸入 | 輸出 |
|---|---|---|
| `search` | query, k, filters（來源、年份、是否含參考文獻區） | 命中段落＋所屬文件＋頁碼，依文件分組 |
| `get_document` | doc_id, pages（可選）, sections（可選） | 整篇或指定頁／章節的原文，每段附 para_id |
| `get_citations` | doc_id | 誰引用它（引用句、章節）；它引用了誰 |
| `list_documents` | filters | 文件清單與 metadata |

- 工具說明寫明：「回傳的是原文；引用時請附 para_id 與頁碼」。
- 每次查詢前檢查 `data/derived/index_version.json`，版本變了就重新開啟資料庫。

## 8. 評估（用真實任務）

1. **引用核實**：從 AD 草稿挑 20–30 個「主張＋引用」，人工標出正確的支持段落；看 AI 用 `get_document` 能否找到正確頁碼。
2. **搜尋**：20 題「我讀過哪些在講 X」，看 `search` 的 Recall@5（文件層級）。
3. 第 2 項若關鍵字常失敗 → 再評估加入向量檢索。

## 9. 資料夾結構

```
paper-rag-mcp/
├── README.md / PLAN.md / INGEST.md
├── update.py                 # 資料更新流程
├── input_raw/{inbox,batches}/
├── corpus/                   # 參考文獻筆記＋PDF
├── src/paper_kb/
│   ├── ingest/pdf.py         # 解析層
│   ├── index.py              # FTS5 索引
│   ├── citations.py          # 引用關係（讀 corpus 筆記）
│   └── server.py             # MCP server
├── data/derived/             # registry、parsed、index、log（可重建）
├── eval/
└── tests/
```

## 10. 實作順序

1. ✅ 解析器比較 → PyMuPDF4LLM → `src/paper_kb/ingest/pdf.py` → `update.py` ⑤（247/248 份完成）
2. ✅ FTS5 索引 `src/paper_kb/index.py`＋引用關係 `src/paper_kb/citations.py` → `update.py` ⑥
3. ✅ MCP server `src/paper_kb/server.py`（4 個工具，已用 MCP client 實測）→ ⬜ 接上 Claude Desktop（見 README）
4. ⬜ 評估集
5. ⬜ 第二版資料：AD 草稿、決策紀錄、導師系統

## 11. 注意事項
- 公開 repo 只放程式碼；`data/`、`input_raw/`、`corpus/pdf/` 不上傳（PDF 是出版品）。
- MCP SDK v2 的匯入路徑以官方 migration guide 為準；固定版本號。
