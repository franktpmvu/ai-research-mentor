# done 收尾總順序

> 目錄：../CLAUDE.md

## 什麼時候用
- 使用者說 done、「今天就到這裡」「先這樣」等結束語。
- **先排除**：若你剛問了一題蘇格拉底題、對方只回「.」「嗯」「ok」這類空訊號 → 不是 done，先問「要繼續這題還是今天先收？」（`socratic.md` 第 9 條）。

## 先判斷今天屬於哪種
- **A. 真的有討論論文機制／嘗試回答 deep** → 走完整順序。
- **B. 只看了看、隨口一句** → 只做 `light_checkin`（＋需要時對話總結）。

## 完整順序（A）
| # | 步驟 | 條件 | 細則 |
|---|---|---|---|
| 1 | `recall` | 有順帶驗收到舊概念 | `recall.md` |
| 2 | `review` | 有作答／辯證 | `deep_eval.md` |
| 3 | `journal_add` | 有實質互動 | `journal.md` |
| 4 | `paper_xlsx` | 當次真的討論了某篇論文（每篇一次） | `paper_xlsx.md` |
| 5 | `sheet_sync` | `profile.md` 有 Google Sheet ID | `sheet_sync.md` |
| 6 | `kb_queue` | 有 paper-kb 且論文有網址 | `paper_kb.md` |
| 7 | `light_checkin` | **一律** | `light_mode.md` |
| 8 | 獨立評判（反討好） | 本次有實質評斷/辯證/評估 | `independent_judge.md` |
| 9 | 對話總結 | 一律（未答蘇題不劇透；若有第8步裁決，總結據實反映、不得軟化） | `summary.md` |

## 驗收標準
- 當天 `push_log.json` 有 `user_engaged=True`。
- A 類日子：`learner.json` 有新 review、`journal/` 有新檔、`論文閱讀.xlsx` 有對應列（M 欄已寫）。
- Sheet 同步失敗時，對話裡有提醒「Sheet 未同步第 N 列」。
- 含實質評斷日：收尾有一段未被軟化的獨立評判裁決；純推播/light-only 日不觸發（不空燒 token）。

## 存放位置
- 見各步驟細則；總覽見 `file_map.md`。
- **M 欄對話脈絡只存在當下對話裡，必須在 done 當下寫，事後無法還原。**
