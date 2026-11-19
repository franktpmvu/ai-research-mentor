# 習慣統計（streak）

> 目錄：../CLAUDE.md

## 什麼時候用
- **只在使用者主動問**時（「我連續幾天了」「我這陣子表現如何」）。
- `daily_brief`、`learner_state`、`push_log`、`boot` 等自動流程一律**不主動**顯示「連續 N 天」。

## 怎麼做
- `python3 mentor.py streak` → 回傳「總互動天數」與「目前連續天數」，如實告知。
- 語氣中性、不帶壓力；中斷不說「破功」「失敗」，回來就從新的一天繼續。

## 什麼算互動
- ✅ 算：`teaser`／`deep`／`review` 留下的 episodic（teaser_seen／reading／passed／failed）、`push_log` 裡 `user_engaged=True`（light_checkin 打卡）、`journal/` 逐字對話。
- ❌ 不算：沒有打卡標記的推播紀錄（那只代表系統備好了功課，不代表使用者看過）。

## 驗收標準
- 數字是即時從原始紀錄推導（不靠計數器），與實際互動相符。
- 自動流程的輸出裡沒有連續天數。

## 存放位置
- 不另存；讀 `learner.json`、`learner_archive.json`、`push_log*.json`、`journal/`。
- `state.json` 殘留的 `throttle_mode`／`consecutive_active_days`／`last_active_date` 是舊欄位，程式不讀，不要依賴。
