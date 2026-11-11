# paper-kb：地端論文知識庫（MCP server）

你讀過、收藏的論文全文＋你已發表論文的參考文獻與引用原句，包成 5 個 MCP 工具，任何支援 MCP 的 AI 都能用。
設計與理由見 [PLAN.md](PLAN.md)；新資料怎麼加見 [INGEST.md](INGEST.md)。

## 工具

| 工具 | 用途 | 例子 |
|---|---|---|
| `search` | 全文關鍵字搜尋（BM25），依文件分組，附頁碼與 para_id | `search("mouse grimace scale pain")` |
| `get_document` | 讀原文：整篇、指定頁、指定章節，或只看章節大綱 | `get_document("2203.11991", pages=[5,6])` |
| `get_paragraphs` | 依 para_id 讀指定段落，可帶前後文（核實引用用） | `get_paragraphs(["b0b8069bedbb:p8:1"], window=1)` |
| `get_citations` | 你的論文引用了誰、某篇被你哪篇引用、引用原句、你的 note | `get_citations(query="SiamFC")` |
| `list_documents` | 列出文件（可依標題、來源、是否為你的論文過濾） | `list_documents(mine=True)` |

server 只回傳原文與定位，不做摘要或判斷。

## 最簡單的用法（Windows）：雙擊 `maintain.bat`

| 要做的事 | 指令（在專案資料夾執行，或雙擊） |
|---|---|
| 第一次安裝＋更新資料＋健康檢查 | 雙擊 `maintain.bat`（第一次會自動建立 `.venv` 並安裝套件；需要 Python 3.11+） |
| 接上 Claude Desktop | `maintain.bat --install-claude`（會先備份原設定） |
| 每週自動維護 | `maintain.bat --schedule weekly`（取消：`--schedule off`） |
| 只做健康檢查 | `maintain.bat --check` |

- 新論文丟進 `input_raw/inbox/`，下次維護就會自動收件、去重、解析、索引。
- 也可以把論文網址（arXiv 或 PDF 直連）一行一個寫進 `input_raw/url_queue.txt`，維護時會先下載（導師系統的 `kb_queue` 就是寫這個檔）。
- 個人設定（哪些是你自己的論文）放 `config.json`，範本見 `config.example.json`；沒有也能跑。
- 每次結果寫在 `data/derived/health.md`（最新一次）和 `maintain_log.md`（歷史）。
- 不需要 poppler 了：沒有的話改用 pymupdf 盤點。

以下是手動安裝的方式，用 `maintain.bat` 的話可以跳過。

## 安裝（只是要「用」server）

server 只需要 Python 3.10+ 和 `mcp`，不需要解析器：

```bash
pip install "mcp>=2.3,<3"
```

### 接上 Claude Desktop（Windows）

編輯 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "paper-kb": {
      "command": "python",
      "args": ["-m", "paper_kb.server"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\paper-kb\\src"
      }
    }
  }
}
```

- `command` 要指到裝了 `mcp` 的那個 Python。用 conda 的話寫完整路徑，例如 `C:\\Users\\<你>\\miniconda3\\envs\\kb\\python.exe`。
- 改完重開 Claude Desktop，對話框的工具清單應該會出現 paper-kb 的 4 個工具。

### 其他 client
任何支援 stdio MCP server 的 client 都一樣：指令 `python -m paper_kb.server`，環境變數 `PYTHONPATH=<專案>/src`。
資料放在別處時，可以加 `PAPER_KB_ROOT=<專案根目錄>`。

### 測試（不用 client）
```bash
npx @modelcontextprotocol/inspector python -m paper_kb.server   # MCP Inspector，網頁上逐一試工具
```

## 安裝（要「更新」資料：跑 update.py）

```bash
pip install -r requirements.txt     # pymupdf4llm 2.1 需要 Python 3.11+
python update.py --workers 2
```
poppler（`pdfinfo`、`pdftotext`）可有可無：有就優先用，沒有就改用 pymupdf。

## 已知限制
- 搜尋是關鍵字比對：要用論文裡會出現的英文字。同義詞不會自動擴充，例如搜 "occlusion" 找不到只寫 "blocked" 的段落。之後評估若常漏掉，再加向量檢索工具。
- 公式辨識不好（PyMuPDF4LLM 不做公式 OCR），數學式會亂。
- 表格轉成 markdown；表頭有時會被切碎。
- 少數掃描檔若沒有文字層，目前不做 OCR，內容會是空的。
- 索引放在 VM 共用的資料夾時，SQLite 用獨占鎖＋記憶體日誌（掛載磁碟不支援一般的檔案鎖）。寫到一半當掉的話，跑 `python update.py --rebuild` 重建。

## 公開 repo
只放程式碼。`data/`、`input_raw/`、`corpus/`、`config.json` 不上傳（PDF 是出版品；corpus 與 config 是個人資料）。
