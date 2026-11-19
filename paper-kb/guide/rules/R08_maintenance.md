# R08 日常維運


## 何時用
- 定期更新、檢查系統是否健康、排除故障。

## 怎麼做（Windows，在專案資料夾）
| 要做的事 | 指令 |
|---|---|
| 安裝＋更新＋健康檢查 | 雙擊 `maintain.bat`（第一次會自動建 `.venv`，需要 Python 3.11+） |
| 只做健康檢查 | `maintain.bat --check` |
| 接上 Claude Desktop | `maintain.bat --install-claude` |
| 每週自動維護 | `maintain.bat --schedule weekly`（取消：`--schedule off`；工作排程器名稱 `paper-kb-maintain`） |

- 一定要用 `.venv` 的 Python 執行（否則可能缺 `pymupdf4llm`，全部解析失敗）。
- 向量（R05）：維護前先開著 Ollama（裝好後通常常駐在背景）。沒開的話 update.py 會略過向量並警告，下次再算。第一次要算全部約 6.5 萬段，之後只算新文件。
- 同時只能跑一個維護：用 `data/derived/.maintain.lock` 鎖住。確定沒有在跑卻一直被擋時，才手動刪除這個鎖檔。

## 在 Claude 的 Linux 環境執行（不經過 Windows）
- 環境：Python 3.11 venv 在 `$HOME/kbvenv`（用 `uv` 安裝；VM 內建的 3.10 不能裝 pymupdf4llm 2.1）。
- 這個環境連不到 arXiv（proxy 403）：論文改由雲端工作區從 `export.arxiv.org` 下載後放進 `input_raw/inbox/`；超過約 40 MB 的檔案傳不過去，網址留在佇列，給 Windows 的 `maintain.bat` 下載。
- 背景程式會在該次呼叫結束時被終止 → 用前景分段跑：`timeout 175 $HOME/kbvenv/bin/python update.py --workers 2 --minutes 1.5`，重複到「解析完成」沒有剩餘為止。
- Zotero 等 Windows 路徑（`F:/…`）在 Linux 讀不到：update.py 會保留原紀錄、不當作刪除，補洞也會跳過，留給下次在 Windows 執行。

## 故障處理
| 症狀 | 處理 |
|---|---|
| 解析失敗 `ModuleNotFoundError` | 改用 `maintain.bat` 或 `.venv\Scripts\python.exe update.py` |
| 單份逾時 `TIMEOUT` | `python update.py --retry-failed --doc-timeout 1200` |
| 索引壞掉、資料庫鎖住 | `python update.py --rebuild` |
| health.md 和 index_version 對不上 | 重跑 `maintain.bat --check` |

## 驗收標準
- `data/derived/health.md` 是最新日期；PDF 數、canonical 數、索引文件數和 `index_version.json` 一致；「MCP server：可載入」。
- 警告（⚠️）都有處理方式，或已記錄為已知限制。

## 存放位置
- 程式：`maintain.py`、`maintain.bat`
- 紀錄：`data/derived/health.md`（最新一次）、`maintain_log.md`（歷史）、`update_log.md`
- `data/derived/_to_delete/`：舊盤點檔，可以整個刪掉

## 目前狀態（2026-11-18）
- `index_version` 22：377 個 PDF、323 份 canonical、322 份已索引、65,436 段（LNCS 論文集逾時）。
- `health.md` 已更新（17:00）；Claude Desktop 兩個設定檔都已接上 paper-kb。
- `url_queue.txt` 已清空（Windows 端可以直接下載 Linux 環境被擋的網址）。
