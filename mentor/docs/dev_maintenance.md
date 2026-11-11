# 系統維護與檔案架構（Dev & Maintenance）— docs/dev_maintenance.md

> 入口：../CLAUDE.md。只在你要改 mentor.py、integrity 失敗除錯、或想查各狀態檔案用途時才需要讀這份。

---

## 系統架構（重要：狀態必須持久 + 導師/使用者記憶分離）

所有狀態存在此固定資料夾，**不要**再寫進暫存 outputs（會跨階段遺失）。

| 檔案 | 歸屬 | 內容 | 可否重置 |
|------|------|------|----------|
| `mentor.py`      | 系統 | 所有功能函數 | — |
| `profile.md`     | **個人設定** | 使用者背景、目標、常見偏差、偏好、路徑。**不上傳 GitHub**；沒有時讀 `profile.example.md` | — |
| `roadmap.json`   | 系統 | 52 週三軌藍圖（**滾動擴充**：`roadmap_set` 寫回） | — |
| `state.json`     | 執行狀態 | 週次、quarter、domain balance、學習者等級、輪轉基準（`throttle_mode` 等欄位為 2026-08-06 已停用的舊版遺跡） | 隨重置 |
| `memory/`        | **導師記憶** | **切檔儲存（2026-07-11）**：`meta.json`、`trends.json`、`layer_week/month/half_year/year/long_term.json` ×5、`archive.json`（淡出項歸檔）。**累積資產，不輕易重置。** | 否 |
| `learner.json`   | **使用者記憶** | 通關紀錄 episodic（**只留近 45 天**）、盲區 blind_spots、技能圖 skill_map。**可分開重置。** | 是 |
| `learner_archive.json` | 使用者記憶·歸檔 | episodic 超過 45 天自動搬入（`mem_consolidate` 執行）。評估與防重仍讀取。 | 否 |
| `week_plan.json` | 執行狀態 | 當週 7 天想法軸/跨域輪轉 + 黑名單快照（`week_plan new` 產生，可隨週重生） | 隨週重生 |
| `push_log.json`  | **推播記錄** | 每日推播事件（**只留近 30 天**）：{date, papers[pid/role/anchor], composition, ok} | 否 |
| `push_log_archive.json` | 推播記錄·歸檔 | push_log 超過 30 天自動搬入。防重（check_dup）仍讀取。 | 否 |
| `journal/*.md`   | **瑣碎記憶** | 每次互動的**逐字原始對話**（`YYYY-MM-DD_HHMMSS_<tag>.md`），內嵌記憶快照。**只累積。** | 否 |
| `kg.json`        | **知識圖譜** | 先修依賴 DAG（`nodes[pid]={title,domain,level,prereqs[],spontaneous,url,note}`）。**推薦守門的地圖**：主領域只能推「先修全通過」的前沿節點。累積資產。 | 否 |

> `memory.json` 為 2026-07-11 前的遺留單檔，首次執行時自動遷移為 `memory/` 切檔並改名 `memory.json.migrated.bak` 保留。

> 設計原則：導師記憶（研究知識）與使用者記憶（學習軌跡）**分項評估、分開儲存**。
> `mem_consolidate` 評估導師記憶；`learner_state` 評估使用者狀態。
> 重置使用者端用 `python3 mentor.py reset_learner`（清空 learner.json + 進度，**保留** memory/ 的研究記憶）。
>
> **三層記憶的分工**（重要）：
> - `memory/`（導師）與 `learner.json`（使用者）保存**去蕪存菁、結構化**的知識。
> - `journal/`（瑣碎記憶）保存**未經摘要的原始互動**——使用者每一次回話本身就是有價值的記憶。
> - 兩者互補：結構化記憶用於「推薦與評估」，瑣碎記憶用於「回溯與稽核」。
>
> **G. 檔案永遠保持小（2026-07-11，token 紀律）**：
> - token 只在「LLM 直接 Read 檔案」或「指令輸出過長」時消耗；`mentor.py` 程式讀 JSON **不耗 token**。
>   → **LLM 一律透過 CLI 指令讀狀態（daily_brief/mem_context/rubric…），絕不直接 Read 大 JSON。**
> - 雙保險——切檔 + 歸檔輪替（`mem_consolidate` 每日附帶執行，全程式化）：
>   ① 導師記憶按層切檔，單檔小、誤讀成本有上限；淡出項移入 `memory/archive.json` 不刪除。
>   ② `learner.json` episodic >45 天、`push_log.json` >30 天自動搬入歸檔檔。
> - 歸檔**不損失功能**：等級推導（_domain_qa）、升層資格（passed_ids）、防重（check_dup）都仍涵蓋歸檔內容。

bash 路徑範例：`$HOME/mnt/<專案資料夾>/mentor.py`（host 路徑記在 `profile.md`）

**F. 完整性鐵則（2026-07-07；2026-07-17 補強）**：每日流程開頭**必跑** `python3 -m py_compile mentor.py && python3 mentor.py integrity`。
若編譯失敗或 JSON 損壞（曾發生沙箱同步到截斷版 mentor.py）→ **停止流程、先修復檔案；絕對禁止手改 JSON 繞過主程式**（會破壞狀態一致性：漏 push_log、漏輪轉推進）。

**F2. mentor.py 修改鐵則（2026-07-17，截斷病灶已確診）**：
- **病灶**：沙箱 mount 對 `mentor.py` 這個路徑的**屬性快取（size/mtime）凍結在「上次沙箱端寫入」的值**——host 端（Edit/Write 工具）把檔案改大後，沙箱只更新內容、不更新大小，超出舊 size 的尾段被截掉（截斷點常落在註解中 → py_compile 假陽性）。其他檔案（JSON、CLAUDE.md）同步正常；只有「host 端改 mentor.py」這個方向壞。
- **規則①**：**mentor.py 的任何修改一律從沙箱端（bash）寫入**——python heredoc 讀舊檔、程式化替換（anchor 需 assert 唯一）、寫回 mount 路徑；沙箱→host 方向可靠且會刷新屬性快取。**禁止用 host 端 Edit/Write 工具直接改 mentor.py**。
- **規則②**：`integrity` 已加**尾行哨兵**——檔案最後一行必須含 `EOF-SENTINEL`，缺了即判定截斷版、exit 4 停手。改檔後該行必須保留在檔尾。
- **規則③**：修改後雙側驗證：沙箱端 `wc -l + py_compile + integrity`；host 端 Read 檔尾確認 EOF-SENTINEL 存在。

