# 知識圖譜·先修守門（kg）

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日推播：main 三篇**每一篇**推薦前。
- 搜到任何新的主領域論文、決定 `mem_add` 時（同時入圖）。
- 跨域／金融論文 `mem_add` 時（以 spontaneous 入圖）。
- wild 軌**不進圖譜**。

## 核心概念
- **節點**：每個論文／概念一個 node（key=pid），欄位 `{title, domain, level, prereqs[], spontaneous, url, note}`。
- **通過**：該 pid 有 depth≥2 的 review pass（程式由 episodic 自動推導，不需手記）。
- **前沿 frontier**：尚未通過、但先修全部通過的節點 = 主領域推薦的天花板。

## 怎麼做
1. 主領域新論文：依它的**引用與概念依賴**接上先修邊：
   `python3 mentor.py kg_add --id <pid> --title "..." --domain <cv|llm|diffusion> --prereqs "a||b" [--level N]`
   - 真的找不到先修 → 加 `--entry` 標為入門節點（不加會被警告，避免靜默繞過守門）。
2. 守門：`python3 mentor.py kg_check --id <pid>`
   - 🟢 FRONTIER／OPEN → 可推。
   - 🔴 LOCKED（exit 3）→ **禁止跳推**，改推它的先修前沿（`daily_brief` 已列各領域 🔓 前沿，或 `kg_frontier <domain>`）。
   - ⚠ UNKNOWN（exit 2）→ 還沒入圖，先做第 1 步再判。
3. 跨域／金融：`kg_add ... --spontaneous` → 豁免先修守門（kg_check 回 🟢 OPEN），保留跳躍自由。
4. 其他：`kg_link --id <p> --prereqs "a||b" [--remove]` 增刪先修邊；`kg_show [domain]` 樹狀看進度；`kg_seed` 只在首次建骨幹用。

## 驗收標準
- main 三篇在 `push_log --dry` 都不是 LOCKED／UNKNOWN（push_log 會程式化再驗一次，失敗 exit 3）。
- `integrity` 的跨檔參照檢查通過（沒有孤兒先修 slug、主領域節點不是「無先修又未標入門」）。

## 存放位置
- `kg.json`（累積資產，不重置）。
