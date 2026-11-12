# 已知修復紀錄（Changelog）— docs/changelog.md

> 入口：../CLAUDE.md。歷史沿革與踩坑紀錄，日常執行不需要讀這份。

## 已知修復紀錄
- 2026-07-03：檔案遷移至固定資料夾 `atomic_habit/`（原暫存 outputs 跨階段遺失）。
- 2026-07-03：導入層級時間記憶 + 導師/使用者記憶分離；評估改 LLM-as-Judge（rubric+review）；新增跨域鏡子常設軌 + 保守升級 + 機制級精準度優先；建立每日 07:00 排程。start_date = 2026-07-03（week 1）。
- 2026-07-04：新增第三層記憶「瑣碎記憶」（journal/）。
- 2026-07-07：推薦機制改版（web search 為主體、防重複、想法軸輪盤、跨域來源放寬）；省 token 分層重構（check_dup / week_plan / daily_brief）；確立設計哲學北極星；跨域 1–3 篇 + 金融鏡子常設軌。
- 2026-07-07（二）：**系統盤點後改版 A–D+F**：
  ① **A. `push_log`**：每日推播事件程式化驗收——組成（3主+≥1跨域+1金融，throttle 放寬）、xdomain/finance 必填 anchor（「回接主領域機制」從自律變資料欄位）、daily_brief 改以 push_log∪episodic 推進日 slot（修正「無互動則想法軸不輪轉」）。
  ② **B. 漸進鞏固修正**：升層需「資格（seen≥2/learner passed/imp≥7）+ 本層停留≥窗口一半」；long_term 入口需（passed且imp≥8）或 seen≥3——修正 imp≥7 連日直通 long_term 的漏洞。
  ③ **C. 深度守門程式化**：`review` pass 但 depth<2 不推進領域；`_derive_level` 只計 depth≥2 的 pass。
  ④ **D. `roadmap_set`**：52 週藍圖滾動擴充——`week_plan new` 遇空白週目標時由 LLM 生成寫回。
  ⑤ **F. `integrity`**：每日流程開頭檢查 mentor.py 可編譯 + JSON 可解析；曾發生沙箱同步到截斷版 mentor.py 導致指令全掛、狀態被手改繞過——今後壞了停手修檔，禁止手改 JSON。
- 2026-07-09：**金融鏡子方向鎖定**——使用者反饋過去所選金融鏡子多為「用 LLM/ML 模型做金融任務」（如 Transformer 讀 order book 做價格預測、VLM 讀 K 線圖），這不是想要的方向。修正為：必須借金融/經濟學**自身的數學理論**（隨機微積分、無套利定價、鞅論、市場微結構理論等）反過來解釋主領域機制，禁止「AI 模型應用在金融」類論文歸入金融鏡子。
- 2026-07-09（二）：**跨域鏡子方向鎖定（同一問題的推廣：「拿著槌子看什麼都是釘子」）**——使用者指出跨域鏡子也不該找「與目標領域相關」（即 AI/ML 套用到其他領域）的論文，而應找該領域**自身**方法論更強、更純粹理論的論文，借的是方法論而非再套一次深度學習。修正為：跨域來源論文必須不涉及 AI/ML、是該領域自身的經典或前沿方法論/理論，禁止「用 GNN/Transformer/深度學習做 X 領域任務」類論文歸入跨域鏡子。已同步更新每日排程 SKILL.md。
- 2026-07-11：**趣味探索軌（wild）+ 記憶切檔與歸檔輪替**。
  ① 使用者反饋「推薦一定要回接主領域」開始無聊——新增 wild 常設軌：每日固定 3 篇與主領域無關的有趣論文（獨特方法論/反直覺，可非自然科學，越廣越好），輕量制（免 anchor/mem_add/rubric/守門，僅 check_dup 防重 + push_log 記 `pid::wild::標題`）。`push_log` 組成檢查改為 3主+≥1跨域+1金融+3wild。
  ② 記憶檔案瘦身（token 紀律 G）：memory.json 切為 `memory/` 分層檔（首次執行自動遷移，原檔留 .migrated.bak）；learner episodic >45 天、push_log >30 天由 `mem_consolidate` 自動歸檔（learner_archive.json / push_log_archive.json）；淡出項移 memory/archive.json 不刪除。評估與防重仍涵蓋歸檔。check_dup 擴大掃描 push_log（含歸檔），wild 論文因此也防重。已同步更新每日排程 SKILL.md。
- 2026-07-14：**拒平庸 survey（硬規則④，適用所有軌）**——使用者反饋 survey 論文不有趣：單純整理彙總不帶來想法轉變，且許多新方法本身就是先做好 survey 才得出的。修正為：原則上不推 survey/review/綜述；唯一例外是該 survey 本身提出突破性觀點或新方法，且推薦理由必須明講突破點。已同步更新每日排程 SKILL.md。
- 2026-07-16：**知識圖譜·先修守門（防跳級）**——使用者反饋 diffusion/llm 推薦太難無法下手（推 EDA 但沒看過 EDM、不懂 ODE/SDE）。病灶：粗粒度 A/B/C 等級太鈍，且 mem_add 進來的新論文從不進任何先修圖，等級守門形同虛設。新增持久化先修依賴 DAG `kg.json`：node={title,domain,level,prereqs[],spontaneous}；`passed=depth≥2 review pass` 自動推導解鎖；main 三篇每篇推薦前必跑 `kg_check`，🔴LOCKED（先修未過）禁止跳推、改推先修前沿；搜到新論文 `kg_add` 依引用入圖接先修邊。刻意保留跳躍自由：跨域/金融用 `--spontaneous` 豁免守門，wild 不進圖譜。新增指令 `kg_seed/kg_add/kg_link/kg_check/kg_frontier/kg_show`，`daily_brief` 內嵌前沿摘要，`integrity` 納入 kg.json。已同步更新每日排程 SKILL.md。
  ⚠ 本次改動時再次遇到「沙箱 mount 同步到舊/截斷版 mentor.py」（host 檔完好、bash 端 mtime 凍在 07-11）——依鐵則 F 未在殘缺副本上執行，等待重新同步後才驗證。
- 2026-07-16（二）：**KG 守門程式化接入 push_log + --dry 呈現前預檢**——使用者質疑「鎖定論文照目前形式好像還是會推給使用者」。查證屬實：07-16 當日推播（03:13，早於 kg.json 建立 10:36）推了兩篇 LOCKED main（eda-arb 缺 edm、infokv 缺 kv_cache），push_log 仍回 ok=True。病灶有二：① 時序——當日推播先於 KG 建立；② 結構——`kg_check` 只是自律指令，唯一程式化驗收點 `push_log` 完全不驗 main 的 KG 狀態（與 07-07 前「anchor 靠自律」同病灶）。修正：`push_log` 對每篇 main 程式化驗 KG（LOCKED/UNKNOWN 與缺 anchor 同級 → exit 3、提示改推先修前沿）；新增 `--dry` 旗標供**呈現給使用者之前**預檢（完整驗收、不寫檔）——每日流程新增步驟 3.5，使用者永遠不看到鎖定論文。已以 stub 單元測試驗證五情境（含重演當日事故）。⚠ 沙箱 mount 仍凍在截斷版（斷點位移到 2381 行、恰在註解中導致 py_compile 假陽性——**integrity 應搭配尺寸/尾行檢查**），本次依鐵則 F 於 host 檔修改、以 outputs 沙箱單元測試驗證。
- 2026-07-17：**mentor.py 截斷病灶確診 + 修復 + 程式化防護（鐵則 F2）**——以雙向探針實驗確診：沙箱 mount 對 mentor.py 的**屬性快取（size/mtime）凍結在上次沙箱端寫入的值**（凍在 07-11、124036 bytes）；host 端 Edit 改大檔案後，沙箱只更新內容、size 不動 → 尾段被截。證據：① host 端加 ZX91 標記，沙箱完全看不到；② 沙箱端 cp 完整版回 mentor.py 後暫時恢復；③ host 端再改大（加哨兵檢查）→ 沙箱又截斷在 139736（= 上次沙箱寫入的 size）。修復與防護：① 完整版由沙箱端寫回（雙側驗證 2685 行、可編譯）；② `integrity` 新增**尾行哨兵檢查**（檔尾必含 EOF-SENTINEL，缺了 exit 4——堵 py_compile 假陽性）；③ 立鐵則 F2：**mentor.py 一律沙箱端修改，禁止 host 端 Edit/Write**。工作副本 mentor_full/mentor_run/mentor_fixed_20260717/mentor_tail_* 為歷次搶修遺留，確認穩定後可清。
- 2026-08-05：**streak 計算病灶修復 + 改為主動查詢才顯示 + 新增超輕量模式**（使用者反饋三點）：
  ① **病灶確診**：`consecutive_active_days`/`last_active_date`/`throttle_mode` 只有已淘汰的 `boot()`/`daily_push()`（舊版 curated-PAPERS 流程）才會遞增/衰減，但現行每日流程完全走 `push_log`，從不觸碰這三個欄位——實測 `state.json` 的 `last_active_date` 凍結在專案第一天 2026-07-07，數字停滯不動，正是使用者「顯示錯誤、好久沒互動也沒更新」的成因。
  ② **修法**：新增 `_all_activity_dates()`/`_streak_stats()`/`_is_throttle_due()`，一律從**原始紀錄**即時推導、不再維護計數器：只算「使用者真的有動作」的日期——`teaser`/`deep`/`review` 產生的 episodic 狀態（`teaser_seen`/`reading`/`passed`/`failed`）、`light_checkin` 打卡、`journal/` 逐字對話——**刻意排除**每日自動產生的推播本身（`push_log` 的 main/xdomain/finance/wild，那只代表系統照排程備好功課，不代表使用者看過，算進去會虛報 streak，實測用舊定義得出誤導性的「連續 34 天」，改用真實互動定義後正確顯示「總 20 天／連續 0 天，最近一次 2026-07-24」）。`push_log`/`boot`/`mem_context` 的精簡模式判斷同步改用 `_is_throttle_due()`。
  ③ **只在主動詢問時顯示**：`daily_brief`/`learner_state`/`push_log`/`boot` 移除自動印出「連續 N 天」；新增 `streak` 指令，只在使用者主動問時才執行回答。
  ④ **新增超輕量模式**：`light_checkin [--note] [--interest] [--date]`——只看簡介或說一句方向感受也算完成一天，免深讀評估，仍計入 streak 與週執行進度；帶 `--interest` 時寫入 `state.json progress.redirect_note`，`daily_brief` 下次會主動提示「📍 待處理方向回饋」，導師依此重新搜尋、調整推薦方向後執行 `redirect_clear` 清除。目的：使用者給方向回饋時，導師依「現在深讀 vs 之後再排」分流——講明「今天就要」才進深讀模式，否則預設超輕量記錄。
  ⑤ 以沙箱端隔離副本（`/tmp/test_atomic`）驗證 `light_checkin`/`redirect_clear`/`daily_brief` 提示/`push_log --show` 顯示皆正確，未污染真實 `push_log.json`/`state.json`；`streak`（唯讀）已於正式資料驗證。全程依鐵則 F2 於沙箱端修改 mentor.py，雙側驗證 `wc -l`/`py_compile`/`integrity`（含 EOF-SENTINEL）通過。
- 2026-08-06：**移除節流/精簡模式 + light_checkin 改為不可破壞性打卡 + 「done 一律記互動」**（使用者反饋：既然已有超輕量模式，就不需要另一套自動判斷「久未互動」再放寬標準的節流機制；且回覆 done 不管是不是超輕量都要留下互動紀錄，只有深讀才要詳細記錄）：
  ① **移除節流/精簡模式**：刪除 `_is_throttle_due()` 與所有呼叫點（`push_log` 組成驗收、`daily_brief`/`boot`/`mem_context` 的精簡模式徽章、`daily_push()` 的降頻/連續3天恢復邏輯）。`push_log` 現在**一律**要求完整組成（3主+≥1跨域+1金融+3wild），沒有放寬情境；沒力氣深讀時改用 `light_checkin`。
  ② **light_checkin 改為合併寫入，不再覆蓋當天紀錄**：舊版每次呼叫都會用空白 `mode=light` entry 整筆覆蓋當天的 push_log（若當天已有正式推播，論文清單會被清空——這在「done 一律要打卡」的新規則下會是嚴重的資料損毀風險）。修正：先找當天既有 entry，若存在只加註 `user_engaged=True`（+ 可選 `light_note`/`interest`），**保留原本的 papers/composition**；若當天還沒有任何紀錄，才新建空白 entry。`push_log`（正式推播）寫入時同樣會保留先前 light_checkin 留下的 `user_engaged`/`light_note`/`interest` 欄位，兩個方向互不覆蓋。
  ③ **streak 判準改用 `user_engaged` 旗標**（原本是 `mode=="light"`，只認得到「純輕量、無推播」的那種 entry，改版後 light_checkin 可能合併進一筆有完整論文清單的 entry，`mode` 欄位不存在，必須改認獨立旗標）。
  ④ **CLAUDE.md 新增鐵則**：使用者回覆「done」／今天結束了 → 一律 `light_checkin`，不論今天是深讀還是只看一眼；今天是否算「深讀」不是預先選擇，而是事後依「是否真的討論到機制／是否嘗試攻略了論文」判斷——真的有的話才額外做 `review`＋`journal_add` 詳細記錄，`light_checkin` 兩種情況都照樣執行一次。
  ⑤ 以沙箱端隔離副本驗證：先 `push_log` 寫入一筆完整推播 → 再 `light_checkin` 打卡 → 確認論文清單未被清空、`user_engaged` 正確附加、`streak`/`push_log --show` 正確反映；並確認組成不足時 `push_log` 一律 exit 3（無放寬）。正式資料 `streak`（唯讀）驗證無誤。全程依鐵則 F2 於沙箱端修改 mentor.py，雙側驗證 `py_compile`/`integrity`（含 EOF-SENTINEL）通過。
- 2026-08-07：**wild 防重機械化——以「論文身分(URL/arXiv id)」為單位去重**（使用者反饋：才能/專精主題的 wild 反覆出現，7/13 甚至寫過感想；且要求「能機械化就機械化，不做需 LLM 判斷的事」）。病灶診斷：① wild 軌輕量制不進導師記憶，防重唯一依據是 push_log 標題比對；② `_collect_known_papers` 對 push 論文的 url 硬編為空字串，wild 連 URL 都沒存；③ 才能主題每次換標題（Junior vs senior／What Makes a Champion／Later specialization…），Jaccard 被壓在 0.6 門檻下溜過。修法（純機械、無語意判斷）：① push_log 論文格式加**選填第四欄 url**（`pid::wild::標題::url`），存進 papers 欄位；② `_collect_known_papers` 改讀 push 論文的 url；③ 新增 `_arxiv_id()` 正規化 arXiv id，`check_dup` 增一條 **arXiv id 一致即 HIT**（abs/pdf/html + vN 各形式互相命中）。效果：**同一篇論文換任何 URL 形式重推都會被擋**。誠實限界：此為「論文身分」去重，**擋不了「不同論文、同一主題」反覆**（今日才能案例正是三篇不同論文）——那需主題關鍵詞黑名單或 embedding 語意去重，兩者皆需判斷，依使用者指示**不建置**。今日已將 wild 三篇補上 url 寫回 push_log；`daily_brief` 流程與 CLAUDE.md 指令速查已註明 wild 一律附第四欄 url。沙箱端隔離副本驗證三情境（arXiv 跨形式命中／非 arxiv 完整 URL 命中／wild 確實存 url）皆通過；依鐵則 F2 沙箱端改 mentor.py，雙側 `py_compile`/`integrity`（EOF-SENTINEL）通過。
- 2026-08-07（二）：**daily_brief 新增「近45天 wild 已推主題」長窗——補足「不同論文·同一主題」反覆的漏洞（低 token、不需 embedding）**（延續 08-07 誠實限界：機械 URL/id 去重擋不了同主題不同論文；使用者提問「搜尋時本來就在用 LLM，順便比對會不會很貴」→ 結論：不貴，因為判斷本來就在做，只需把一份短文字清單塞進上下文即可，貴的是 per-candidate embedding，不走）。病灶：daily_brief 原本只印「近7天已推」黑名單，才能主題三次（7/11、7/13、7/22）全在 7 天窗外，我搜 wild 時等於閉眼判斷。修法：新增一行 `🎲 近45天 wild 已推主題`，掃 `push_log`＋`push_log_archive`（>30 天已歸檔，故必含 archive）取 role=wild 標題、`_norm_title` 去重、每則截 40 字，與原 7 天黑名單並存、不動原邏輯。效果：搜 wild 時肉眼即可避開同主題反覆（實測列出 84 則，涵蓋全部才能相關標題）。token 成本：純文字清單約 1.5–2k tokens/日，遠低於一則搜尋結果。依鐵則 F2 沙箱端改 mentor.py，雙側 `py_compile`/`integrity`（EOF-SENTINEL）通過。
- 2026-08-08：**推薦呈現改「三段結構」**（使用者反饋：舊呈現「一句話 Takeaway＋推薦理由」太像結論、常淪為「把 ooo 改成 xxx」，讀完不知道問題到底卡在哪、為何這招管用）。修法：每日推播流程步驟 4 的主領域/跨域/金融呈現格式，從「標題＋一句 Takeaway＋推薦理由＋標籤」改為強制三段——**① 問題背景（機制成因，非症狀）② 核心發想（關鍵 insight／類比，且講清為何能解①）③ 技術細節（公式/演算法/設計取捨；跨域·金融此段須回接主領域 anchor）**，末尾才接推薦理由＋標籤。判準：讀者看完①②要能回答「問題是什麼、為何這招管用」。wild 維持輕量一句話、不套三段。純文件規則調整（CLAUDE.md），未動 mentor.py。


## 2026-11-02 論文閱讀.xlsx 自動登錄（paperlog.py）
- 使用者覺得手動更新 log 太麻煩 → 新增 `paper_xlsx`，done 收尾時自動寫入。
- 欄位定案：note = 使用者逐字原話（程式從 journal 擷取）；question = 導師精煉內容＋思考軌跡；新增 H–M 欄（領域/判定/paper_id/背景知識/journal/對話脈絡）。
- 使用者原則：「好幾年後回來看還是要能懂當時在問什麼、思考邏輯是什麼，不能只有精煉後的語言」→ 加入 M 欄對話脈絡＋D 欄思考軌跡。
- 踩坑：A 欄 `=IF(..,TEXT(NOW()),A)` 自我參照公式的快取是字串，用 openpyxl 存檔會丟失快取 → 寫入前一律凍結成固定日期（第一次寫入時只處理了 datetime 快取，28 列被洗掉，已從備份還原並修正）。
- 實作放在獨立的 paperlog.py；mentor.py 只加一行指令分派，降低觸發 F2 截斷病灶的風險。

## 2026-11-05 問題優先原則（使用者回饋）
- 使用者原話：「你講的很數學的部分都很難讓人覺得有興趣。先講好問題是什麼，數學只是工具而已。」
- 處理：在 docs/daily_push.md 的「三段結構」判準後新增「問題優先原則」——①問題背景必須講到有感、當賣點；數學/公式只是工具放②③且每符號服務於①；能白話講機制就白話優先，不以數學漂亮當推薦理由。
- 動機：連續推播偏數學導致「無聊」；北極星的跳躍思考要靠「問題的張力」點火，不是公式密度。
- 2026-11-11：**借鏡 Jane Street `socratic-tutor`（MIT）升級評估系統**：① 新增間隔抽考 `recall_due`/`recall`（3→7→30→90→180 天，狀態由 qa_record 推導、不另存排程），`daily_brief` 每天顯示 1 題；② 升級加嚴：2026-11-10 後的 pass 需抽考確認才算滿分（之前不追溯）；③ 修復 `skill_map` 自 7/3 起從未被更新的 bug，改 0–5 級、`review`/`recall` 自動更新、新增 `skill_map` 指令；④ `learner_eval.md` 新增蘇格拉底式提問規則（一次一題、答錯追問不給答案、答對壓力測試、複述不算通過）。改前備份在 `archive/pre_socratic_20261111/`。
- 2026-11-11（改版）：使用者指出每日抽考在門口加關卡、違反原子習慣 → **拿掉獨立抽考**（`daily_brief` 不再出題），改成「討論新論文時順帶驗收它的先修/同技能舊概念」：新增 `recall_related`；`recall` 加 `--how mentioned|asked|followup`（主動講對＝最好的無提示回想，不必另問）；單次答錯只記盲區、間隔歸零，同概念連錯兩次才算 fail、才降技能等級。
- 2026-11-11（GitHub 化）：個人資訊從規則文件移到 `profile.md`（gitignore；範本 `profile.example.md`，沒有也能跑）；新增 paper-kb 整合 `kb_search`/`kb_read`/`kb_queue`（直接讀 paper-kb 的 SQLite，免 MCP；沒裝 paper-kb 自動略過），見 `docs/paper_kb.md`。
- 2026-11-12：**補蘇格拉底 × 收尾的規則打架 + 禁理解確認句（使用者回饋）**：實戰踩到兩坑——(1) 使用者只回「.」被誤判為 done,跑了收尾且對話總結把還沒答的蘇格拉底題答案爆雷;(2) 講解後用「懂了嗎/腑に落ちた」收尾,是被動 comprehension check、非蘇格拉底(追問精神)。處理:`learner_eval.md` 蘇格拉底規則新增 #9(題開著時遇模糊/空回覆先問『繼續還是收』、總結不得劇透未答題)與 #10(禁「懂了嗎/清楚嗎」收尾,改以壓力測試/應用題收尾),並在「對話總結」段加同義護欄。動機:蘇格拉底為純文字規則、無程式 enforce,易與「done→收尾」打架、也易退回「老師確認理解」慣性。

- 2026-11-12：**文獻強制核實（使用者要求「每一筆都要是真文獻、核實必須被強制」）**：新增 `refcheck.py`（arXiv 官方 API＋本機 paper-kb＋人工登記證據網址，結果存 `ref_ledger.json`）。程式把關三個入口：`mem_add`（exit 5）、`push_log`（每篇需出處網址且已核實，exit 3）、`paper_xlsx`（主文獻＋【補強文獻】逐條，未過不寫）。全面稽核：試算表 68 列無捏造文獻，ReDiF 標題記錯；導師歷來推薦的 54 篇補強文獻全數真實；導師記憶 344 個 arXiv 連結中 5 個指錯論文（elastic_detr 副標題與編號皆錯、fin_pq_wedge_llm 把論文小節當標題、xd_rd_equiv 查無此文、online_vqa 與 xd_paralleltemper_diff 編號錯）。另發現歷來推播 1025 筆只有 162 筆附出處網址——之後一律必附。改前備份 `archive/pre_refcheck_20261112/`。
