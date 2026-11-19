# R07 評估


## 何時用
- 建立評估集、改了解析器或 encoder 之後、比較 encoder。

## 原則
- **題目用真實問題**：從使用者在 `atomic_habit` 對話裡實際問過的問題擷取，而不是另外編題目。
- **不需要事先知道答案**：用「候選池＋標註」的方式，先讓各 encoder 搜尋，再標出搜到的結果是否相關（TREC 的 pooling 做法）。
- **找不到答案的題目也保留**：標成「語料裡沒有答案」，用來檢查系統會不會亂給結果。
- 所有 encoder 在同一份評估集上比較。

## 怎麼做
1. **擷取問題**：
   - 來源：mentor 的 `journal/*.md` 的「使用者原始互動（逐字）」段落，每行 `> ` 是一句。
   - 原樣全部抽出 → `eval/questions_raw.jsonl`（不篩選）。
   - 篩選「想找資料、有疑問」的句子；陳述、作答、確認、閒聊不收 → `eval/questions.jsonl`：
   ```json
   {"id": "q0093", "query": "原句", "kind": "lookup|concept|survey",
    "query_sem": "中文語意問句", "query_sem_en": "英文語意問句",
    "source": "journal 檔名", "turn": 2, "topic": "...", "domain": "...",
    "context_doc_id": "當時討論的論文", "context_title": "...", "query_anchored": "在《標題》這篇論文中：原句",
    "answerable": null}
   ```
   - **錨點**：原句常省略前提（例如「Phi 是可訓練的嗎」，phi 在幾百篇論文都有）。每題記下當時討論的論文（`context_doc_id`），從閱讀紀錄的 journal 欄位或標題比對而來；找不到的填 null。
   - **語意問句**（`query_sem`、`query_sem_en`）：把原句補上前文，改寫成單獨看也有意義的問題，例如「diffusion 中原本要一步步走的方法，為什麼能少步甚至一步到位？」
     - 可以用：領域和一般概念（diffusion、attention、softmax、物件偵測…）。
     - 不能用：目標論文的標題、它自己命名的方法或縮寫（DDIM、FlashAttention、ToMe…），否則等於把答案放進題目。
     - 寫完用程式比對「目標論文標題的字」有沒有出現在問句裡，命中的逐題判斷是一般用詞還是洩漏。
   - `kind`：lookup＝答案在某篇論文裡；concept＝概念推理，未必有原文可查；survey＝找一批相關論文。
   - **兩種任務分開評估**：
     | 任務 | 答案是 | 用哪些問句版本 | 指標 |
     |---|---|---|---|
     | A. 跨文件：「我讀過哪篇在講 X？」 | 論文 | raw、query_sem、query_sem_en（**不可含論文或方法名稱**） | 文件層級＋段落層級 |
     | B. 文件內：「這篇裡哪一段在講 X？」 | 段落 | query_anchored，或任一版本加 `doc_ids=[context_doc_id]` | **只算段落層級**（論文是已知前提，算文件層級沒有意義） |
   - 對話裡討論的論文若不在知識庫，把網址加進 `input_raw/url_queue.txt`；不是 arXiv／PDF 直連的，要手動下載 PDF 放進 `input_raw/inbox/`。
2. **建候選池**：`python eval/build_pool.py [--depth 5]`（需要 Ollama）。每題 × 3 種問句 × 每個 encoder（全文、各模型的向量與混合），任務 A 在全部文件裡搜、任務 B 只在 context_doc_id 裡搜，各取前 depth 段，聯集寫進 `eval/pool.jsonl`（附原文與「被誰找到、排第幾」）。同一個（題目, 段落）只標一次，兩種任務共用；qrels 裡已標過的不會再列出。
3. **標註**：候選池裡每段標相關程度，寫進 `eval/qrels.jsonl`：
   ```json
   {"id": "q001", "para_id": "<doc_id>:p5:3", "rel": 2, "by": "llm|user"}
   ```
   - `rel`：0＝不相關、1＝部分相關、2＝直接回答。
   - 先用地端 LLM 預標：`python eval/llm_label.py [--sample 50] [--model qwen3:8b]`（Ollama；temperature 0、JSON 輸出；給模型看中英文語意問句、原句、段落出處與原文；可中斷續標）。`by` 記成 `llm:<模型>`，附一句理由。
   - **證據檢查**：給 1、2 分時模型必須從段落原文複製一句當 `evidence`，程式檢查這句真的在段落裡，不在就降為 0 分（原分數留在 `llm_rel`），擋掉「問題裡有的詞就以為段落裡也有」的錯誤。
   - 再抽查：先用 `--sample` 試標一小批，由 Claude（或使用者）獨立標同一批，算一致率；一致率夠高才標全部，抽查改過的那筆把 `by` 改成 `claude` 或 `user`。
4. **沒有答案的題目**：候選池全部是 0 的題目，在 `questions.jsonl` 加上 `"answerable": false`。
5. **跑評估**：`python eval/run_eval.py`（全文＋`config.json` 所有 embed_models 的向量與混合；`--models a,b` 指定模型；`--no-vector` 只跑全文），直接呼叫 encoder，不經過 AI。
   - 還沒有 qrels 時，跑的是**代理評估**：以 `context_doc_id` 為唯一正確文件，只算任務 A 文件層級（Hit@5、Hit@10、MRR@10），結果寫到 `eval/results/YYMMDD_proxy_taskA.md`。
   - 有答案的題目：nDCG@10、Recall@10、MRR（文件層級和段落層級都算）。
   - 沒有答案的題目：最高分結果的分數分布，用來設定「找不到」的門檻。
6. **加入新的 encoder 時**：它搜到、但還沒標過的段落要先補標，再比較分數（否則對新 encoder 不公平）。
7. 每次執行的結果寫成 `eval/results/YYMMDD_<encoder>.md`：日期、`index_version`、各管線版本、指標、表現最差的題目清單。

## 驗收標準
- 每個數字都查得到出處：結果檔名＋index_version＋管線版本。
- 同一設定重跑，數字相同。
- `qrels.jsonl` 裡寫明哪些是 LLM 標的、哪些是使用者確認過的。

## 存放位置
- 題目：`eval/questions_raw.jsonl`（全部原句）、`eval/questions.jsonl`（篩選後）；標註：`eval/qrels.jsonl`（含個人內容，不上傳公開 repo）
- 程式：`eval/run_eval.py`、`eval/build_pool.py`、`eval/llm_label.py`
- 結果：`eval/results/`

## 目前狀態（2026-11-19）
- 42 份對話 → 184 句原句 → 篩出 63 題（lookup 47、concept 12、survey 4）。
- 閱讀紀錄 71 篇中，原本只有 9 篇在庫；已新收 36 篇（index_version 21），另有少數要手動下載（見 R08）。
- 60/63 題有錨點論文（另 3 題的論文是新聞稿或部落格，不在庫）。
- 全文 BM25 的代理比較（`eval/results/261118_fulltext_anchor_proxy.md`，任務 A、當時那篇在前 5）：原句 6/60、中文語意問句 1/60、英文語意問句 42/60 → 跨語言是向量 encoder 要補的主要缺口。
- 代理評估（`eval/results/261119_proxy_taskA.md`，當時那篇在前 5／60）：
  | | 全文 | 向量 0.6b | 向量 4b | 混合 4b |
  |---|---|---|---|---|
  | 原句 | 6 | 28 | 42 | 38 |
  | 中文語意 | 1 | 41 | 51 | 50 |
  | 英文語意 | 42 | 50 | 49 | 49 |
- 失敗分析：Nash 1950 是掃描檔（已 OCR 補上，全文英文語意問句排第 1）；7 份文件標題抓錯（已用 title_overrides 修正）；q158／q159／q161 是一般概念題，答案不一定在當時那篇；其餘多半是其他論文也相關（代理指標的限制）。
- 候選池：2,430 段（depth 5）。
- 試標 v1（qwen3:8b，50 筆，沒有證據檢查）vs Claude 獨立標註（`eval/qrels_claude_trial.jsonl`）：完全一致 40/50、相關與否一致 42/50、kappa 0.55。8b 的主要錯誤是把問題裡的詞當成段落裡有（例如段落沒提 LoRA 卻說有）→ 加上證據檢查。
- 下一步：用證據檢查版重標同一批 50 筆（`--out eval/qrels_trial_v2.jsonl`）→ 再比一致率 → 決定是否標全部 2,430 段。
