# R06 MCP 工具


## 何時用
- 要用、測試、修改或新增 MCP 工具；要接上 Claude Desktop 或其他 client。

## 目前的工具（`src/paper_kb/server.py`，官方 Python SDK `mcp>=2.3,<3`，`MCPServer`，stdio）
| 工具 | 用途 |
|---|---|
| `search(query, k=10, include_references=False, source=None, doc_ids=None)` | 全文 BM25 搜尋，依文件分組，附 para_id、頁碼、章節 |
| `semantic_search(query, k=10, mode='vector', model=None, source=None, doc_ids=None)` | 語意搜尋（向量 RAG，需要 Ollama）；`mode='hybrid'` 用 RRF 合併全文與向量；中文問句也可以 |
| `get_document(doc_id, pages, section, outline_only, include_references, max_chars=60000)` | 讀原文（整篇／指定頁／章節／只看大綱）；doc_id 也接受 arXiv、DOI、筆記編號 |
| `get_paragraphs(para_ids, window=0)` | 依 para_id 讀段落，可帶前後文（核實引用用） |
| `get_citations(doc_id, query)` | 使用者的論文引用了誰、被誰引用、引用原句、note |
| `list_documents(title, source, mine, limit, offset)` | 列出文件 |

建議的使用流程（已寫進 server 的 instructions）：search 找候選 → get_document／get_paragraphs 讀原文 → 回答時附 para_id 與頁碼。

## 怎麼做
### 使用、測試
- 命令列：`python kb.py tools`、`python kb.py search query="mouse grimace scale" k=5`
- 網頁介面：`npx @modelcontextprotocol/inspector python -m paper_kb.server`
- 接上 Claude Desktop：`maintain.bat --install-claude`（會先備份原設定），然後重開 Claude Desktop。

### 修改或新增工具
1. 工具只回傳原文與定位，不做摘要或判斷（R01 原則 1、2）。
2. 每筆結果都要有 `doc_id`、`para_id`、`page`。
3. docstring 寫清楚每個參數，以及「片段只是線索，要讀原文確認」。
4. 參數用簡單型別（str、int、bool、list）；新 encoder 用新的工具，不改既有工具的行為（R05）。
5. 改完用 `kb.py` 和 Inspector 都測過，再同步更新 README 的工具表。

## 驗收標準
- `python kb.py tools` 列得出所有工具，每個都呼叫成功。
- 跑完 update.py 不用重啟 server，下一次查詢就是新資料（版本號檢查）。
- Claude Desktop 的工具清單看得到 paper-kb。

## 已知問題
- README 的工具表和「接上 Claude Desktop」段落還沒更新：實際是 6 個工具（含 `semantic_search`）。

## 存放位置
- server：`src/paper_kb/server.py`；命令列 client：`kb.py`
- Claude Desktop 設定：`%APPDATA%\Claude\claude_desktop_config.json`
