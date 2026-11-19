# R01 專案目標與架構


## 何時用
- 開始任何新功能之前；判斷一個改動屬於哪一層。

## 目標
做一個 **MCP server＋可替換 encoder** 的搜尋系統。目前的內容是論文，但骨架不限論文。
- encoder 可以是全文搜尋、RAG（向量），也可以是其他技術，而且可以同時並存：
  - 全文搜尋的強項：**真實來源**，命中的字一定在原文裡。
  - RAG 的強項：**語意比對、模糊搜尋**，用詞不同也找得到。
- 現有的程式（解析、FTS5 全文、5 個 MCP 工具、update.py）就是這個專案的起點，在它上面繼續做。

## 架構分層
```
        任何支援 MCP 的 AI（Claude、地端模型…）
                     │
④ 查詢層  MCP server（src/paper_kb/server.py）          → R06
③ 檢索層  encoder（可替換、可並存）                      → R04 全文、R05 向量／混合
② 解析層  原始文件 → 有 para_id 的段落 JSON               → R03
① 資料層  原始檔（唯讀）＋ registry                       → R02
```

## 設計原則（每次改動都要遵守）
1. **結果一律對應回原文**：任何 encoder 的結果都要對應回 `para_id`（格式 `<doc_id>:p<頁>:<段>`）與頁碼；server 回傳原文段落，不回傳 embedding 或摘要。
2. **server 不做判斷**：只回傳原文與定位，摘要、推論交給 client 端的 AI。
3. **encoder 可替換、可並存**：每個 encoder 只吃「② 解析層的段落」，只吐出「para_id＋分數」。新增 encoder 不改 ①②④ 的資料格式。
4. **骨架不限論文**：新類型的資料只要寫一個輸出同樣段落 JSON 的解析器，就能用同一套 encoder 和 MCP 工具。
5. **原始資料只搬不改**；衍生資料全部放 `data/derived/`，可以整個刪掉重建。
6. **增量更新**：靠檔案 hash 和各層的版本常數（`PARSER_VERSION`、`INDEX_VERSION`，以及各 encoder 自己的版本常數）判斷要重做什麼。
7. **全部地端、不需要 GPU**（目前執行環境：VM 2 核、3 GB；Windows 主機）。
8. **用評估比較 encoder**：各 encoder 在同一份評估集上比較（R07），用結果決定預設用哪個或怎麼組合。

## 驗收標準
- 新功能說得出屬於哪一層，而且沒有破壞上面 8 條。
- 任何搜尋結果都能用 `get_paragraphs` 讀回原文。

## 存放位置
- 程式：`src/paper_kb/`（`ingest/` 解析、`index.py` 全文、`citations.py` 引用關係、`server.py` MCP）
- 流程腳本：`update.py`、`maintain.py`、`maintain.bat`、`kb.py`（命令列 client）
- 早期設計紀錄：`PLAN.md`（和本細則衝突時以本細則為準）
