# 金融鏡子（finance）

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日推播固定 **1 篇「金融理論 × 主領域」**；連結的主領域由 `daily_brief` 輪轉指定（llm／diffusion／cv）。

## 怎麼做
1. 選一個**金融／經濟學本身的學理與數學結構**：隨機微積分、無套利定價、鞅論與測度變換、市場微結構、投資組合最適化、資訊不對稱賽局、選擇權定價 PDE、random matrix theory、Kelly 準則等。
2. 用它解釋／重講當天指定主領域的某個機制。方向是 **finance theory → 主領域機制**。
   - 例：Black-Scholes PDE／反向 SDE ↔ score-based diffusion；Girsanov 測度變換 ↔ normalizing flow 變數變換；市場微結構資訊不對稱 ↔ attention 的資訊篩選；均值-變異數權衡 ↔ 多目標 loss 權衡。
3. 核實出處（`refcheck.md`）→ `check_dup` → `mem_add`（domain 記所連結主領域、tags 加 `finance`、含 rubric）→ `kg_add --spontaneous`。
4. `push_log` 寫成 `pid::finance::<anchor>::<url>`，anchor 必填。

## 禁止（方向鎖定）
- ❌ 主領域模型 → 金融應用：LLM 預測股價、Transformer 讀 order book、VLM 讀 K 線、diffusion 生成金融時序。這些是量化金融應用，不算金融鏡子。

## 驗收標準
- anchor 格式為「金融理論 X ↔ 主領域機制 Y」（哪個數學結構、對應哪個機制），不是應用場景。
- 呈現四段結構，③ 明確回接 anchor。
- `push_log` 不報缺 anchor／缺網址／未核實。

## 存放位置
- `memory/`、`kg.json`、`push_log.json`。
