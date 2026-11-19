# 指令速查

> 目錄：../CLAUDE.md

## 什麼時候用
- 忘記指令怎麼打。每個指令「什麼時候用、驗收標準」請看右欄的細則。
- 全部在專案資料夾執行：`python3 mentor.py <指令>`（營養軌用 `python3 nutrition.py`）。

## 每日推播
| 指令 | 用途 | 細則 |
|---|---|---|
| `integrity` | 完整性檢查（先跑 `python3 -m py_compile mentor.py`） | `integrity.md` |
| `daily_brief` | 每日短讀 | `daily_push.md` |
| `week_plan new` / `week_plan show` | 每週重排想法軸輪轉＋黑名單 | `daily_push.md` |
| `check_dup --title ".." [--url ".."]` | 程式化防重 | `paper_selection.md` |
| `kg_add --id <pid> --title .. --domain .. [--prereqs "a\|\|b"] [--level N] [--spontaneous] [--entry]` | 論文入圖 | `knowledge_graph.md` |
| `kg_check --id <pid>` | 先修守門 | `knowledge_graph.md` |
| `kg_frontier [domain]` / `kg_show [domain]` / `kg_link --id .. --prereqs .. [--remove]` / `kg_seed` | 前沿／樹狀／改邊／首建 | `knowledge_graph.md` |
| `mem_add ... --rubric ".." --pid ..` / `trend_add` | 寫回導師記憶 | `mentor_memory.md` |
| `push_log --papers ".." [--dry]` / `push_log --show [N]` | 推播驗收 | `push_log.md` |
| `mem_consolidate` / `learner_state` / `snapshot` | 收尾 | `daily_push.md` |
| `mem_context` / `mem_view [layer]` | 看導師記憶 | `mentor_memory.md` |

## 文獻與論文庫
| 指令 | 用途 | 細則 |
|---|---|---|
| `python3 refcheck.py check\|manual\|audit_xlsx\|ledger ...` | 文獻核實 | `refcheck.md` |
| `kb_search ".." [--k 5]` / `kb_read <id> [--pages ..] [--section ..]` / `kb_queue --url ..` | paper-kb | `paper_kb.md` |

## 互動與評估
| 指令 | 用途 | 細則 |
|---|---|---|
| `deep <id>` / `rubric <id>` | 出深度題／讀審查標準 | `deep_eval.md` |
| `review --paper <id> --result pass\|fail --depth 0-4 [--blindspots ..] [--note ..] [--skills ..]` | 記錄裁決 | `deep_eval.md` |
| `recall_related --paper <id>` / `recall --paper <id> --result .. --how mentioned\|asked\|followup ...` / `recall_due [--all]` | 順帶驗收舊概念 | `recall.md` |
| `review_mode pick` / `concept_add` / `concept_log` / `concepts` / `kyc_add` / `kyc_show` | 概念複習＋學習者畫像（三篇都不喜歡、考我） | `review_mode.md` |
| `skill_map [--rebuild]` | 技能地圖 | `learner_state.md` |
| `reset_learner` | 重置使用者端（保留導師記憶） | `learner_state.md` |
| `light_checkin [--note ..] [--interest ..] [--date ..]` | 打卡 | `light_mode.md` |
| `redirect_clear` | 清除方向回饋提示 | `redirect.md` |
| `streak` | 連續天數（只在使用者主動問） | `streak.md` |

## done 收尾
| 指令 | 用途 | 細則 |
|---|---|---|
| `journal_add --user ".." --mentor ".." --tag .. --domain .. --title ..` / `journal_list` | 逐字保存 | `journal.md` |
| `paper_xlsx --pid .. --journal .. --question .. --context .. [--title --url --year --authors --bg] [--replace] [--dry]` / `paper_xlsx --flush` | 寫 論文閱讀.xlsx | `paper_xlsx.md` |
| `python3 sheetsync.py rows N` / `rows 2-<末列>` / `header` | 匯出給 Google Sheet | `sheet_sync.md` |

## 營養軌
| 指令 | 用途 |
|---|---|
| `nutrition.py brief` / `check_dup --title ..` / `log --topic .. --kind ..` / `roadmap_set --week N ..` / `show` / `streak` | 見 `nutrition.md` |

## 其他（少用）
- `boot` / `status` / `groups` / `tree [domain]` / `calibrate ...`

## 已停用（不要用）
- `roadmap_set`（主軌 52 週藍圖）、`weekly_review`、`daily`（舊 curated PAPERS 流程）、`assess`（舊關鍵詞評分，僅離線後備）。
