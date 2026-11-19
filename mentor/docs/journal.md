# 瑣碎記憶：逐字保存對話（journal_add）

> 目錄：../CLAUDE.md

## 什麼時候用
- 使用者有實質互動（deep 作答、機制辯證、提出想法／質疑），在 `review` 與記憶更新之後。
- 日常推播若使用者沒回話 → 略過。

## 怎麼做
```
python3 mentor.py journal_add \
    --user "使用者原話1||使用者原話2||..." \
    --mentor "導師這次的回應／裁決摘要" \
    --tag <短標籤> --domain <cv|llm|diffusion> --title "一句主題"
```
- `--user` **逐字保留**，不改寫、不摘要。
- 檢視：`python3 mentor.py journal_list`。
- 分工：`mem_add`／`review` 萃取要點；`journal_add` 保存原礦。兩者都要做。

## 驗收標準
- `journal/` 多一個檔，內容裡的使用者原話與對話一字不差。
- `paper_xlsx` 的 C 欄、M 欄能從這個 journal 擷取到原話（`paper_xlsx.md`）。

## 存放位置
- `journal/YYYY-MM-DD_HHMMSS_<tag>.md`（自動命名，內嵌記憶快照）。只累積，不刪。
