# R00 指引維護與同步


## 何時用
- 要新增、修改、刪除任何一條細則或目錄時。
- 發現 README／PLAN／INGEST 和細則不一致時。

## 結構
```
paper-rag-mcp/
├── CLAUDE.md                 # 目錄（索引），每件事一行：「要做的事 → 請至 xxx.md」
└── guide/
    ├── rules/RNN_<名稱>.md   # 細則：只寫目前最新的規則
    └── changelog/RNN_<名稱>.log.md   # 每條細則一份變更紀錄
```

## 怎麼做
1. **改細則**：直接改 `guide/rules/` 裡的檔案，讓它只呈現最新規則，不留「舊做法」「已廢除」之類的文字。
2. **寫變更紀錄**：在對應的 `guide/changelog/RNN_….log.md` **最上面**加一筆：
   ```
   ## YYYY-MM-DD
   - 改了什麼：…
   - 為什麼：…
   - 誰決定：使用者／Claude 提議、使用者同意
   ```
3. **新增細則**：編號接續（R11、R12…），同時建 rules 和 changelog 兩個檔，並在 `CLAUDE.md` 目錄表加一行。
4. **刪除細則**：從目錄移除那一行；rules 檔移到 `guide/changelog/_retired/`，changelog 寫明原因。
5. **同步兩邊**（每次改完都要做）：
   - 本機：專案根目錄。
   - 雲端：claude.ai Project「rag_paper_proj」的文件。`guide/rules/…`、`guide/changelog/…` 路徑與本機相同；目錄在雲端是 `claude/CLAUDE.md`（雲端會把根目錄的檔名自動放進 `claude/`）。
   - 本機是主版本。雲端有人改過時，先合併回本機，再整份覆寫回雲端。
6. 既有文件（README／PLAN／INGEST）和細則衝突時，修正那份文件，並在相關細則的 changelog 記一筆。

## 驗收標準
- 目錄裡的每一行都指向一個存在的細則檔；每個細則檔都有對應的 changelog。
- 細則裡沒有歷史敘述；歷史只出現在 changelog。
- 本機和雲端的檔案清單、內容一致（逐檔比對）。

## 存放位置
- 目錄：`CLAUDE.md`
- 細則：`guide/rules/`
- 變更紀錄：`guide/changelog/`（已退役的細則：`guide/changelog/_retired/`）
