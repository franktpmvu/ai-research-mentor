# 指令速查（Commands Reference）— docs/commands.md

> 入口：../CLAUDE.md。

## 指令速查
```
── 每日流程（順序）──
integrity                                 0. 完整性檢查（壞了停手，禁手改 JSON）
week_plan new [--week N --notes "..."]    每週一次·長讀規劃（roadmap 空白→先 roadmap_set）
week_plan show / daily_brief              檢視週計畫 / 每日短讀
check_dup --title "..." [--url "..."]     程式化重複判定（掃記憶+episodic+push_log 各含歸檔）
kg_check --id <pid>                        先修守門（main 每篇必跑）：🟢可推/🔴LOCKED禁跳(exit3)/UNKNOWN先kg_add
kg_add --id <pid> --title .. --domain .. [--prereqs "a||b"] [--level N] [--spontaneous]  放新論文入圖(接先修邊)
kg_frontier [domain] / kg_show [domain]   列可推前沿 / 樹狀看進度   ·  kg_link --id <p> --prereqs "a||b" [--remove]
mem_add / trend_add                       寫回導師記憶（含 rubric、--pid）；wild 軌免 mem_add；新論文先強制核實
refcheck check|text|manual|audit_xlsx|ledger   文獻強制核實（也可 python3 refcheck.py ...；規則見 docs/refcheck.md）
push_log --papers "..." --dry             呈現前預檢：驗組成/anchor/main 的 KG 守門，不寫檔（未過 exit 3 → 換片再呈現）
push_log --papers "pid::role[::anchor|::title][::url]||..."  推播驗收：3主+≥1跨域+1金融+3wild；
                                          xdomain/finance 必填 anchor；wild 第三欄填標題、第四欄填 url（建議）；
                                          main 每篇驗 KG（LOCKED/UNKNOWN → exit 3）
                                          ★ wild 一律附第四欄 url，check_dup 才能靠 URL/arXiv id 擋同一篇重推
push_log --show [N]                       檢視近 N 天推播
mem_consolidate / learner_state / snapshot    收尾（consolidate 附帶歸檔輪替）

── 習慣統計／超輕量模式（2026-08-05，只在使用者主動詢問時執行 streak）──
streak                                    總互動天數 + 目前連續天數（僅主動查詢時顯示，不進自動流程）
light_checkin [--note "..."] [--interest "..."] [--date YYYY-MM-DD]
                                           超輕量完成一天（免深讀評估）；--interest 記錄方向回饋供下次規劃
redirect_clear                            清除待處理的方向回饋提示（重新搜尋、調整推薦後執行）

── 順帶驗收舊概念／技能地圖（2026-11-11，規則見 learner_eval.md）──
recall_related --paper <id>               討論某篇時：列出它的先修/同技能舊概念（只給導師看）
recall --paper <id> --result pass|fail --how mentioned|asked|followup [--depth N --note .. --blindspots "a||b"]
                                           記錄舊概念驗收：pass 拉長間隔；單次 fail 只記盲區（連錯兩次才扣分）
recall_due [--all]                        （選用）使用者主動說「考我」時才用
skill_map [--rebuild]                     ASCII 技能地圖（0–5 級）；review/recall 自動更新

── 論文知識庫 paper-kb（2026-11-11，規則見 paper_kb.md；沒裝會自動略過）──
kb_search "<英文關鍵字>" [--k 5]          全文搜尋（附頁碼、para_id）
kb_read <doc_id|arXiv> [--pages 3,4] [--section ..]   讀原文段落（不帶範圍只印大綱）
kb_queue --url <網址>                      排進 paper-kb 下載佇列

── 藍圖 ──
roadmap_set --week N --cv "..." --llm "..." --diffusion "..." [--criteria_cv "a||b" ... --force]

── 評估與記憶 ──
rubric <id> / review --paper <id> --result pass|fail [--depth 0-4 ...]
journal_add --user "..." [--mentor "..." --tag slug --domain D --title "..."] / journal_list
paper_xlsx --pid ID --journal f1,f2 --question q.txt --context ctx.txt [--title --url --year --authors --bg] [--replace] [--dry] / paper_xlsx --flush   # 寫入 論文閱讀.xlsx（規則見 learner_eval.md）
boot / daily / status / groups / tree [domain] / mem_context / mem_view [layer]
learner_state / reset_learner / weekly_review <w> "a1" "a2" "a3" / calibrate ...

── 營養學獨立軌（2026-08-10，用 python3 nutrition.py，與 mentor.py 分離）──
nutrition.py brief                        每日短讀：本週主題(理論+實作)、近14則防重、本季主題
nutrition.py check_dup --title "..."       主題防重（🟢CLEAR 才推）
nutrition.py log --topic "..." --kind theory|practice|both [--note ..] [--url ..]   記錄今日推播
nutrition.py roadmap_set --week N --theme .. --theory .. --practice ..   滾動擴充空白週
nutrition.py show / nutrition.py streak    看藍圖 / 看連續天數(僅主動查詢)
```

> 註：`week_plan new` 把輪轉基準存進 `state.json`（`axis_base`/`xsrc_base`），每週自動 +7 前進不重複。
