# R02 資料收件與更新


## 何時用
- 有新論文（PDF、zip、資料夾、網址）要加進系統。
- Zotero 有新收藏。

## 怎麼做
| 來源 | 做法 |
|---|---|
| PDF／zip／資料夾 | 丟進 `input_raw/inbox/` |
| 網址（arXiv abs/pdf 或 PDF 直連） | 一行一個寫進 `input_raw/url_queue.txt` |
| Zotero | `config.json` 填 `zotero_dir`；只讀不搬，registry 記絕對路徑 |

接著執行（擇一）：
- 一般使用：雙擊 `maintain.bat`（會呼叫 update.py，再做健康檢查，見 R08）。
- 手動：`python update.py --dry-run` 先看會發生什麼，再 `python update.py`。

常用參數：`--workers 2`（每份約 0.7 GB 記憶體）、`--minutes N`、`--doc-timeout 秒數`（預設 300）、`--retry-failed`、`--rebuild`。

### 流程（update.py）
⓪ 下載佇列 → ① 收件到 `batches/YYMMDD_名稱/`（zip 原檔放 `_original/`）→ ② 盤點進 `registry.csv` → ③ 去重（hash、arXiv、DOI）選 canonical → ④ 補 corpus 缺的 PDF → ⑤ 解析（R03）→ ⑥ 索引（R04）→ ⑦ `index_version.json` 版本 +1、寫 `update_log.md`

## 驗收標準
- `data/derived/update_log.md` 最後一段：新文件出現在「解析完成」，失敗數為 0（或失敗原因已記錄）。
- `index_version.json` 的 `version` 增加，`n_canonical` 符合預期。
- 用 `python kb.py list_documents title=<新論文標題片段>` 查得到。
- MCP server 不用重啟（server 每次查詢都會檢查版本號）。

## 已知限制
- 去重只看 hash／arXiv／DOI：會議版和期刊版可能被當成兩篇。
- 補洞用標題比對；少於 15 個字母的標題不自動補。
- 解析需要 `pymupdf4llm`（Python 3.11+）；沒裝會全部記成失敗，要用 `.venv`（Windows）或 `$HOME/kbvenv`（Linux，見 R08）執行。
- 在非 Windows 環境執行時，Windows 磁碟路徑（例如 Zotero 的 `F:/…`）會保留原紀錄、不當作刪除；需要讀取這些檔案的補洞會跳過。

## 存放位置
- 輸入：`input_raw/inbox/`、`input_raw/url_queue.txt`、`input_raw/batches/`
- 參考文獻筆記與 PDF：`corpus/*_refs/`（建置腳本與工作檔在 `corpus/_work/`）
- 產出：`data/derived/registry.csv`、`update_log.md`、`index_version.json`
- 詳細說明：`INGEST.md`
