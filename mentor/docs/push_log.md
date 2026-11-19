# 推播驗收（push_log）

> 目錄：../CLAUDE.md

## 什麼時候用
- **呈現前**：`--dry` 預檢（不寫檔）。
- **呈現後**：正式驗收（寫檔）。同一天重跑會覆蓋當天的推播清單（保留 light_checkin 留下的打卡標記）。

## 怎麼做
```
python3 mentor.py push_log --papers "pid::main::::<url>||pid2::xdomain::<anchor>::<url>||pid3::finance::<anchor>::<url>||pid4::wild::<標題>::<url>||..." --dry
python3 mentor.py push_log --papers "...同上..."
```
- 每篇格式：`pid::role[::anchor 或 標題][::url]`。
- role ∈ `main`／`xdomain`／`finance`／`wild`／`review`。
- xdomain、finance 第三欄 = anchor（必填）；wild 第三欄 = 標題；**每篇第四欄 url 都要附**。
- 檢視：`push_log --show [N]`。

## 程式會檢查（任何一項失敗 → exit 3）
- 組成：3 main + ≥1 xdomain + 1 finance + 3 wild（沒有放寬情境）。
- xdomain／finance 有 anchor。
- 每篇 main 的 KG 狀態不是 LOCKED／UNKNOWN（`knowledge_graph.md`）。
- 每篇有出處網址且已核實；main 另驗標題（`refcheck.md`）。

## 驗收標準
- `--dry` exit 0 才能呈現給使用者；未過就換掉問題論文或補缺軌再預檢。
- 正式 `push_log` exit 0，當天紀錄 ok=True。

## 存放位置
- `push_log.json`：`{date, papers[pid/role/anchor/url], composition, ok, user_engaged?}`，近 30 天。
- 超過 30 天由 `mem_consolidate` 自動搬到 `push_log_archive.json`（`check_dup` 仍會掃）。
