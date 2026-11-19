# R03 解析層


## 何時用
- 解析結果有問題（斷字、雙欄順序、參考文獻區判斷錯）。
- 要換解析器，或要支援論文以外的文件類型。

## 目前做法
- 解析器：PyMuPDF4LLM 2.1，`src/paper_kb/ingest/pdf.py`，`PARSER_VERSION = 'pymupdf4llm-2.1/v2'`。
- 輸出格式（**所有解析器都必須遵守**）：`data/derived/parsed/<doc_id>.json`
  ```json
  {"doc_id": "...", "title": "...", "pages": 12,
   "blocks": [{"para_id": "<doc_id>:p3:2", "page": 3, "section": "3.1 Method",
               "kind": "text|heading|table|caption|reference", "text": "..."}]}
  ```
- 參考文獻區的段落標成 `kind=reference`，搜尋時預設排除。

## 怎麼做
### 修改解析規則
1. 改 `pdf.py`，並把 `PARSER_VERSION` 的尾碼 +1（例如 `/v3`）。
2. 先挑 3–5 篇不同版型（單欄、雙欄、Elsevier、Nature、舊論文）手動檢查輸出。
3. 跑 `python update.py`：版本不同的文件會自動全部重新解析與索引。

### 換解析器或加新文件類型
1. 新寫一個模組（例如 `ingest/docling.py`、`ingest/tex.py`），提供 `parse_xxx(path, doc_id)`，輸出上面的格式。
2. 在 `update.py` 的解析步驟依副檔名或來源分派。
3. 設定新的版本常數，讓 update.py 判斷要重做哪些。
4. 限制：VM 擋 `cdn.hf.co`，需要下載模型權重的解析器（如 Docling）要先確認裝得起來。

### 標題抓錯時
- 自動抓的標題有時是章節名、檔名或摘要（例如「2. Model architecture」「# YOLOv4.pdf」）。在 `config.json` 的 `title_overrides` 加上 `doc_id → 正確標題`，update.py 每次索引後會套用；向量會因為標題改變而自動重算（R05）。
- 檢查方法：列出 `docs` 表中標題太短、以數字或 Abstract 開頭、以 .pdf 結尾的文件。

### 掃描檔（沒有文字層）
- 解析器不做 OCR，掃描檔的段落數會是 0。處理方式：用 Linux 環境的 tesseract＋pymupdf 產生有文字層的副本（每頁 `get_pixmap(dpi=300)` → `pdfocr_tobytes(language='eng')`），存成 `<原檔名>_ocr.pdf` 放進 `input_raw/inbox/`，再跑 update.py。原檔不動（只搬不改），在 `title_overrides` 註明它是掃描檔。
- Windows 端沒有裝 tesseract，所以這一步在 Claude 的 Linux 環境做（R08）。

## 驗收標準
- 抽查的文件：閱讀順序正確、References 有被標成 `reference`、`para_id` 連續且唯一。
- `update_log.md` 沒有新增的解析失敗；舊的 `ERR`／`TIMEOUT` 數量不增加。
- 對評估集（R07）的分數不下降。

## 已知限制
- 公式辨識差（不做公式 OCR）；表頭偶爾被切碎；掃描檔要另外 OCR（見上）。
- 已處理的掃描檔：Nash 1950《The Bargaining Problem》（原檔 2819cd077194 無文字；OCR 版 64404b024814）。
- `LNCS13256_IbPRIA2022_proceedings.pdf`（整本論文集）超過時間限制。要處理的話用 `python update.py --retry-failed --doc-timeout 1200`。

## 存放位置
- 程式：`src/paper_kb/ingest/`
- 產出：`data/derived/parsed/`
