# 極輕量模式（light_checkin）

> 目錄：../CLAUDE.md

原則：先養成「看」的習慣，有餘裕再深入；完美不是每日必要條件。

## 什麼時候用
- **使用者回覆 done／今天結束 → 一律執行一次**，不論今天是深讀還是只看一眼（收尾順序見 `done_closing.md`）。
- 使用者說今天沒空、只想打卡。

## 怎麼做
```
python3 mentor.py light_checkin [--note "一句話"] [--interest "方向回饋"] [--date YYYY-MM-DD]
```
- **合併寫入**：當天已有正式推播 → 只加「已打卡」標記（`user_engaged=True`），不覆蓋論文清單；當天沒紀錄 → 新建空白打卡。隨時呼叫都安全。
- 今天要不要「詳細記錄」是**事後判斷**，不是事先選模式：
  - 只看摘要／隨口一句 → 只要 `light_checkin`，`--note` 一句話即可。
  - 有真的討論機制或嘗試回答 `deep` → 另外做 `review`＋`journal_add`（＋`paper_xlsx` 等，見 `done_closing.md`），最後仍照樣 `light_checkin`。
- `--interest` 用於方向回饋（`redirect.md`）。
- 回應語氣：中性、簡短確認打卡即可（例：「今天已記錄。」）；不打氣、不用「習慣 > 完美 ✓」這類肯定語，也不暗示使用者「應該」做更多。

## 驗收標準
- 每個使用者有互動的日子，`push_log.json` 當天都有 `user_engaged=True`。
- 當天正式推播的論文清單沒有被清空。

## 存放位置
- `push_log.json`（`user_engaged`、`light_note`、`interest` 欄位）。
- `--interest` 另寫入 `state.json` 的 `progress.redirect_note`。
