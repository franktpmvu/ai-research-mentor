# 導師記憶（層級時間記憶＋rubric）

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日推播：main／xdomain／finance 每篇寫回記憶（wild 不寫）。
- 每日收尾：`mem_consolidate`。
- 要看記憶脈絡：`mem_context`、`mem_view [layer]`。

## 五層結構
```
week（7 天）→ month（30 天）→ half_year（182 天）→ year（365 天）→ long_term（永久）
```

## 怎麼做
1. **寫入**（同時寫審查 rubric，你就是評分器）：
   ```
   python3 mentor.py mem_add --title "正式標題" --domain <cv|llm|diffusion> --url <網址> \
       --summary "..." --importance <1-10> --pid <slug> \
       --rubric "點1||點2||點3" --questions "問1||問2"
   ```
   - 寫入前程式會強制核實標題與網址，未過 exit 5、不寫入（`refcheck.md`）。
   - 新論文進 week 層；再次遇到同一篇 → 再 `mem_add` 一次就會強化（seen_count+1、importance 取大）。
   - 趨勢用 `trend_add`。
2. **鞏固**：`python3 mentor.py mem_consolidate`（每日收尾跑一次；同時做歸檔輪替）。
   - 升層資格：seen_count≥2，或學習者已通過該篇，或 importance≥8。
   - 停留條件：在目前層至少待滿該層窗口的一半（week 層至少 3 天）；importance 高只是資格，不能免除停留。
   - long_term 入口：（學習者通過 且 importance≥8）或 seen_count≥3。
   - 每次最多升一層；過期且不重要者淡出到 `memory/archive.json`（不刪除）。

## 驗收標準
- 每篇 main／xdomain／finance 都有 rubric（之後 `deep_eval.md` 要用）。
- `mem_consolidate` 正常結束，沒有錯誤。

## 存放位置
- `memory/`：`meta.json`、`trends.json`、`layer_week|month|half_year|year|long_term.json`、`archive.json`。累積資產，不輕易重置。
- 一律用 CLI 讀，不要直接 Read 這些 JSON。
