# 檔案存放位置總表

> 目錄：../CLAUDE.md

## 什麼時候用
- 想知道某個狀態存在哪、能不能重置、該用哪個指令讀。

## 原則
- 所有狀態存在專案資料夾的固定檔案，**不要**寫進暫存 outputs（會跨階段遺失）。
- LLM **一律透過 CLI 讀狀態**（daily_brief／mem_context／rubric…），不要直接 Read 大 JSON（token 紀律）。
- 導師記憶（研究知識）與使用者記憶（學習軌跡）分開存、分開評估。

## 規則與文件
| 位置 | 內容 |
|---|---|
| `CLAUDE.md` | 目錄 |
| `docs/*.md` | 細則（只寫最新守則） |
| `changelog/*.md` | 各細則的變更紀錄（與細則同名）＋舊版總表 |
| `profile.md` | 個人設定：背景、偏好、路徑、Google Sheet ID。**不上傳 GitHub**；沒有就讀 `profile.example.md` |
| `archive/` | 改版前備份、xlsx 輪替備份 |
| `reviews/` | 稽核報告等一次性文件 |

## 程式
| 檔案 | 用途 |
|---|---|
| `mentor.py` | 主系統所有指令（修改規則見 `dev_maintenance.md`） |
| `nutrition.py` | 營養軌 |
| `paperlog.py` | `paper_xlsx` 的實作 |
| `refcheck.py` | 文獻核實 |
| `sheetsync.py` | 匯出 xlsx 列給 Google Sheet |
| `review_mode.py` | 概念複習＋KYC（經 `mentor.py review_mode` 分派） |

## 狀態檔
| 檔案 | 歸屬 | 內容 | 可否重置 |
|---|---|---|---|
| `state.json` | 執行狀態 | 學習者等級、輪轉基準、redirect_note 等 | 隨重置 |
| `week_plan.json` | 執行狀態 | 7 天想法軸／跨域輪轉＋黑名單快照 | 隨週重生 |
| `memory/` | 導師記憶 | 5 層分檔＋meta／trends／archive | 否 |
| `learner.json` | 使用者記憶 | episodic（近 45 天）、blind_spots、skill_map | 是（`reset_learner`） |
| `learner_archive.json` | 使用者記憶歸檔 | episodic 超過 45 天 | 否 |
| `push_log.json` | 推播紀錄 | 近 30 天 | 否 |
| `push_log_archive.json` | 推播紀錄歸檔 | 超過 30 天 | 否 |
| `journal/*.md` | 瑣碎記憶 | 逐字對話 | 否（只累積） |
| `kg.json` | 知識圖譜 | 先修 DAG | 否 |
| `concepts.json` | 概念節點 | 語意概念、來源論文、先修概念、作答歷史 | 否 |
| `kyc.json` | 學習者畫像觀察 | 思考模式、興趣訊號 | 否 |
| `ref_ledger.json` | 文獻核實登記簿 | 公開書目資料 | 否 |
| `論文閱讀.xlsx` | 閱讀紀錄主檔 | A–M 欄 | 否 |
| `paper_xlsx_pending.json` | 佇列 | Excel 開著時暫存 | 寫入後自動清 |
| `nutrition_roadmap.json`／`nutrition_log.json` | 營養軌 | 藍圖／紀錄 | 否 |
| `roadmap.json` | 已停用 | 舊 52 週主軌藍圖，程式不再讀 | — |
| `memory.json.migrated.bak` | 遺留 | 舊單檔記憶的備份 | — |

## 歸檔輪替（`mem_consolidate` 每日自動）
- 導師記憶淡出項 → `memory/archive.json`（不刪）。
- `learner.json` episodic >45 天 → `learner_archive.json`；`push_log.json` >30 天 → `push_log_archive.json`。
- 歸檔不損失功能：等級推導、升層資格、防重都仍涵蓋歸檔內容。
