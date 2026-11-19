# 方向回饋 → 重新指路

> 目錄：../CLAUDE.md

## 什麼時候用
- 使用者說「我對 OO 領域感興趣」「最近 OO 感覺很 ooxx，想要 OO 方向」之類。
- `daily_brief` 印出「📍 待處理方向回饋」時。

## 怎麼做
1. 依使用者的話**重新上網搜尋**，先構思新方向的候選（可以先找，但先別呈現）。
2. 問使用者：「要現在看（深讀）還是之後再排？」——若原話已講明「今天就要／現在」，跳過詢問。
3. **今天就要** → 照 `daily_push.md` 完整流程把新方向候選正式推播；收尾照常 `light_checkin`。
4. **之後再排／沒講明** → `python3 mentor.py light_checkin --interest "使用者原話或摘要"`：算完成今天，並把方向回饋寫進 `state.json`。
5. 之後 `daily_brief` 會主動提示 📍；依此調整推薦方向並正式呈現後，執行 `python3 mentor.py redirect_clear` 清除提示。

## 驗收標準
- 方向回饋不會遺失：不是當天推播，就是存進 redirect_note 並在下次 daily_brief 出現。
- 新方向已呈現後，redirect_note 有被清除。
- 不影響已累積的導師記憶與知識圖譜。

## 存放位置
- `state.json` → `progress.redirect_note`。
