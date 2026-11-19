# 營養學獨立實用軌

> 目錄：../CLAUDE.md

目標：一年內學會自己規劃三餐（想懂的主題寫在 `profile.md`）。形式：**理論實作各半、每天一則**。
與主研究軌**完全分離**：不套知識圖譜、不套 depth 評估、不進導師記憶、不動 `mentor.py` 任何狀態；兩軌各自記錄、各自 streak。

## 什麼時候用
- 每日排程第 4 步（主研究軌之後）。

## 怎麼做
1. `python3 nutrition.py brief` → 本週主題（理論＋實作骨架）、近 14 則已推主題、本季主題。
2. 依本週主題選今日角度；必要時上網搜尋佐證（方法論／證據等級／爭議），優先可信來源；營養新聞要標證據等級，不要把觀察性研究講成因果。
3. `python3 nutrition.py check_dup --title "..."` → 🟢CLEAR 才推。
4. 呈現（固定兩段）：
   - **🧠 理論**：概念的機制／來龍去脈／批判觀點（講「為什麼」，不是口號）。
   - **🍽 實作**：一個今天就能做的具體動作（份量、手掌測量、進食窗、採買、記錄…），對準「能自己排餐」。
   - 末尾一行：關聯本週主題與一年目標的推薦理由 ﹝週主題標籤﹞。
5. `python3 nutrition.py log --topic "..." --kind theory|practice|both [--note ".."] [--url ".."]`
6. 結尾不加打氣語（不用「習慣 > 完美」這類鼓勵句）；語氣中性。
- 本週主題空白 → 依上週結果生成後 `python3 nutrition.py roadmap_set --week N --theme .. --theory .. --practice ..`。
- 使用者主動問連續天數才 `python3 nutrition.py streak`。

## 驗收標準
- 當天 `nutrition_log.json` 有一筆紀錄，主題通過 check_dup。
- 呈現有理論與實作兩段，實作是今天可執行的具體動作。

## 存放位置
| 檔案 | 內容 |
|---|---|
| `nutrition.py` | CLI（brief／check_dup／log／roadmap_set／show／streak）。start_date=2026-08-10 為營養軌 Week 1。 |
| `nutrition_roadmap.json` | 52 週實用藍圖（滾動擴充） |
| `nutrition_log.json` | 每日推播紀錄 {date, topic, kind, note, url} |
