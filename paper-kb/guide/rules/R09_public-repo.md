# R09 公開 repo 與隱私


## 何時用
- 建立或推送公開 GitHub repo、寫公開 README。

## 規則
- **只放程式碼和說明文件。**
- 不上傳（已在 `.gitignore`）：`data/`、`input_raw/`、`corpus/`（含 `_work/`）、`config.json`、`.venv/`、`__pycache__/`。
- 還要加進 `.gitignore`：`models/`、`eval/questions_raw.jsonl`、`eval/questions.jsonl`、`eval/qrels.jsonl`、`eval/results/`（含個人內容；repo 另放示範題）。
- 不能出現個資：本機路徑（`F:\…`、`C:\Users\…`）、Zotero 路徑、使用者論文清單（`config.json` 的 `mine`）。
- `config.example.json` 只能放假資料。
- `guide/`、`CLAUDE.md` 可以公開（裡面不要寫個資；本機路徑只寫在 R00，推送前改成相對說明或移除）。

## README
- **第一個畫面**要有：架構圖、評估結果（R07 的數字＋出處）。

## 怎麼做
1. `git status` 和 `git ls-files` 確認沒有 PDF、db、json 資料檔。
2. `grep -rn "F:\\\\\|C:\\\\Users\|Zotero" --include=*.md --include=*.py --include=*.json .` 找出個資。
3. 第一次推送前，請使用者確認檔案清單。

## 驗收標準
- repo 裡沒有任何 PDF、資料庫、解析結果或個人設定。
- 從零 clone，照 README 能安裝並跑起 server（用空的資料也能啟動）。

## 存放位置
- 規則：`.gitignore`；公開說明：`README.md`
