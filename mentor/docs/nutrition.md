# 營養學獨立實用軌（Nutrition Track）— docs/nutrition.md

> 入口：../CLAUDE.md。與主研究軌完全分離，用 nutrition.py。

---

> 目標：一年內學會自己規劃三餐（使用者想懂的主題寫在 `profile.md`）。形式：**獨立實用軌 · 理論實作各半 · 每天一則**。

**刻意與主研究軌（CV/LLM/Diffusion）完全分離**——不套用知識圖譜先修守門、不套用 depth≥2 深度評估、不進導師記憶 memory/。理由：目標是「可執行的排餐能力」，論文深度守門那套機制對實用技能是包袱。營養軌自成一套輕量系統：

| 檔案 | 內容 |
|------|------|
| `nutrition.py` | 輕量 CLI（brief / check_dup / log / roadmap_set / show / streak）。start_date=2026-08-10 為營養軌 Week 1，週次獨立於主軌。 |
| `nutrition_roadmap.json` | 52 週實用藍圖（**滾動擴充**：空白週由 LLM 依上週結果生成後 `roadmap_set` 寫回）。Q1 已排 W1-13。 |
| `nutrition_log.json` | 每日推播紀錄（防重＋streak 用）：{date, topic, kind(theory/practice/both), note, url}。 |

**每日流程（附加在主軌之後，每天一則）：**
1. `python3 nutrition.py brief` → 讀本週主題（含理論與實作骨架）、近 14 則已推主題（防重）、本季主題。
2. 依本週主題選今日角度，**必要時上網搜尋佐證**（方法論/證據等級/爭議），優先給可信來源；營養新聞要標證據等級，避免把觀察性研究講成因果。
3. `python3 nutrition.py check_dup --title "..."` → 🟢CLEAR 才推。
4. **呈現格式（理論實作各半，固定兩段）**：
   - **🧠 理論**：今天這個概念的機制/來龍去脈/批判觀點（不是口號，要講「為什麼」）。方法論/演進/批判類主題落在這段。
   - **🍽 實作**：一個今天就能做的具體動作（份量、手掌測量、進食窗、採買、記錄…），對準「能自己排餐」的最終目標。
   末尾一行：關聯本週主題與一年目標的推薦理由 ﹝週主題標籤﹞。
5. `python3 nutrition.py log --topic "..." --kind theory|practice|both [--note "..."] [--url "..."]` 記錄。
6. 結尾一行鼓勵（習慣 > 完美）。使用者主動問「連續幾天」才 `python3 nutrition.py streak`。

> 與主軌收尾並存：營養軌不影響 mentor.py 的任何狀態；兩軌各自記錄、各自 streak。
