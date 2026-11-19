# 深讀與作答評估（teaser／deep／review）

> 目錄：../CLAUDE.md

## 什麼時候用
- 使用者回覆 `teaser <id>` 或 `deep <id>`。
- 使用者對某篇論文的機制給出回答／辯證，需要判讀。

## 怎麼做
1. `teaser <id>`：給精簡導讀；`deep <id>`：`python3 mentor.py deep <id>` 出深度思考題。
2. 提問與追問一律照 `socratic.md`。
3. 讀審查標準：`python3 mentor.py rubric <id>`。你（LLM）就是評分器，不靠關鍵詞比對。
4. 論文在 paper-kb 裡 → 先 `kb_search`／`kb_read` 核對原文再判（`paper_kb.md`）。
5. 逐一檢查**機制細節**（演算法怎麼算、公式乘什麼、為何成立）。使用者常見偏差寫在 `profile.md`（例如框架直覺強、機制細節有偏差）。
6. 記錄裁決：
   ```
   python3 mentor.py review --paper <id> --result pass|fail --depth <0-4> \
       [--domain cv|llm|diffusion] [--blindspots "概念1||概念2"] [--note "一句評語"] [--skills "A||B"]
   ```
   - 正確且有深度 → `pass --depth 2-4`。
   - 有誤或敷衍 → `fail --depth 0-1 --blindspots ".."`，用追問給提示（不給答案）。
   - depth：0–1 表層／2 機制／3 推導／4 批判。沒填 depth 時程式預設 1（不推進）。
7. 同時順帶驗收舊概念（`recall.md`）。

## 驗收標準
- **絕對禁止**未答題或未展現足夠理解就標通過。
- pass 但 depth<2 → 程式不推進領域（會警告）。
- 使用者剛被告知答案後的複述不算 depth≥2 證據，要換角度再問一次答對才算。

## 存放位置
- 裁決寫入 `learner.json`（episodic、blind_spots、skill_map）。
- rubric 來源：`memory/`（`mem_add` 時寫入）。
