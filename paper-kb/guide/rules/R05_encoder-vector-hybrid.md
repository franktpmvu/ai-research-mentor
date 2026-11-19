# R05 向量（RAG）與混合 encoder


## 何時用
- 要做語意比對或模糊搜尋：用詞不同、只記得概念、問句是中文。
- 要修改向量 encoder、換 embedding 模型，或在評估集上比較「全文 vs 向量 vs 混合」。

## 強項與弱項
- 強項：**語意比對、模糊搜尋、跨語言**（中文問句找英文段落）。
- 弱項：「語意相似」不等於「原文有寫」，所以結果一定附原文段落，交給 AI 讀原文確認。

## 目前做法（`src/paper_kb/encoders/vector.py`）
- **embedding**：Ollama（Windows 主機，GTX 1070 8GB）。模型清單在 `config.json` 的 `embed_models`，目前是 `qwen3-embedding:0.6b`、`qwen3-embedding:4b`；第一個是 `semantic_search` 的預設。Ollama 位址用環境變數 `OLLAMA_HOST`（預設 `http://localhost:11434`）。`num_ctx=2048`（段落短，省顯示卡記憶體）。
- **輸入**：FTS5 索引裡的段落，跳過 `kind=reference`；切段單位就是 `para_id`，不另外切塊。送進模型的文字是「論文標題＋章節＋段落」（`EMBED_VERSION = 'title-section-text/v1'`）；查詢加上各模型官方建議的指令前綴（Qwen3：`Instruct: … Query:`；EmbeddingGemma：`task: search result | query:`）。
- **存放**：`data/derived/vectors/<模型>/<doc_id>.npy`（float16、已正規化）＋`<doc_id>.json`（模型、版本、段落數、para_id 清單）。模型、版本、段落數或標題不同就重算（標題會送進模型）；索引裡已刪除的文件會一併刪掉。整個資料夾可以刪掉重建。
- **輸出**：和全文搜尋同格式的 `[{para_id, doc_id, title, page, section, kind, snippet, score, match}]`；原文由 FTS5 的 `paras` 表用 rowid 取回（para_id 欄位沒有索引，逐筆查會掃整張表）。
- **查詢快取**：同一問句的向量只算一次（`query_vec`），vector 和 hybrid 共用。
- **混合**：全文和向量各取前 50 段，用 RRF（k=60）合併；`match` 欄標示來自 fulltext、vector 或兩者。
- **更新**：`update.py` 的「⑥b 向量」步驟，在索引之後執行，只算缺的文件。連不到 Ollama 或沒 pull 模型時印出警告並略過，不讓整個更新失敗。`--no-vector` 可以跳過；`--minutes` 時間到會先停，下次接著算。
- **MCP**：`semantic_search`（見 R06），不改 `search` 的行為。

## 怎麼做
### 換模型或新增模型
1. 在 Windows 上 `ollama pull <模型>`，呼叫一次後用 `ollama ps` 確認 PROCESSOR 是 GPU。
2. 加進 `config.json` 的 `embed_models`；若模型需要特殊前綴，在 `query_text`／`doc_text` 加一個分支。
3. 跑 `maintain.bat`（或 `python update.py`）算向量，再跑 `python eval/run_eval.py` 比較（R07）。

### 改送進模型的文字格式
- 改 `doc_text`，並把 `EMBED_VERSION` 尾碼 +1，所有向量會重算。

### 新增別種 encoder
- 放在 `src/paper_kb/encoders/<名稱>.py`，輸入、輸出格式同上，要有自己的版本常數；接進 `update.py` 和 `eval/run_eval.py`。

## 驗收標準
- 三組方法（全文、向量、混合）在同一評估集上都有數字（R07）。
- `semantic_search` 的每筆結果都能用 `get_paragraphs` 讀回原文。
- 新增文件後跑 update.py，只會對新文件算向量。
- 連不到 Ollama 時，update.py 照常完成，MCP 工具回清楚的錯誤訊息。

## 存放位置
- 程式：`src/paper_kb/encoders/vector.py`
- 向量：`data/derived/vectors/`
- 設定：`config.json` 的 `embed_models`
- 比較結果：`eval/results/`
