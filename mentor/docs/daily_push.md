# 每日主研究軌推播（總流程）

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日排程（完整性檢查之後）。
- 使用者要求「今天就要看」新方向時（見 `redirect.md`），照同一流程走。

## 每日組成（固定）
| 軌 | 篇數 | 細則 |
|---|---|---|
| 主領域 main（CV、LLM、Diffusion 各一） | 3 | `paper_selection.md`、`knowledge_graph.md` |
| 跨域鏡子 xdomain | 1–3（越多越好，至少 1） | `xdomain_mirror.md` |
| 金融鏡子 finance | 1 | `finance_mirror.md` |
| 趣味探索 wild | 3 | `wild_track.md` |

沒有任何放寬情境；使用者沒力氣時走 `light_mode.md`，不是減少推播組成。

## 怎麼做（依序）
0. **完整性**：`integrity.md`。
1. **讀今日計畫**：`python3 mentor.py daily_brief`。
   - 印出：今日想法軸、跨域來源輪轉、金融連結領域、近 7 天黑名單、近 45 天 wild 已推主題、各主領域 🔓 前沿、📍 待處理方向回饋（若有）。
   - 若提示「計畫產生超過 7 天」→ 先 `python3 mentor.py week_plan new`（重排 7 天想法軸輪轉＋黑名單快照，每週一次）。
   - 若有 📍 方向回饋 → 依 `redirect.md` 調整今天的搜尋方向。
   - 「（今日已推）」只在當天 push_log 的 `composition.main >= 3` 時出現；顯示「今日僅有打卡/互動、尚未推論文」→ **照常推播**，不可跳過。
   - 日期一律以 Asia/Taipei 計（程式已固定時區，不必手動處理）。
2. **上網搜尋候選**：依想法軸與跨域來源搜尋近期論文，web search 找到的新論文是主體。選片規則見 `paper_selection.md`。
3. **每篇候選驗重複**：`python3 mentor.py check_dup --title "..." --url "..."` → 🟢CLEAR 才推；🔴HIT 換一篇；🟡 人工確認。
4. **核實文獻**：每篇都要核實出處，見 `refcheck.md`。
5. **主領域守門**：main 三篇先 `kg_add` 入圖再 `kg_check`，見 `knowledge_graph.md`。
6. **寫回導師記憶**：main／xdomain／finance 每篇 `mem_add`（含 rubric、--pid），見 `mentor_memory.md`；wild 不寫。
7. **呈現前預檢**：`push_log --papers "..." --dry`，見 `push_log.md`。未過就換片／補軌，通過才進下一步。
8. **呈現給使用者**：格式見 `presentation.md`。推播本身不放考題。
9. **正式驗收**：`push_log --papers "..."`（不帶 --dry）。
10. **收尾**：`python3 mentor.py mem_consolidate` → `python3 mentor.py learner_state` → `python3 mentor.py snapshot`。
11. **使用者之後回覆 done** → 依 `done_closing.md`。

## 驗收標準
- `push_log`（非 dry）exit 0，且當天 push_log 有一筆 ok=True 的紀錄。
- 使用者看到的每一篇都通過了 `--dry` 預檢（不會看到 LOCKED 論文或未核實文獻）。
- 每天至少出現 1 個使用者記憶裡沒出現過的新概念關鍵詞。

## 存放位置
- 推播紀錄：`push_log.json`（近 30 天）／`push_log_archive.json`。
- 導師記憶：`memory/`；知識圖譜：`kg.json`；週計畫：`week_plan.json`；輪轉基準：`state.json`。
- 全部透過 CLI 讀寫，**不要直接 Read 大 JSON**（token 紀律）。
