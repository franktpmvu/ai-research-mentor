# 複習模式（概念複習＋學習者畫像 KYC）

> 目錄：../CLAUDE.md

原則：**知識本身要有語意**。複習考的是「概念」（例：一對一匹配為何免 NMS），論文只是概念的證據來源；同一概念可由多篇論文支撐。每次複習同時是在更了解使用者（KYC）。

## 什麼時候用
- 使用者對當天推播說「三篇都不喜歡」「都沒興趣」之類 → 不硬推新論文，改開複習。
- 使用者主動說「考我」「幫我複習」。
- 使用者只想打卡、沒力氣（`light_mode.md`）→ **不做**。

## 三把尺（別混淆）
| 尺 | 量什麼 | 用在哪 |
|---|---|---|
| 知識樹 kg 先修（先修距離） | 概念／論文之間誰是誰的前提 | 決定**考什麼**、能不能往下讀 |
| depth 0–4（答題層次） | **單次回答**的品質：0–1 背得出／2 講對機制／3 推得出／4 找破綻或反駁 | 記錄這次答得多好 |
| 技能等級 0–5 | 長期累積熟練度 | 技能地圖 |

## 怎麼做
1. **不喜歡時先記興趣訊號**：`python3 mentor.py review_mode kyc_add --kind interest --text "不喜歡：<哪個方向/想法軸>" --evidence "<日期> <pid們>" --sign -`。一句話問原因可以，不追問、不要求自評。
2. **選題**：`python3 mentor.py review_mode pick`（只給導師看）。候選只來自 review 通過 depth≥2 的內容；排序已考慮：通過後從沒複習過的長期逾期、上次留下缺口、是當日推播的先修、領域分散、當天已討論過的排除。
3. **抽概念**：從候選的 rubric／舊盲區抽一個**語意概念句**（不是論文名）。已有就用；沒有就
   `review_mode concept_add --name "<概念句>" --sources "pid||pid" [--prereqs "cid||cid"]`。概念之間的前提關係用 `concept_link` 補上。
4. **出題**：一次 1 題，形式為換情境應用／反事實（拿掉 X 會怎樣）／兩者比較／找破綻；**不要求複述**、不洩漏上次評語。一次複習 1–2 個概念為限。
5. **追問**：照 `socratic.md`，答錯就更窄地問，不給答案。
6. **記錄**：`review_mode concept_log --id <cid> --result pass|fail --depth 0-4 --how asked|followup [--note ..] [--blindspots "a||b"]`
   - 會自動對概念的第一個來源論文跑 `recall`（沿用間隔與技能地圖）；若已另外用 recall 記過，加 `--no_recall` 避免重複計分。
7. **KYC 觀察**：看到思考模式（強項或偏差），用**固定一句 text** 記：
   `review_mode kyc_add --kind pattern --text "<模式>" --evidence "<cid/日期>" --sign +|-`
   `review_mode kyc_show` 中標「⬆ 可寫入 profile.md」（同一模式 ≥3 次）→ 寫進 `profile.md` 的「學習時的常見模式」。
8. 長期逾期那批的通過／失敗比例就是遺忘曲線證據；若大多仍通過或大多失敗，在 `kyc_add --kind pattern` 記一筆，作為之後調整 recall 間隔的依據。

## 驗收標準
- 題目針對概念、要求應用或推理，不是背論文內容。
- 每次複習至少一筆 `concept_log`；有觀察到模式就有 `kyc_add`。
- 不喜歡的日子有一筆 `--kind interest` 紀錄。
- 同一天已討論過的概念沒有再被考。

## 存放位置
- `concepts.json`：概念節點（名稱、來源論文、先修概念、作答歷史）。
- `kyc.json`：畫像觀察（pattern／interest）。
- 論文層的作答仍在 `learner.json`（透過 recall）。程式：`review_mode.py`（經 `mentor.py review_mode` 分派）。
