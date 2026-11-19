# R04 全文搜尋 encoder（SQLite FTS5／BM25）


## 何時用
- 要查「原文裡確實出現這些字」的段落：引用核實、找精確術語、找出處。
- 要調整斷詞、排序、索引欄位。

## 強項與弱項
- 強項：**真實來源**。命中的字一定在原文裡，可以精確定位到頁碼和段落。
- 弱項：同義詞找不到（搜 occlusion 找不到只寫 blocked 的段落）；只能用英文關鍵字。

## 目前做法
- `src/paper_kb/index.py`，`INDEX_VERSION = 'fts5-porter/v5'`，tokenizer：`porter unicode61 remove_diacritics 2`。
- 一個檔案：`data/derived/index/papers.db`
  - `paras`（FTS5）：`text, section, alt`；`para_id, doc_id, page, kind, seq` 不索引。`alt` 放斷字合併後的替代文字。
  - `docs`：doc_id、title、path、source（collection／corpus）、mine、arxiv、doi、pages、n_paras。
  - 引用關係表（由 `citations.py` 建立）。
- 查詢：先找「所有字都出現」的段落，不足 k 筆再放寬成「任一字出現」；支援 FTS5 語法（片語、AND／OR／NOT、NEAR、前綴*）。

## 怎麼做（修改時）
1. 改 `index.py`，`INDEX_VERSION` 尾碼 +1。
2. `python update.py`：只會重新索引（約 30 秒），不會重新解析。
3. 用 `python kb.py search query="..." k=5` 抽查，再跑評估（R07）。

## 驗收標準
- 評估集的 Recall@5 不比上一版低（R07）。
- 每筆結果都有 `para_id`、頁碼、章節，`get_paragraphs` 讀得回原文。
- 掛載磁碟上不會鎖死（目前用獨占鎖＋記憶體日誌；壞了用 `python update.py --rebuild` 重建）。

## 存放位置
- 程式：`src/paper_kb/index.py`、`src/paper_kb/citations.py`
- 索引：`data/derived/index/papers.db`
