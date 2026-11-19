# 學習者狀態、升降級、技能地圖

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日排程第 3 步（推播之後）。
- 每日推播收尾（`mem_consolidate` 之後）。
- 使用者問「進度」「我學得怎樣」 → 給技能地圖。

## 怎麼做
1. `python3 mentor.py learner_state` → 評估進度、自動升降級。
2. 與使用者互動（`deep_eval.md`、`socratic.md`、`recall.md`）。
3. 有作答 → `review` 記錄裁決；通過（depth≥2）才推進、解除盲區。
4. 技能地圖：`python3 mentor.py skill_map`（`--rebuild` 依全部歷史重算）。

## 升降級規則（程式 enforce）
- 每次至多升降一級，不低於地板。
- 只計 **depth≥2** 的 pass；淺過另列「淺過（不計分）」。
- 2026-11-10 之後的 review pass：要等之後的舊概念驗收（`recall.md`）通過才算 1 分，之前只算 0.5 分（顯示「待驗收確認 N」）。
- 舊概念驗收：同一概念**連續兩次**答錯才算一次 fail（−0.5）；單次答錯只記盲區。
- 原則：優先「把機制講精準」，不衝廣度。起點依 `profile.md` 的自評。

## 技能地圖 skill_map（0–5 級）
| 級 | 意義 | 怎麼達到 |
|---|---|---|
| 0 | 未聽過 | — |
| 1 | 聽過 | — |
| 2 | 跟得上 | — |
| 3 | 有提示能做 | `review` 通過（review 最高只到 3） |
| 4 | 獨立能做 | 之後 `recall` 驗收通過 |
| 5 | 能教／能處理邊界 | 驗收時能處理邊界或批判問題（depth 4） |
- `review` 失敗降 1 級；`recall` 要連續兩次答錯才降。
- `review`／`recall` 會依 pid 與標題自動比對技能名稱；也可 `--skills "DETR||Attention"` 指定，不存在會新增。

## 驗收標準
- `learner_state` 正常輸出；沒有因 depth<2 的 pass 而升級。
- **不主動顯示連續天數**（`streak.md`）。

## 存放位置
- `learner.json`：episodic（近 45 天）、blind_spots、skill_map。可單獨重置：`python3 mentor.py reset_learner`（保留導師記憶）。
- `learner_archive.json`：episodic 超過 45 天自動搬入，評估與防重仍會讀。
