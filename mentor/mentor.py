#!/usr/bin/env python3
"""
AI Research Mentor OS — Atomic Habit Edition v2
Usage: python mentor.py <command> [args]

Commands:
  boot                               系統啟動
  daily                              今日 Hook（從 group 隨機抽取）
  teaser <paper_id>                  5分鐘 Teaser
  deep <paper_id>                    深入閱讀 + 評估問題
  status                             進度儀表板
  groups                             查看所有論文 group 與狀態
  tree [domain]                      學習依賴樹
  snapshot                           輸出狀態快照
  load_snapshot <json>               還原狀態
  weekly_review <w> "a1" "a2" "a3"  週回顧
  calibrate <cv> <llm> <diff> <min> "<motivation>"

  ── LLM-as-judge 評估（取代關鍵詞比對）──
  rubric <paper_id>                  顯示該論文的審查標準（供 LLM 判讀）
  review --paper <id> --result pass|fail [--depth N --domain D --blindspots "a||b" --note "..."]
  assess <paper_id> "<answer>"       （LEGACY 關鍵詞比對，離線後備）

  ── 導師層級記憶（memory.json，累積資產）──
  mem_add --title "..." --domain D [--url --summary --importance N --rubric "a||b" --questions "..." --pid slug]
  mem_consolidate                    記憶自優化（升層/淡出）
  mem_context                        推薦前必讀的記憶脈絡摘要
  mem_view [layer]                   檢視各層記憶
  trend_add --name "..." [--domain D --note "..."]

  ── 學習者記憶（learner.json，可重置）──
  learner_state                      評估學習進度 + 自動升降級
  reset_learner                      重置學習者記憶與進度（保留導師研究記憶）

  ── 瑣碎記憶（journal/，逐字原始互動，只累積不重置）──
  journal_add --user "..." [--mentor "..." --tag slug --domain D --title "..."]
  paper_xlsx --pid ID --journal f1,f2 --question q.txt --context ctx.txt [--title --url --year --authors --bg --replace --dry | --flush]  寫入 論文閱讀.xlsx
                                     以時間點命名保存原始對話 + 內嵌兩種記憶快照
  journal_list                       列出所有瑣碎記憶

  ── 省 token 分層流程（驗證/輪轉/規劃/盤點全程式化）──
  week_plan new [--week N --notes "..."]  每週一次：排定 7 天想法軸/跨域輪轉 + 黑名單快照（讀長文）
  week_plan show                          顯示現行週計畫
  daily_brief                             每日輕量：compact 今日計畫 + 近7天黑名單 + 本週執行驗證
  check_dup --title "..." [--url "..."]   程式化重複判定（正規化+Jaccard），取代 LLM 目視照合
  push_log --papers "pid::role[::anchor|::title]||..."   記錄當日推播＋驗組成
                                           （3主+≥1跨域+1金融+3趣味wild；跨域/金融必填 anchor；
                                            wild 免 anchor，第三欄填標題即可，免 mem_add）
  push_log --show [N]                      檢視近 N 天推播紀錄
  roadmap_set --week N --cv "..." --llm "..." --diffusion "..."   滾動擴充藍圖：該週三軌目標寫回 roadmap.json
  integrity                                檔案完整性檢查（每日流程開頭；壞了停手，禁止手改 JSON 繞過）

  ── 習慣統計 / 超輕量模式（2026-08-05）──
  streak                                   總互動天數 + 目前連續天數（只在主動查詢時顯示，不進自動流程）
  light_checkin [--note "..."] [--interest "..."] [--date YYYY-MM-DD]
                                            超輕量完成一天（免深讀評估）；--interest 會記錄方向回饋供下次重新規劃
  redirect_clear                           清除待處理的方向回饋標記（重新搜尋、調整推薦後執行）

  ── 間隔抽考 + 技能地圖（2026-11-11，借鏡 Jane Street socratic-tutor）──
  recall_related --paper <id>              討論某篇時：列出它的先修/同技能、已通過的舊概念（順帶驗收用，只給導師看）
  recall --paper <id> --result pass|fail --how mentioned|asked|followup [--depth N --blindspots "a||b" --note ..]
                                            記錄舊概念驗收：pass 拉長下次間隔；fail 記盲區、間隔歸零（連錯兩次才扣分）
  recall_due [--all]                       （選用）使用者主動說「考我」時，列出最該複習的舊概念
  skill_map [--rebuild]                    ASCII 技能地圖（0–5 級）；--rebuild 依全部歷史重算

  ── 論文知識庫 paper-kb 整合（2026-11-11；沒裝 paper-kb 時這些指令只提示、不報錯）──
  kb_search "<英文關鍵字>" [--k 5]          在你讀過/收藏的論文全文裡搜尋（附頁碼、para_id）
  kb_read <doc_id|arXiv編號> [--pages 3,4] [--section Method]   讀原文段落（核實機制用）
  kb_queue --url <論文網址>                 排進 paper-kb 下載佇列（下次 paper-kb 維護時下載、解析、索引）
"""

import json, sys, os, random
from datetime import date, datetime, timedelta

BASE        = os.path.dirname(os.path.abspath(__file__))
STATE_FILE  = os.path.join(BASE, "state.json")
ROAD_FILE   = os.path.join(BASE, "roadmap.json")
MEMORY_FILE = os.path.join(BASE, "memory.json")   # 遺留單檔（2026-07-11 起遷移為 memory/ 切檔，原檔改名 .migrated.bak）
# ── 記憶切檔 + 歸檔輪替（2026-07-11）──
# memory/ 目錄：meta.json / trends.json / layer_<層>.json ×5 / archive.json（淡出項，不刪除）
# learner_archive.json：episodic 超過 EPISODIC_ARCHIVE_DAYS 天自動搬入（評估/防重仍讀取）
# push_log_archive.json：push_log 超過 PUSHLOG_ARCHIVE_DAYS 天自動搬入（防重仍讀取）
# 目的：主檔永遠保持小，LLM 永不直接 Read 大 JSON；程式讀 JSON 不耗 token。
MEMORY_DIR           = os.path.join(BASE, "memory")
MEMORY_ARCHIVE_FILE  = os.path.join(MEMORY_DIR, "archive.json")
LEARNER_ARCHIVE_FILE = os.path.join(BASE, "learner_archive.json")
PUSHLOG_ARCHIVE_FILE = os.path.join(BASE, "push_log_archive.json")
EPISODIC_ARCHIVE_DAYS = 45
PUSHLOG_ARCHIVE_DAYS  = 30
# 瑣碎記憶（raw interaction journal）：每次互動以時間點命名，逐字保存原始對話，
# 並「快照」當下的導師記憶 + 學習者記憶，作為可追溯的原始素材。不重置、只累積。
JOURNAL_DIR = os.path.join(BASE, "journal")

# ─────────────────────────────────────────────────────────
# Paper metadata schema
#
# group_id  = "{domain}_{difficulty}_{type}"
#   domain      : cv | llm | diffusion
#   difficulty  : basic | advanced | hard
#   type        : foundation | application
#   week_range  : [start_week, end_week]  (inclusive)
#
# Papers sharing the same group_id are INTERCHANGEABLE:
# the planner randomly rotates through unseen ones first,
# then cycles back through all.
# ─────────────────────────────────────────────────────────

PAPERS = {

    # ══════════════════════════════════════════════════════
    # CV ▸ basic ▸ foundation  (Week 1–3)
    # 消除手工設計的偵測 pipeline
    # ══════════════════════════════════════════════════════
    "detr": {
        "id": "detr", "domain": "cv", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "DETR — End-to-End Object Detection with Transformers",
        "url": "https://arxiv.org/abs/2005.12872",
        "hook_headline": "把『找東西』變成『配對遊戲』——NMS 消失了",
        "hook_summary": "DETR 用 Hungarian bipartite matching 保證每個物件只輸出一個框，直接消除 NMS。把 detection 變成 set prediction 問題。",
        "concept_map": """\
  舊：圖片→1000候選框→NMS刪重複→結果   ← 麻煩
  新：圖片→Encoder→100 query→Decoder→Hungarian配對→結果  ← 一步到位""",
        "curiosity_hook": "配對這麼優雅，為什麼訓練要跑 500 epoch？YOLO 只要幾十個？",
        "teaser_analogy": "100個男生相親 N 個女生，Hungarian 保證總體最佳配對，每個女生只配一次——query 就是男生，GT box 是女生。",
        "teaser_key_insight": "Transformer 沒有 locality bias，attention 初始是隨機的，得從零學會看哪裡，所以收斂慢。",
        "deep_questions": [
            "DETR 如何透過 Hungarian algorithm 實現 one-to-one matching？為何能消除 NMS？",
            "訓練收斂慢的根本原因是什麼？後來的改進論文如何解決？"
        ],
        "keywords": ["hungarian","bipartite","one-to-one","nms","set prediction","收斂","encoder","decoder","query"]
    },

    "anchor_free": {
        "id": "anchor_free", "domain": "cv", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "FCOS — Fully Convolutional One-Stage Object Detection",
        "url": "https://arxiv.org/abs/1904.01355",
        "hook_headline": "不用預設框——讓每個像素點自己預測物件",
        "hook_summary": "FCOS 拋棄 anchor box，讓 feature map 上每個點直接預測到物件邊界的距離（l, t, r, b），加上 centerness 分數壓制離中心太遠的低質量框。",
        "concept_map": """\
  Anchor-based：預設成千個框 → 每個框判斷是否為物件 → 調整框
  FCOS：每個像素點 → 預測 (l, t, r, b, centerness) → 直接是框""",
        "curiosity_hook": "沒有 anchor 怎麼處理同一個點被多個物件覆蓋的情況（FPN 多尺度如何分工）？",
        "teaser_analogy": "你站在房間裡，不用事先放捲尺，直接估計你到四面牆的距離——這就是 FCOS 每個點做的事。",
        "teaser_key_insight": "Centerness score = √(min(l,r)/max(l,r) × min(t,b)/max(t,b))，懲罰偏離中心的預測，大幅減少低質量框。",
        "deep_questions": [
            "FCOS 的 centerness branch 解決了什麼問題？為何不用 NMS 就能壓制假陽性？",
            "FPN 多尺度在 FCOS 中如何分配不同大小的物件？"
        ],
        "keywords": ["centerness","fcos","anchor-free","ltrb","fpn","多尺度","像素","直接回歸"]
    },

    # ══════════════════════════════════════════════════════
    # CV ▸ advanced ▸ foundation  (Week 1–4)
    # query 設計的演進
    # ══════════════════════════════════════════════════════
    "dab_detr": {
        "id": "dab_detr", "domain": "cv", "difficulty": "advanced", "type": "foundation",
        "week_range": [1, 4],
        "title": "DAB-DETR — Dynamic Anchor Boxes are Better Queries",
        "url": "https://arxiv.org/abs/2201.12329",
        "hook_headline": "DETR 的 query 是盲的——DAB-DETR 給它座標眼睛",
        "hook_summary": "把 DETR 的隨機 query 換成 4D anchor box (x,y,w,h)，讓 attention 天生有定位能力，收斂從 500→50 epoch。",
        "concept_map": """\
  DETR：   [隨機向量] → 慢慢學位置（500 epoch）
  DAB-DETR：[x,y,w,h] → attention 直接聚焦該區域（50 epoch）""",
        "curiosity_hook": "anchor 是動態更新的還是固定的？給了位置先驗後模型還能自由調整嗎？",
        "teaser_analogy": "給新員工指定工作區（不是讓他自己摸索），效率提升 10 倍。anchor 是引導，不是鎖死——每層 decoder 都會更新它。",
        "teaser_key_insight": "用 anchor (x,y,w,h) 調製 attention 的 key positional encoding，讓 attention map 天然空間對齊。",
        "deep_questions": ["DAB-DETR 的 anchor query 如何在 decoder 各層動態更新？這與 DETR 固定 query 有何本質差異？"],
        "keywords": ["anchor","4d","dynamic","modulated","收斂","位置","decoder layer","更新"]
    },

    "conditional_detr": {
        "id": "conditional_detr", "domain": "cv", "difficulty": "advanced", "type": "foundation",
        "week_range": [1, 4],
        "title": "Conditional DETR — Conditional Cross-Attention for Fast DETR",
        "url": "https://arxiv.org/abs/2108.06152",
        "hook_headline": "讓 cross-attention 先看邊緣再看內容——收斂快 10 倍",
        "hook_summary": "Conditional DETR 把 cross-attention 的 spatial query 和 content query 分開，讓模型先定位再識別，解決 DETR 初期 attention 發散的問題。",
        "concept_map": """\
  DETR cross-attention：query 同時學位置+內容，互相干擾
  Conditional：空間 query（位置）+ 內容 query（語意）→ 分工合作""",
        "curiosity_hook": "空間和內容分開之後，attention map 的可視化長什麼樣？",
        "teaser_analogy": "先看地圖定位（空間），再讀路標辨識（內容）——兩件事分開做比同時做更快收斂。",
        "teaser_key_insight": "將 reference point 從 content embedding 中解耦，讓 spatial attention 純粹聚焦幾何，大幅減少訓練需要的 epoch。",
        "deep_questions": ["Conditional DETR 如何解耦 spatial 和 content cross-attention？這在梯度流上有什麼好處？"],
        "keywords": ["conditional","spatial","content","解耦","cross-attention","reference point","收斂","梯度"]
    },

    # ══════════════════════════════════════════════════════
    # CV ▸ basic ▸ application  (Week 2–5)
    # 開放詞彙與分割應用
    # ══════════════════════════════════════════════════════
    "sam": {
        "id": "sam", "domain": "cv", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "SAM — Segment Anything Model",
        "url": "https://arxiv.org/abs/2304.02643",
        "hook_headline": "點一下任何東西，AI 幫你框出來",
        "hook_summary": "SAM 是 Meta 訓練的通用分割模型，給一個點/框/文字提示就能分割任意物件，不需要重新訓練。用 1B 個 mask 訓練，泛化能力極強。",
        "concept_map": """\
  傳統分割：針對特定類別訓練（貓、車、人...）
  SAM：     任意提示 → 通用分割
            [點擊位置] ↘
            [邊界框]   → Prompt Encoder → Mask Decoder → 分割結果
            [文字描述] ↗""",
        "curiosity_hook": "SAM 的 mask 品質在醫療影像、衛星圖像這些訓練集之外的域表現如何？",
        "teaser_analogy": "SAM 是分割界的 GPT——通用基礎模型，downstream 任務只需提示，不需微調。",
        "teaser_key_insight": "Prompt encoder 把幾何提示（點/框）轉成和 image embedding 同空間的向量，讓 mask decoder 能跨模態對齊。",
        "deep_questions": ["SAM 的 promptable segmentation 如何做到 zero-shot？image encoder 和 prompt encoder 分別學什麼？"],
        "keywords": ["prompt","zero-shot","image encoder","mask decoder","通用","分割","泛化","點擊","邊界框"]
    },

    "grounding_dino": {
        "id": "grounding_dino", "domain": "cv", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "Grounding DINO — Open-Set Detection with Language",
        "url": "https://arxiv.org/abs/2303.05499",
        "hook_headline": "輸入文字就能找到圖裡任何東西",
        "hook_summary": "Grounding DINO 把 DINO（強力 DETR 變體）和語言模型結合，用文字描述當 query，實現 open-vocabulary detection——沒見過的類別也能偵測。",
        "concept_map": """\
  傳統 detection：訓練80類 → 只能找這80類
  Grounding DINO：文字「一隻紅色的貓坐在書上」→ 直接定位""",
        "curiosity_hook": "open-vocabulary detection 和 image-text matching（CLIP）的根本差異是什麼？",
        "teaser_analogy": "CLIP 告訴你『這張圖有貓』，Grounding DINO 告訴你『貓在左上角那個框裡』。",
        "teaser_key_insight": "Feature fusion 讓視覺特徵和文字特徵在 cross-attention 中互相增強，而非只在輸出端匹配。",
        "deep_questions": ["Grounding DINO 如何實現語言-視覺特徵融合？與 CLIP 的 contrastive learning 有何本質差異？"],
        "keywords": ["open-vocabulary","grounding","fusion","cross-modal","文字","定位","clip","contrastive"]
    },

    # ══════════════════════════════════════════════════════
    # LLM ▸ basic ▸ foundation  (Week 1–3)
    # Transformer 核心
    # ══════════════════════════════════════════════════════
    "attention": {
        "id": "attention", "domain": "llm", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "hook_headline": "為什麼 AI 讀句子不用從頭讀到尾？",
        "hook_summary": "Attention 讓每個 token 直接問所有其他 token「你跟我有多相關？」加權求和——不用順序，不會忘遠的字。Multi-Head 同時從多個角度看。",
        "concept_map": """\
  RNN：蘋果→很→好→吃→我→喜歡→它  （遠距依賴容易消失）
  Attention：「它」直接對「蘋果」打 0.9 分，加權取用""",
        "curiosity_hook": "Attention 每個 token 看全部 token，計算量是 O(n²)，長文章怎麼辦？",
        "teaser_analogy": "Query=你的問題，Key=書名，Value=書內容。打分數、加權讀。Multi-Head=派 8 個人各找不同面向的資料。",
        "teaser_key_insight": "除以 √d_k 防止高維時點積過大導致 softmax 飽和，梯度消失。",
        "deep_questions": [
            "Scaled Dot-Product Attention 為何除以 √d_k？從梯度角度解釋。",
            "Multi-Head 相較單頭的核心優勢是什麼？"
        ],
        "keywords": ["sqrt","dk","梯度","softmax","飽和","multi-head","query","key","value","parallel"]
    },

    "bert": {
        "id": "bert", "domain": "llm", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "BERT — Pre-training of Deep Bidirectional Transformers",
        "url": "https://arxiv.org/abs/1810.04805",
        "hook_headline": "同時看左邊和右邊——雙向理解的革命",
        "hook_summary": "GPT 只看左邊預測下一個字。BERT 用 Masked LM 遮住 15% 的字，讓模型同時用左右文脈預測——理解能力大幅提升，各種 NLP 任務微調一下就 SOTA。",
        "concept_map": """\
  GPT（單向）：我 喜歡 吃 [預測→] 蘋果
  BERT（雙向）：我 喜歡 [MASK] 蘋果 → 預測「吃」（左右都看）""",
        "curiosity_hook": "BERT 這麼強，為什麼現在主流都是 GPT 系列而不是 BERT 系列？",
        "teaser_analogy": "填空題（BERT）和寫作題（GPT）。填空需要雙向理解，寫作只能看之前的字——兩種訓練方式培養不同能力。",
        "teaser_key_insight": "Masked LM 讓 encoder 學到深度雙向表示，但代價是不能做生成任務——預訓練目標決定了模型能力的邊界。",
        "deep_questions": ["BERT 的 Masked LM 和 Next Sentence Prediction 各解決什麼問題？為何後來研究發現 NSP 效果存疑？"],
        "keywords": ["masked","bidirectional","双向","nsp","finetune","預訓練","遮住","填空","encoder"]
    },

    # ══════════════════════════════════════════════════════
    # LLM ▸ advanced ▸ foundation  (Week 1–4)
    # 位置編碼演進
    # ══════════════════════════════════════════════════════
    "rope": {
        "id": "rope", "domain": "llm", "difficulty": "advanced", "type": "foundation",
        "week_range": [1, 4],
        "title": "RoPE — Rotary Position Embedding (Roformer)",
        "url": "https://arxiv.org/abs/2104.09864",
        "hook_headline": "讓 AI 感知相對距離而非絕對位置",
        "hook_summary": "把位置信息編碼成旋轉角度，attention score 自動只依賴兩個 token 的相對距離，外推性遠好於 sinusoidal。幾乎所有現代大模型（LLaMA/Qwen/Gemma）都在用。",
        "concept_map": """\
  傳統：token_m + 固定向量_m → 超出訓練長度就沒向量了
  RoPE：token_m 旋轉 m 角度，attention = f(m-n)，只看相對距離""",
        "curiosity_hook": "RoPE 為什麼能外推到比訓練長度更長的序列？sinusoidal 不行？",
        "teaser_analogy": "時鐘指針：第 m 個 token 轉 m 格，第 n 個轉 n 格。夾角 = m-n，純粹相對，與絕對位置無關。",
        "teaser_key_insight": "旋轉矩陣的內積天然包含相對位置，且不需要學習額外參數，外推到更長序列時衰減平滑。",
        "deep_questions": ["RoPE 如何讓 attention score 只依賴相對位置？用數學推導說明。"],
        "keywords": ["旋轉","rotation","相對","inner product","外推","夾角","complex","絕對位置"]
    },

    "alibi": {
        "id": "alibi", "domain": "llm", "difficulty": "advanced", "type": "foundation",
        "week_range": [1, 4],
        "title": "ALiBi — Train Short, Test Long",
        "url": "https://arxiv.org/abs/2108.12409",
        "hook_headline": "不加位置向量——直接在 attention score 扣分",
        "hook_summary": "ALiBi 不用任何位置 embedding，而是在 attention score 加一個負的線性偏置（距離越遠扣越多分），訓練 1024 token 可外推到 2048 token 而不降質量。",
        "concept_map": """\
  傳統：attention(q,k) + position_embedding(q) + position_embedding(k)
  ALiBi：attention(q,k) - λ × |i-j|   （越遠扣越多，簡單有效）""",
        "curiosity_hook": "為什麼這麼簡單的方法外推性比 RoPE 還好？線性懲罰的直覺是什麼？",
        "teaser_analogy": "開會時離你越遠的人，你自然越難聽清楚——ALiBi 就是把這個物理直覺硬編碼進 attention。",
        "teaser_key_insight": "每個 attention head 有不同的 λ（懲罰斜率），自動學習不同的局部/全域關注模式。",
        "deep_questions": ["ALiBi 和 RoPE 在長度外推上各有什麼優勢？為什麼 ALiBi 不需要重新訓練就能外推？"],
        "keywords": ["alibi","線性","偏置","外推","懲罰","距離","head","斜率","不需要embedding"]
    },

    # ══════════════════════════════════════════════════════
    # LLM ▸ basic ▸ application  (Week 2–5)
    # 對齊與指令跟隨
    # ══════════════════════════════════════════════════════
    "instructgpt": {
        "id": "instructgpt", "domain": "llm", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "InstructGPT — Training with Human Feedback",
        "url": "https://arxiv.org/abs/2203.02155",
        "hook_headline": "讓模型學會聽話——不只是預測下一個字",
        "hook_summary": "GPT-3 很強但難用：它預測下一個字，不懂你要什麼。InstructGPT 用 RLHF（人類回饋強化學習）讓模型學會遵循指令，是 ChatGPT 的技術前身。",
        "concept_map": """\
  預訓練 GPT：預測下一個字（統計學習）
       ↓ SFT（有監督微調）
  學會基本指令格式
       ↓ Reward Model（人類打分）
  學會什麼回答人類喜歡
       ↓ PPO 強化學習
  InstructGPT：聽話、有用、無害""",
        "curiosity_hook": "RLHF 讓模型更聽話，但有沒有可能讓它變得更會說人類想聽的話而不是說真話？",
        "teaser_analogy": "預訓練 = 讀遍所有書。SFT = 學禮儀。RLHF = 根據老闆打分持續改進工作方式。",
        "teaser_key_insight": "Reward model 是瓶頸：人類打分有噪音，reward hacking（模型學會討好 reward model 而非真正有用）是至今未解的問題。",
        "deep_questions": ["RLHF 的三個階段各解決什麼問題？PPO 在這裡為何優於普通梯度下降？"],
        "keywords": ["rlhf","sft","reward","ppo","對齊","指令","人類","微調","強化學習","hacking"]
    },

    "lora": {
        "id": "lora", "domain": "llm", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "LoRA — Low-Rank Adaptation of Large Language Models",
        "url": "https://arxiv.org/abs/2106.09685",
        "hook_headline": "微調 1000 億參數的模型，只動幾百萬個",
        "hook_summary": "Full fine-tuning 要更新所有參數，成本巨大。LoRA 假設權重的更新矩陣是低秩的，只訓練兩個小矩陣 A、B（ΔW = BA），參數量減少 1000 倍，效果幾乎不差。",
        "concept_map": """\
  Full FT：W（10000×10000）全部更新 → 1億參數
  LoRA：   W 不動，只訓練 A（10000×8）和 B（8×10000）→ 16萬參數
           推理時：W_new = W + BA""",
        "curiosity_hook": "為什麼低秩假設成立？模型在 fine-tuning 時真的只改變了低秩的部分嗎？",
        "teaser_analogy": "你不用重寫整本教科書，只需在頁邊寫筆記（低秩更新）——推理時把筆記合回去就好。",
        "teaser_key_insight": "rank r 是超參數，r=8 通常就夠了。推理時 BA 合併進 W，無額外延遲。",
        "deep_questions": ["LoRA 的低秩假設數學上意味著什麼？為何 rank=4~16 通常就夠？"],
        "keywords": ["lora","低秩","rank","矩陣","a","b","delta","參數","微調","合併"]
    },

    # ══════════════════════════════════════════════════════
    # Diffusion ▸ basic ▸ foundation  (Week 1–3)
    # 擴散模型基礎
    # ══════════════════════════════════════════════════════
    "ddpm": {
        "id": "ddpm", "domain": "diffusion", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "DDPM — Denoising Diffusion Probabilistic Models",
        "url": "https://arxiv.org/abs/2006.11239",
        "hook_headline": "把『生成圖片』變成『學會橡皮擦』",
        "hook_summary": "先把圖片慢慢加雜訊到純噪音，再讓模型學每次去一點點噪音。生成時從噪音出發一步步去噪。學『去噪』比學『生成』容易得多。",
        "concept_map": """\
  前向（固定，不用學）：真實圖片→加噪→...→純噪音
  反向（模型要學）：    純噪音→去噪→...→生成圖片
  訓練目標：MSE(真實ε, 預測ε)  ← 超穩定""",
        "curiosity_hook": "既然要跑 1000 步，生成一張圖要很久？後來怎麼解決的？",
        "teaser_analogy": "學雕刻：先把雕像磨回石頭（加噪），再學逆操作（去噪）。前向有 closed-form：xₜ = √ᾱₜ x₀ + √(1-ᾱₜ) ε。",
        "teaser_key_insight": "預測 ε 比預測 x₀ 穩定：t 大時 x₀ 信號極弱，預測它很難；預測加了多少噪音，任何 t 難度相同。",
        "deep_questions": [
            "q(xₜ|x₀) 的 closed-form 是什麼？為何能直接採樣而不用跑 t 步？",
            "L_simple 為何比 L_vlb 訓練更穩定？"
        ],
        "keywords": ["alphabar","closed form","epsilon","elbo","重新參數化","加噪","去噪","前向","反向","穩定"]
    },

    "score_matching": {
        "id": "score_matching", "domain": "diffusion", "difficulty": "basic", "type": "foundation",
        "week_range": [1, 3],
        "title": "Score Matching — A Connection to Diffusion Models",
        "url": "https://arxiv.org/abs/2011.13456",
        "hook_headline": "擴散模型其實在學什麼？——梯度場",
        "hook_summary": "Yang Song 的視角：訓練 diffusion model 等同於學習 log p(x) 的梯度（score function）。去噪 = 沿著概率密度的梯度爬坡，每步讓 x 更像真實數據。",
        "concept_map": """\
  DDPM 視角：學去噪（預測加了多少噪音）
  Score 視角：學 ∇ₓ log p(x)（概率密度的梯度場）
  等價！去噪方向 = 梯度上升方向""",
        "curiosity_hook": "如果擴散模型在估計梯度場，能不能用 ODE 求解器代替 SDE 採樣？",
        "teaser_analogy": "山上的水往低處流（梯度下降）。反過來，score function 告訴噪音怎麼往概率密度高的地方走（梯度上升）。",
        "teaser_key_insight": "Score matching 的訓練目標和 DDPM 的 L_simple 在數學上等價，這統一了兩個看似不同的生成框架。",
        "deep_questions": ["score function ∇ₓ log p(x) 在物理上代表什麼？為何去噪等於沿 score 方向移動？"],
        "keywords": ["score","梯度","log p","sde","ode","等價","score matching","概率密度","朗之萬","採樣"]
    },

    # ══════════════════════════════════════════════════════
    # Diffusion ▸ advanced ▸ foundation  (Week 1–4)
    # 採樣加速
    # ══════════════════════════════════════════════════════
    "ddim": {
        "id": "ddim", "domain": "diffusion", "difficulty": "advanced", "type": "foundation",
        "week_range": [1, 4],
        "title": "DDIM — Denoising Diffusion Implicit Models",
        "url": "https://arxiv.org/abs/2010.02502",
        "hook_headline": "DDPM 要 1000 步，DDIM 用 50 步生成一樣的圖",
        "hook_summary": "把 Markov 鏈換成確定性 ODE：可以跳步，50 步=1000步效果，且同一噪音每次生成結果完全相同（可重現）。",
        "concept_map": """\
  DDPM（隨機）：x₁₀₀₀→x₉₉₉→...→x₀  （不能跳）
  DDIM（確定）：x₁₀₀₀────→x₈₀₀────→x₀  （跳步，結果可重現）""",
        "curiosity_hook": "確定性採樣有什麼用？同一噪音生成一樣的圖——這讓影像編輯成為可能？",
        "teaser_analogy": "DDPM 像走山路每步隨機，DDIM 像抄捷徑——知道目的地方向就能大步跨。",
        "teaser_key_insight": "DDIM 邊際分佈 q(xₜ|x₀) 與 DDPM 完全相同，所以同一個 DDPM 模型，直接套 DDIM 採樣公式就能加速，不用重新訓練。",
        "deep_questions": [
            "DDIM 的 non-Markovian process 如何保持與 DDPM 相同的邊際分佈？",
            "確定性採樣如何應用在影像編輯（DDIM inversion）？"
        ],
        "keywords": ["non-markovian","deterministic","確定性","marginal","跳步","inversion","加速","ode","重現"]
    },

    "dpm_solver": {
        "id": "dpm_solver", "domain": "diffusion", "difficulty": "advanced", "type": "foundation",
        "week_range": [2, 5],
        "title": "DPM-Solver — Fast ODE Solver for Diffusion",
        "url": "https://arxiv.org/abs/2206.00927",
        "hook_headline": "用數值 ODE 求解器讓 diffusion 只需 10~20 步",
        "hook_summary": "把 diffusion 的反向過程看成 ODE，用高階數值解法（類似 Runge-Kutta）代替一階 Euler，步數從 50 步降到 10-20 步，品質不降。",
        "concept_map": """\
  DDIM（一階）：每步線性近似，需要 50 步
  DPM-Solver（高階）：用更精確的積分近似，10步就夠""",
        "curiosity_hook": "ODE 求解器的階數越高越好嗎？為什麼實際上 2~3 階就夠了？",
        "teaser_analogy": "用梯形公式（二階）積分比矩形公式（一階）準，步數可以少很多——DPM-Solver 就是把這個道理用在 diffusion 上。",
        "teaser_key_insight": "利用 diffusion ODE 的半線性結構（linear + non-linear）推導出精確的高階積分格式，誤差比一般 ODE 求解器小。",
        "deep_questions": ["DPM-Solver 為何比 DDIM 需要更少步數？半線性結構在積分中發揮什麼作用？"],
        "keywords": ["ode","高階","積分","半線性","dpm","runge-kutta","步數","誤差","線性","非線性"]
    },

    # ══════════════════════════════════════════════════════
    # Diffusion ▸ basic ▸ application  (Week 2–5)
    # 條件控制應用
    # ══════════════════════════════════════════════════════
    "controlnet": {
        "id": "controlnet", "domain": "diffusion", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "ControlNet — Adding Conditional Control to Text-to-Image",
        "url": "https://arxiv.org/abs/2302.05543",
        "hook_headline": "用骨架、邊緣、深度圖精確控制生成的姿勢和結構",
        "hook_summary": "ControlNet 複製 UNet 的 encoder，接受額外的結構條件（骨架/邊緣/深度圖），讓生成結果精確符合幾何約束，且只需要微調複製出來的那一半。",
        "concept_map": """\
  原始 SD：文字 → 生成（但姿勢/結構難以精確控制）
  ControlNet：文字 + [骨架圖] → 生成（姿勢完全固定）
              凍結原始UNet + 只訓練複製的encoder""",
        "curiosity_hook": "為什麼要複製 encoder 而不是直接在原始模型上加條件？凍結原模型的好處是什麼？",
        "teaser_analogy": "原始模型是畫家的右手，ControlNet 是左手拿著參考圖——右手繼續畫，左手提供幾何約束。",
        "teaser_key_insight": "Zero convolution 初始化：新加的層初始全為零，訓練開始時不影響原始模型輸出，讓 fine-tuning 更穩定。",
        "deep_questions": ["ControlNet 的 zero convolution 如何確保訓練初始穩定性？為何要凍結原始 UNet？"],
        "keywords": ["controlnet","zero convolution","骨架","邊緣","深度","凍結","條件","複製","結構","unet"]
    },

    "ldm": {
        "id": "ldm", "domain": "diffusion", "difficulty": "basic", "type": "application",
        "week_range": [2, 5],
        "title": "LDM — Latent Diffusion Models (Stable Diffusion)",
        "url": "https://arxiv.org/abs/2112.10752",
        "hook_headline": "把擴散過程壓進小空間——Stable Diffusion 的核心",
        "hook_summary": "在像素空間跑 diffusion 很慢（512×512 很大）。LDM 先用 VAE 壓縮成 64×64 的 latent space，diffusion 在 latent 裡跑，生成完再解碼。速度快 10 倍以上。",
        "concept_map": """\
  原始 DDPM：在像素空間（512×512）跑 diffusion → 慢
  LDM：圖片 →[VAE Encoder]→ latent(64×64) →[Diffusion]→ latent →[VAE Decoder]→ 圖片
       速度快 10 倍，Stable Diffusion 就是這個""",
        "curiosity_hook": "壓到 latent space 之後，diffusion 學到的到底是什麼？是像素還是語意？",
        "teaser_analogy": "與其在原稿上修改（像素），不如先做縮圖（latent），改好再放大——效率高得多。",
        "teaser_key_insight": "VAE 的 perceptual loss + patch adversarial loss 確保 latent space 保留語意信息而不只是壓縮統計。",
        "deep_questions": ["LDM 為何在 latent space 而非 pixel space 做 diffusion？VAE 的訓練目標如何確保 latent 的品質？"],
        "keywords": ["latent","vae","encoder","decoder","壓縮","pixel","stable diffusion","perceptual","語意","空間"]
    },
}

# ─────────────────────────────────────────────
# Group helper
# ─────────────────────────────────────────────

def get_group_id(paper: dict) -> str:
    return f"{paper['domain']}_{paper['difficulty']}_{paper['type']}"

def get_papers_in_group(group_id: str, week: int) -> list:
    """Return all papers in a group valid for the given week."""
    return [
        p for p in PAPERS.values()
        if get_group_id(p) == group_id
        and p["week_range"][0] <= week <= p["week_range"][1]
    ]

def is_unlocked(paper: dict, passed_ids: set) -> bool:
    """A paper is unlocked if all its prereqs have been passed."""
    prereqs = paper.get("prereqs", [])
    return all(pid in passed_ids for pid in prereqs)

def pick_from_group(group_id: str, week: int, seen_ids: set, passed_ids: set) -> dict | None:
    """
    Pick a paper from the group using this priority:
    1. Unlocked + unseen  (ideal)
    2. Unlocked + seen but not passed  (retry candidate)
    3. Locked + unseen  (show as preview, clearly marked)
    Always prefer unseen within each tier; random within tie.
    """
    candidates = get_papers_in_group(group_id, week)
    if not candidates:
        return None

    unlocked_unseen = [p for p in candidates if is_unlocked(p, passed_ids) and p["id"] not in seen_ids]
    unlocked_seen   = [p for p in candidates if is_unlocked(p, passed_ids) and p["id"] in seen_ids and p["id"] not in passed_ids]
    locked_unseen   = [p for p in candidates if not is_unlocked(p, passed_ids) and p["id"] not in seen_ids]

    for pool in [unlocked_unseen, unlocked_seen, locked_unseen, candidates]:
        if pool:
            chosen = random.choice(pool)
            chosen["_locked"] = not is_unlocked(chosen, passed_ids)
            return chosen
    return None

def target_group_ids(state: dict, passed_ids: set) -> list[str]:
    """
    Return one group_id per domain.
    Logic:
      - If the learner has passed ≥1 paper in basic/foundation for a domain,
        upgrade target to advanced/foundation (or advanced/application on even weeks).
      - Otherwise stay at basic/foundation (or basic/application on even weeks).
    This makes group selection driven by actual progress, not just calibration level.
    """
    week = state["progress"]["current_week"]
    week_type = "foundation" if week % 2 == 1 else "application"

    # Count passed papers per domain×difficulty
    passed_by_group: dict[str, int] = {}
    for pid in passed_ids:
        if pid in PAPERS:
            gid = get_group_id(PAPERS[pid])
            passed_by_group[gid] = passed_by_group.get(gid, 0) + 1

    groups = []
    for domain in ["cv", "llm", "diffusion"]:
        basic_foundation_done = passed_by_group.get(f"{domain}_basic_foundation", 0) > 0
        adv_foundation_done   = passed_by_group.get(f"{domain}_advanced_foundation", 0) > 0

        if adv_foundation_done:
            difficulty = "hard" if passed_by_group.get(f"{domain}_advanced_foundation", 0) >= 2 else "advanced"
        elif basic_foundation_done:
            difficulty = "advanced"
        else:
            difficulty = "basic"

        # On even weeks, shift to application type if we have enough foundation
        if week_type == "application" and not basic_foundation_done:
            week_type_actual = "foundation"  # not ready for application yet
        else:
            week_type_actual = week_type

        groups.append(f"{domain}_{difficulty}_{week_type_actual}")
    return groups

# ─────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────

def _blank_state():
    """全新安裝（從 GitHub clone、沒有 state.json）時的初始狀態。等級一律從 A 起，之後由評估自動升降。"""
    return {
        "meta": {"version": "1.0", "created": str(date.today()), "last_updated": str(date.today())},
        "learner": {"cv_level": "A", "llm_level": "A", "diff_level": "A", "daily_minutes": 30,
                    "motivation": "", "level_floor": {"cv": "A", "llm": "A", "diffusion": "A"}},
        "progress": {"current_week": 1, "current_day": 1, "quarter": "Q1", "consecutive_active_days": 0,
                     "last_active_date": None, "throttle_mode": False,
                     "domain_balance": {"cv": 0, "llm": 0, "diffusion": 0},
                     "axis_base": 1, "xsrc_base": 1},
        "papers": [], "weekly_gates": {},
    }

def load(path):
    if not os.path.exists(path) and os.path.abspath(path) == os.path.abspath(STATE_FILE):
        st = _blank_state()       # 2026-11-11：全新安裝自動建立 state.json（舊安裝不受影響）
        save(path, st)
        print("  （首次執行：已建立 state.json；等級從 A 起，可用 calibrate 調整）")
        return st
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(path, data):
    d = json.loads(json.dumps(data))
    if "meta" in d:
        d["meta"]["last_updated"] = str(date.today())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# Hierarchical temporal memory — schema & config
# ─────────────────────────────────────────────

MEMORY_LAYERS = [
    ("week",      "近一週",   7,    "month"),
    ("month",     "近一月",   30,   "half_year"),
    ("half_year", "近半年",   182,  "year"),
    ("year",      "近一年",   365,  "long_term"),
    ("long_term", "長期核心", None, None),
]

# STANDARD promotion gate: importance>=7 OR seen_count>=2 bubbles an item up one layer.
PROMOTE_IMPORTANCE = 7
PROMOTE_SEEN_COUNT = 2

# Two physical stores, one logical view:
#   memory.json  = MENTOR memory  → 導師累積的研究知識（層級記憶 + 趨勢）。長期資產，不輕易重置。
#   learner.json = LEARNER memory → 使用者學習紀錄（通關/盲區/技能圖）。可分開重置，丟失重建即可。
# load_memory() 合併兩者供程式使用；save_mem() 依歸屬拆回兩檔。兩邊分項評估：
#   mem_consolidate() 評估導師記憶；learner_state() 評估使用者狀態。
LEARNER_FILE = os.path.join(BASE, "learner.json")

def _blank_memory():
    """MENTOR memory only."""
    layers = {}
    for name, label, window, nxt in MEMORY_LAYERS:
        layers[name] = {"label": label, "window_days": window,
                        "promote_to": nxt, "last_consolidated": None, "items": []}
    return {
        "meta": {"version": "2.0", "created": str(date.today()),
                 "last_updated": str(date.today()),
                 "schema": "hierarchical-temporal-mentor-memory"},
        "layers": layers,
        "trends": []
    }

def _blank_learner():
    """LEARNER memory only — resettable."""
    return {
        "meta": {"version": "2.0", "created": str(date.today()),
                 "last_updated": str(date.today()),
                 "schema": "learner-memory", "resettable": True},
        "episodic": [], "blind_spots": [],
        "skill_map": {k: {"covered": False, "depth": 0, "last_seen": None}
                      for k in ["DETR","Attention","DDPM","DDIM","LDM","LoRA","RLHF","ViT","RoPE","SAM"]}
    }

def _load_one(path, blank):
    if not os.path.exists(path):
        save(path, blank)
        return dict(blank), True
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        d = json.loads(raw) if raw else {}
    except (json.JSONDecodeError, ValueError):
        d = {}
    changed = False
    for k, v in blank.items():
        if k not in d:
            d[k] = v; changed = True
    return d, changed

def _load_json_or(path, default):
    """Tolerant loader for archive files."""
    if not os.path.exists(path):
        return default
    try:
        d = load(path)
        return d if isinstance(d, type(default)) else default
    except Exception:
        return default

def _mentor_layer_path(name):
    return os.path.join(MEMORY_DIR, f"layer_{name}.json")

def _save_mentor_split(mentor):
    """把導師記憶寫成 memory/ 切檔（meta/trends/layer_*.json）。"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    meta = dict(mentor.get("meta", _blank_memory()["meta"]))
    meta["last_updated"] = str(date.today())
    meta["schema"] = "hierarchical-temporal-mentor-memory-split"
    save(os.path.join(MEMORY_DIR, "meta.json"), meta)
    save(os.path.join(MEMORY_DIR, "trends.json"), mentor.get("trends", []))
    blank_layers = _blank_memory()["layers"]
    for name, *_ in MEMORY_LAYERS:
        layer = mentor.get("layers", {}).get(name, blank_layers[name])
        save(_mentor_layer_path(name), layer)

def _load_mentor_split():
    """讀 memory/ 切檔；若只有舊單檔 memory.json → 自動遷移切檔（舊檔改名 .migrated.bak 保留）。"""
    blank = _blank_memory()
    meta_p = os.path.join(MEMORY_DIR, "meta.json")
    if not os.path.exists(meta_p):
        mentor = dict(blank)
        if os.path.exists(MEMORY_FILE):
            try:
                legacy = load(MEMORY_FILE)
            except Exception:
                legacy = {}
            for k in ("meta", "layers", "trends"):
                if isinstance(legacy.get(k), type(blank[k])):
                    mentor[k] = legacy[k]
            # 遺留 learner 鍵先帶著，交給 load_memory() 的既有遷移邏輯處理
            for k in ("episodic", "blind_spots", "skill_map"):
                if k in legacy:
                    mentor[k] = legacy[k]
            _save_mentor_split(mentor)
            try:
                os.replace(MEMORY_FILE, MEMORY_FILE + ".migrated.bak")
                print(f"📦 memory.json 已遷移為 memory/ 切檔（原檔保留為 memory.json.migrated.bak）")
            except OSError:
                pass
        else:
            _save_mentor_split(mentor)
        return mentor
    mentor = {"meta": _load_json_or(meta_p, blank["meta"]),
              "trends": _load_json_or(os.path.join(MEMORY_DIR, "trends.json"), []),
              "layers": {}}
    for name, *_ in MEMORY_LAYERS:
        mentor["layers"][name] = _load_json_or(_mentor_layer_path(name), blank["layers"][name])
    return mentor

def load_memory():
    """
    Merged logical view of MENTOR (memory/ 切檔) + LEARNER (learner.json) memory.
    Repairs empty/corrupt/legacy/split files in place. Also migrates a legacy
    combined memory.json (which held episodic/blind_spots/skill_map) into learner.json,
    and a legacy single-file memory.json into the split memory/ store.
    """
    mentor = _load_mentor_split()
    m_changed = False
    learner, l_changed = _load_one(LEARNER_FILE, _blank_learner())

    # ensure all layers present in mentor store
    blank_layers = _blank_memory()["layers"]
    if "layers" not in mentor or not isinstance(mentor.get("layers"), dict):
        mentor["layers"] = blank_layers; m_changed = True
    else:
        for name, *_ in MEMORY_LAYERS:
            if name not in mentor["layers"]:
                mentor["layers"][name] = blank_layers[name]; m_changed = True

    # migrate legacy learner keys that were saved inside memory.json
    for k in ("episodic", "blind_spots", "skill_map"):
        if k in mentor:
            if not learner.get(k):
                learner[k] = mentor[k]; l_changed = True
            del mentor[k]; m_changed = True

    if m_changed: _save_mentor_split(mentor)
    if l_changed: save(LEARNER_FILE, learner)

    merged = dict(mentor)
    merged["episodic"]   = learner["episodic"]
    merged["blind_spots"] = learner["blind_spots"]
    merged["skill_map"]  = learner["skill_map"]
    merged["_meta_learner"] = learner.get("meta", {})
    return merged

def save_mem(mem):
    """Split the merged view back into the two physical stores."""
    mentor = {
        "meta": mem.get("meta", _blank_memory()["meta"]),
        "layers": mem.get("layers", {}),
        "trends": mem.get("trends", []),
    }
    learner = {
        "meta": mem.get("_meta_learner", _blank_learner()["meta"]),
        "episodic": mem.get("episodic", []),
        "blind_spots": mem.get("blind_spots", []),
        "skill_map": mem.get("skill_map", {}),
    }
    _save_mentor_split(mentor)
    save(LEARNER_FILE, learner)

def reset_learner():
    """
    Wipe LEARNER memory + progress, keep MENTOR research memory intact.
    Lets the user restart their learning journey without losing accumulated知識.
    """
    save(LEARNER_FILE, _blank_learner())
    state = load(STATE_FILE)
    state["progress"]["current_week"] = 1
    state["progress"]["current_day"] = 0
    state["progress"]["quarter"] = "Q1"
    state["progress"]["consecutive_active_days"] = 0
    state["progress"]["last_active_date"] = str(date.today())
    state["progress"]["throttle_mode"] = False
    state["progress"]["domain_balance"] = {"cv": 0, "llm": 0, "diffusion": 0}
    state["weekly_gates"] = {}
    state["learner"].pop("level_floor", None)
    save(STATE_FILE, state)
    print("♻️  已重置學習者記憶（learner.json + 進度）。導師研究記憶（memory/ 切檔）保留。")

def init_memory_if_missing():
    load_memory()

# ─────────────────────────────────────────────
# boot
# ─────────────────────────────────────────────

def boot():
    init_memory_if_missing()
    state = load(STATE_FILE)
    p = state["progress"]

    # 2026-08-05：節流/精簡模式已移除（超輕量模式 light_checkin 取代其功能——
    # 沒力氣深讀時直接超輕量打卡即可，不需要系統另外偵測「降頻」）。
    mem = load_memory()
    passed = [e for e in mem["episodic"] if e["status"] == "passed"]
    blind  = [b for b in mem["blind_spots"] if not b["resolved"]]

    print("=" * 54)
    print("  AI Research Mentor OS")
    print("=" * 54)
    print(f"  {date.today()}  |  Week {p['current_week']}  |  {p['quarter']}")
    b = p["domain_balance"]
    print(f"  通關: CV={b['cv']} LLM={b['llm']} Diff={b['diffusion']}  總={sum(b.values())}")
    if blind:
        print(f"  ⚡ 待釐清: {[x['concept'] for x in blind]}")
    print()
    print("  ▸ daily            今日 Hook（從 group 隨機抽取）")
    print("  ▸ teaser <id>      5分鐘比喻")
    print("  ▸ deep <id>        論文 + 評估問題")
    print("  ▸ groups           查看所有論文 group")
    print("=" * 54)

    save(STATE_FILE, state)
    return state

# ─────────────────────────────────────────────
# daily — Hook，從 group 隨機抽取
# ─────────────────────────────────────────────

def daily_push(week=None):
    state = load(STATE_FILE)
    p = state["progress"]
    w = week or p["current_week"]

    mem = load_memory()
    seen_ids   = {e["paper_id"] for e in mem["episodic"] if e["status"] in ("passed","hook_seen","teaser_seen","reading")}
    passed_ids = {e["paper_id"] for e in mem["episodic"] if e["status"] == "passed"}

    group_ids = target_group_ids(state, passed_ids)

    papers = []
    for gid in group_ids:
        paper = pick_from_group(gid, w, seen_ids, passed_ids)
        if paper:
            papers.append(paper)

    if not papers:
        print("⚠ 本週所有 group 的論文都讀過了，執行 weekly_review 解鎖下週。")
        return []

    # Update progress
    p["current_day"] += 1
    save(STATE_FILE, state)

    # Register in memory
    existing = {e["paper_id"] for e in mem["episodic"]}
    for paper in papers:
        if paper["id"] not in existing:
            mem["episodic"].append({
                "date": str(date.today()), "paper_id": paper["id"],
                "domain": paper["domain"], "group": get_group_id(paper),
                "status": "hook_seen", "qa_record": []
            })
    save_mem(mem)

    # Print
    emoji = {"cv": "🔍", "llm": "🧠", "diffusion": "🌊"}
    name  = {"cv": "CV", "llm": "LLM", "diffusion": "Diffusion"}
    diff_label = {"basic": "基礎", "advanced": "進階", "hard": "困難"}
    type_label = {"foundation": "基石", "application": "應用"}

    print(f"\n📬 Week {w} · Day {p['current_day']}")
    print("─" * 54)

    for paper in papers:
        em = emoji[paper["domain"]]
        dn = name[paper["domain"]]
        dl = diff_label[paper["difficulty"]]
        tl = type_label[paper["type"]]
        locked = paper.get("_locked", False)
        lock_badge = "  🔒 前置未完成（可預覽）" if locked else ""
        print(f"\n{em} [{dn}]  ▪ {dl} · {tl}{lock_badge}")
        print(f"   {paper['hook_headline']}")
        print()
        for line in paper["hook_summary"].strip().split("\n"):
            print(f"   {line}")
        print()
        print(paper["concept_map"])
        print(f"   💭 {paper['curiosity_hook']}")
        if locked:
            prereqs = paper.get("prereqs", [])
            prereq_titles = [PAPERS[pid]["title"].split("—")[0].strip() for pid in prereqs if pid in PAPERS]
            print(f"   ⚠ 建議先通過：{prereq_titles}")
        print(f"\n   ▸ 有興趣？  python mentor.py teaser {paper['id']}")
        print(f"   ▸ 直接深入？python mentor.py deep {paper['id']}")
        print()

    print("─" * 54)
    print("  沒興趣也沒關係，明天再說。習慣 > 完美。")
    return papers

# ─────────────────────────────────────────────
# groups — 查看 group 結構
# ─────────────────────────────────────────────

def show_groups():
    state = load(STATE_FILE)
    mem   = load_memory()
    w = state["progress"]["current_week"]
    passed_ids = {e["paper_id"] for e in mem["episodic"] if e["status"] == "passed"}
    seen_ids   = {e["paper_id"] for e in mem["episodic"]}

    # Collect groups
    from collections import defaultdict
    groups = defaultdict(list)
    for p in PAPERS.values():
        if p["week_range"][0] <= w <= p["week_range"][1]:
            groups[get_group_id(p)].append(p)

    diff_order  = {"basic": 0, "advanced": 1, "hard": 2}
    domain_order= {"cv": 0, "llm": 1, "diffusion": 2}
    type_order  = {"foundation": 0, "application": 1}

    diff_zh = {"basic": "基礎", "advanced": "進階", "hard": "困難"}
    type_zh = {"foundation": "基石", "application": "應用"}
    emoji   = {"cv": "🔍", "llm": "🧠", "diffusion": "🌊"}

    print(f"\n📚 論文 Groups — Week {w}")
    print("─" * 54)

    sorted_gids = sorted(groups.keys(), key=lambda g: (
        domain_order[g.split("_")[0]],
        diff_order[g.split("_")[1]],
        type_order[g.split("_")[2]]
    ))

    target = set(target_group_ids(state, passed_ids))

    for gid in sorted_gids:
        domain, diff, typ = gid.split("_")
        papers_in_group = groups[gid]
        marker = " ← 今日目標" if gid in target else ""
        print(f"\n  {emoji[domain]} {domain.upper()} · {diff_zh[diff]} · {type_zh[typ]}{marker}")
        for p in papers_in_group:
            if p["id"] in passed_ids:
                status = "✅"
            elif p["id"] in seen_ids:
                status = "👁"
            else:
                status = "  "
            unlocked = is_unlocked(p, passed_ids)
            lock_str = "" if unlocked else " 🔒"
            prereq_str = ""
            if not unlocked:
                missing = [pid for pid in p.get("prereqs",[]) if pid not in passed_ids]
                prereq_str = f"  (需先通過: {', '.join(missing)})"
            print(f"    {status} [{p['id']}]{lock_str} {p['title'][:44]}{prereq_str}")

    print("\n  ✅=通關  👁=已見過  🔒=前置未完成")
    print("─" * 54)

# ─────────────────────────────────────────────
# teaser / deep / assess
# ─────────────────────────────────────────────

def teaser(paper_id: str):
    if paper_id not in PAPERS:
        print(f"找不到 {paper_id}"); return
    p = PAPERS[paper_id]
    diff_zh = {"basic":"基礎","advanced":"進階","hard":"困難"}
    type_zh = {"foundation":"基石","application":"應用"}
    print(f"\n📖 Teaser — {p['title']}")
    print(f"   [{diff_zh[p['difficulty']]} · {type_zh[p['type']]}]")
    print("─" * 54)
    print("\n  【比喻】")
    for line in p["teaser_analogy"].strip().split("\n"):
        print(f"  {line}")
    print("\n  【核心洞見】")
    for line in p["teaser_key_insight"].strip().split("\n"):
        print(f"  ✦ {line}")
    print(f"\n  原文: {p['url']}")
    print(f"\n  ▸ 想繼續深入？python mentor.py deep {paper_id}")
    print("─" * 54)
    mem = load_memory()
    for e in mem["episodic"]:
        if e["paper_id"] == paper_id and e["status"] == "hook_seen":
            e["status"] = "teaser_seen"
    save_mem(mem)

def deep(paper_id: str):
    if paper_id not in PAPERS:
        print(f"找不到 {paper_id}"); return
    p = PAPERS[paper_id]
    print(f"\n🔬 Deep Dive — {p['title']}")
    print("─" * 54)
    print(f"  連結: {p['url']}")
    print("\n  讀完後回答（越深入評分越高）：")
    for i, q in enumerate(p["deep_questions"], 1):
        print(f"\n  Q{i}. {q}")
    print(f"\n  ▸ python mentor.py assess {paper_id} \"<你的回答>\"")
    print("─" * 54)
    mem = load_memory()
    for e in mem["episodic"]:
        if e["paper_id"] == paper_id:
            e["status"] = "reading"
    save_mem(mem)

PASS_THRESHOLD = 2

def assess(paper_id: str, answer: str):
    """
    LEGACY offline fallback — crude keyword matching. Prefer `review` (LLM-judged).
    Kept only so curated papers can be self-tested without an LLM in the loop.
    """
    print("⚠ 註：assess 為關鍵詞比對的離線後備。正式評估請用 LLM 判讀的 `review`。")
    if paper_id not in PAPERS:
        print(f"找不到 {paper_id}"); return
    paper = PAPERS[paper_id]
    al = answer.lower()
    hits = [kw for kw in paper["keywords"] if kw.lower() in al]
    depth = min(4, len(hits))
    depth_map = {0:"表層（未達標）",1:"表層（未達標）",2:"機制層 ✓",3:"推導層 ✓✓",4:"批判層 ✓✓✓"}
    passed = len(hits) >= PASS_THRESHOLD

    mem = load_memory()
    # Ensure paper exists in episodic (may be assessed directly without daily)
    existing_ids = {e["paper_id"] for e in mem["episodic"]}
    if paper_id not in existing_ids:
        mem["episodic"].append({
            "date": str(date.today()), "paper_id": paper_id,
            "domain": paper["domain"], "group": get_group_id(paper),
            "status": "reading", "qa_record": []
        })
    for ep in mem["episodic"]:
        if ep["paper_id"] == paper_id:
            ep["status"] = "passed" if passed else "failed"
            ep["qa_record"].append({
                "date": str(date.today()), "answer_excerpt": answer[:200],
                "hit_keywords": hits, "depth_score": depth,
                "result": "passed" if passed else "failed"
            })
            break
    if not passed:
        miss = [kw for kw in paper["keywords"] if kw.lower() not in al][:3]
        bid  = {b["concept"] for b in mem["blind_spots"]}
        for m in miss:
            if m not in bid:
                mem["blind_spots"].append({"concept":m,"detected_date":str(date.today()),
                                           "paper_id":paper_id,"resolved":False})
    save_mem(mem)

    if passed:
        state = load(STATE_FILE)
        state["progress"]["domain_balance"][paper["domain"]] += 1
        save(STATE_FILE, state)
        _check_week_completion()

    print(f"\n{'✅ PASS' if passed else '❌ FAIL'} — {paper['title']}")
    print(f"  深度: {depth_map[depth]}  (命中 {len(hits)}/{len(paper['keywords'])})")
    if hits: print(f"  命中: {hits}")
    if not passed:
        miss = [kw for kw in paper["keywords"] if kw.lower() not in al]
        print(f"  ⚡ 盲區: {miss[:4]}")
        print(f"  → 重試: python mentor.py assess {paper_id} \"<補充>\"")
    return "passed" if passed else "failed"

def _check_week_completion():
    state = load(STATE_FILE)
    mem   = load_memory()
    w = state["progress"]["current_week"]
    # Week complete = all TARGET groups have at least one passed paper
    passed_ids = {e["paper_id"] for e in mem["episodic"] if e["status"] == "passed"}
    target_gids = set(target_group_ids(state, passed_ids))
    groups_done = set()
    for pid in passed_ids:
        if pid in PAPERS:
            gid = get_group_id(PAPERS[pid])
            if gid in target_gids:
                groups_done.add(gid)
    if groups_done >= target_gids and not state["weekly_gates"].get(f"week_{w}", False):
        state["weekly_gates"][f"week_{w}"] = True
        print(f"\n🎉 Week {w} 目標 group 全通關！執行 weekly_review {w} 進行週回顧，解鎖 Week {w+1}")
    save(STATE_FILE, state)

# ─────────────────────────────────────────────
# weekly_review / snapshot / status / calibrate
# ─────────────────────────────────────────────

WEEKLY_REVIEW_QS = {
    1: ["不看論文，說明 DETR 和 DDPM 各消除了什麼『手工設計』的部分？",
        "DDPM 原論文最大的工程缺陷是什麼？後來怎麼解決？",
        "Attention QKV 配對和 Hungarian Matching 在思想上有什麼共同點？"]
}

def weekly_review(week: int, answers: list):
    if len(answers) < 3:
        print("需要 3 個回答"); return
    domain_kws = ["attention","ddpm","detr","matching","epsilon","nms","架構","缺陷","共同","設計","消除","手工","配對"]
    labels = ["概念重建","缺陷挖掘","跨領域連結"]
    scores = []
    for i, (ans, label) in enumerate(zip(answers, labels)):
        kw_hits = sum(1 for kw in domain_kws if kw in ans.lower())
        ok = len(ans.strip()) > 30 and kw_hits >= 2
        scores.append(ok)
        print(f"  {'✅' if ok else '❌'} Q{i+1} [{label}]")
    passed = sum(scores)
    print(f"\n週回顧: {passed}/3")
    if passed >= 2:
        state = load(STATE_FILE)
        state["progress"]["current_week"] += 1
        save(STATE_FILE, state)
        print(f"✅ 通過！Week {week+1} 解鎖。")
    else:
        print("❌ 未達 2/3，補強後重試。")

def snapshot():
    state = load(STATE_FILE)
    mem   = load_memory()
    snap = {
        "snapshot_date": str(date.today()),
        "week": state["progress"]["current_week"],
        "day":  state["progress"]["current_day"],
        "quarter": state["progress"]["quarter"],
        "throttle": state["progress"]["throttle_mode"],
        "domain_balance": state["progress"]["domain_balance"],
        "passed_papers": [e["paper_id"] for e in mem["episodic"] if e["status"] == "passed"],
        "blind_spots": [b["concept"] for b in mem["blind_spots"] if not b["resolved"]],
        "weekly_gates": state["weekly_gates"],
        "learner": state["learner"]
    }
    print("\n【SNAPSHOT — 貼給下一次的 Claude】")
    print("─" * 54)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    print("─" * 54)
    return snap

def load_snapshot(snap: dict):
    state = load(STATE_FILE)
    state["progress"]["current_week"]   = snap["week"]
    state["progress"]["current_day"]    = snap["day"]
    state["progress"]["quarter"]        = snap["quarter"]
    state["progress"]["throttle_mode"]  = snap["throttle"]
    state["progress"]["domain_balance"] = snap["domain_balance"]
    state["weekly_gates"]               = snap["weekly_gates"]
    state["learner"]                    = snap["learner"]
    save(STATE_FILE, state)
    mem = load_memory()
    existing = {e["paper_id"] for e in mem["episodic"]}
    for pid in snap.get("passed_papers", []):
        if pid not in existing:
            mem["episodic"].append({"paper_id":pid,"domain":PAPERS.get(pid,{}).get("domain","?"),
                                    "status":"passed","date":snap["snapshot_date"],"qa_record":[]})
        else:
            for e in mem["episodic"]:
                if e["paper_id"] == pid: e["status"] = "passed"
    mem["blind_spots"] = [{"concept":c,"detected_date":snap["snapshot_date"],"paper_id":"restored","resolved":False}
                          for c in snap.get("blind_spots",[])]
    save_mem(mem)
    print(f"✅ 已還原 Week {snap['week']} Day {snap['day']}")

def status():
    state = load(STATE_FILE)
    mem   = load_memory()
    p = state["progress"]
    b = p["domain_balance"]
    def bar(n): return "█"*min(n*2,10)+"░"*max(0,10-n*2)
    print("\n📊 Progress")
    print("─" * 40)
    print(f"  Week {p['current_week']}/52  {p['quarter']}")
    print(f"  CV        {bar(b['cv'])}  {b['cv']}")
    print(f"  LLM       {bar(b['llm'])}  {b['llm']}")
    print(f"  Diffusion {bar(b['diffusion'])}  {b['diffusion']}")
    blind = [x for x in mem["blind_spots"] if not x["resolved"]]
    if blind: print(f"\n  ⚡ 盲區: {[x['concept'] for x in blind]}")
    ep = {}
    for e in mem["episodic"]: ep[e["status"]] = ep.get(e["status"],0)+1
    if ep: print(f"  論文狀態: {ep}")
    print()

def calibrate(cv, llm, diff, minutes, motivation):
    state = load(STATE_FILE)
    state["learner"] = {"cv_level":cv,"llm_level":llm,"diff_level":diff,
                        "daily_minutes":int(minutes),"motivation":motivation}
    save(STATE_FILE, state)
    print(f"✅ 校準完成  CV:{cv} LLM:{llm} Diff:{diff}  {minutes}分/天")
    mem2 = load_memory()
    p2 = {e["paper_id"] for e in mem2["episodic"] if e["status"] == "passed"}
    print(f"   依你的程度，今日 group 目標：{target_group_ids(state, p2)}")


# ─────────────────────────────────────────────
# prereq_tree — 顯示每個 domain 的學習依賴樹
# ─────────────────────────────────────────────

def prereq_tree(domain_filter: str = None):
    """
    Print the prerequisite dependency tree for all papers.
    Nodes show pass status. Arrows show unlock relationships.
    """
    mem = load_memory()
    passed_ids = {e["paper_id"] for e in mem["episodic"] if e["status"] == "passed"}
    seen_ids   = {e["paper_id"] for e in mem["episodic"]}

    domains = [domain_filter] if domain_filter else ["cv", "llm", "diffusion"]
    emoji_map = {"cv": "🔍", "llm": "🧠", "diffusion": "🌊"}
    diff_zh   = {"basic": "基礎", "advanced": "進階", "hard": "困難"}
    type_zh   = {"foundation": "基石", "application": "應用"}

    def node_str(pid):
        p = PAPERS[pid]
        if pid in passed_ids:   marker = "✅"
        elif pid in seen_ids:   marker = "👁"
        elif is_unlocked(p, passed_ids): marker = "🔓"
        else:                   marker = "🔒"
        label = f"[{diff_zh[p['difficulty']]}·{type_zh[p['type']]}]"
        return f"{marker} {pid}  {label}  {p['title'].split('—')[0].strip()[:35]}"

    for domain in domains:
        em = emoji_map.get(domain, "")
        print(f"\n{em} {domain.upper()} 學習依賴樹")
        print("─" * 54)

        domain_papers = {pid: p for pid, p in PAPERS.items() if p["domain"] == domain}

        def domain_prereqs(pid):
            return [r for r in PAPERS[pid].get("prereqs", []) if r in domain_papers]

        roots = [pid for pid in domain_papers if not domain_prereqs(pid)]

        printed = set()
        def print_tree(pid, prefix="", is_last=True):
            if pid in printed:
                return
            printed.add(pid)
            connector = "└─ " if is_last else "├─ "
            print(f"  {prefix}{connector}{node_str(pid)}")
            children = [c for c, p in domain_papers.items()
                        if pid in p.get("prereqs", []) and c not in printed]
            for i, child in enumerate(children):
                ext = "   " if is_last else "│  "
                print_tree(child, prefix + ext, i == len(children) - 1)

        for i, root in enumerate(roots):
            print_tree(root, "", i == len(roots) - 1)

        cross = [(pid, p) for pid, p in PAPERS.items()
                 if p["domain"] == domain
                 and any(PAPERS[r]["domain"] != domain for r in p.get("prereqs", []) if r in PAPERS)]
        if cross:
            print(f"\n  ↔ 跨域依賴:")
            for pid, p in cross:
                ext_prereqs = [r for r in p.get("prereqs", [])
                               if r in PAPERS and PAPERS[r]["domain"] != domain]
                for ep in ext_prereqs:
                    ep_domain = PAPERS[ep]["domain"]
                    print(f"    {pid} ← {ep}  ({emoji_map[ep_domain]} {ep_domain})")

    print()
    print("  ✅=通關  👁=已見  🔓=已解鎖  🔒=前置未完成")
    print("─" * 54)


# ─────────────────────────────────────────────
# Prereq injection (must run before main)
# ─────────────────────────────────────────────

PREREQ_TREE = {
    "detr":             [],
    "anchor_free":      [],
    "dab_detr":         ["detr"],
    "conditional_detr": ["detr"],
    "sam":              ["detr", "anchor_free"],
    "grounding_dino":   ["dab_detr", "attention"],
    "attention":        [],
    "bert":             [],
    "rope":             ["attention"],
    "alibi":            ["attention"],
    "instructgpt":      ["bert", "attention"],
    "lora":             ["attention"],
    "ddpm":             [],
    "score_matching":   [],
    "ddim":             ["ddpm"],
    "dpm_solver":       ["ddim"],
    "ldm":              ["ddpm"],
    "controlnet":       ["ldm"],
}

for _pid, _prereqs in PREREQ_TREE.items():
    if _pid in PAPERS:
        PAPERS[_pid]["prereqs"] = _prereqs


# ─────────────────────────────────────────────
# Hierarchical temporal memory — operations (MENTOR side)
# ─────────────────────────────────────────────

def _parse_flags(args):
    """Parse '--key value' pairs (value optional -> True flag)."""
    out = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            key = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                out[key] = args[i + 1]; i += 2
            else:
                out[key] = True; i += 1
        else:
            i += 1
    return out

def _days_between(d1_str, d2=None):
    d2 = d2 or date.today()
    return (d2 - datetime.strptime(d1_str, "%Y-%m-%d").date()).days

def _find_item(mem, key_url=None, key_title=None):
    """Return (layer_name, item) for an existing memory item matching url or title."""
    for name, _l, _w, _n in MEMORY_LAYERS:
        for it in mem["layers"][name]["items"]:
            if key_url and it.get("url") and it["url"] == key_url:
                return name, it
            if key_title and it.get("title", "").strip().lower() == key_title.strip().lower():
                return name, it
    return None, None

def _split_multi(val):
    """Split a '||'-separated (or ';'/newline) string into a clean list."""
    if not isinstance(val, str) or not val:
        return []
    sep = "||" if "||" in val else (";" if ";" in val else "\n")
    return [s.strip() for s in val.split(sep) if s.strip()]

def mem_add(flags):
    """
    Add / reinforce a MENTOR memory item in the WEEK layer.

    KEY IDEA: whenever the mentor records a paper it ALSO stores a review rubric —
    what understanding must be demonstrated to pass. The LLM (not a keyword checker)
    later judges the learner's answer against this rubric via `review`.

    Re-seeing an existing item bumps seen_count + importance (reinforcement),
    which later triggers promotion to a higher layer.

    Flags: --title --domain
           [--summary --url --importance --type --tags
            --rubric "點1||點2||點3"   # 通過此論文審查所需展現的理解（由 LLM 撰寫）
            --questions "問1||問2"     # 深問（可選）
            --pid <slug>]             # 穩定識別碼（供 review/rubric 引用；預設自動產生）
    """
    mem = load_memory()
    title = flags.get("title")
    if not title:
        print("需要 --title"); return
    domain = flags.get("domain", "cross")
    url = flags.get("url", "") if isinstance(flags.get("url"), str) else ""
    importance = int(flags.get("importance", 5))
    rubric = _split_multi(flags.get("rubric", ""))
    questions = _split_multi(flags.get("questions", ""))
    layer, existing = _find_item(mem, key_url=url or None, key_title=title)
    if existing:
        existing["seen_count"] = existing.get("seen_count", 1) + 1
        existing["last_seen"] = str(date.today())
        existing["importance"] = max(existing.get("importance", 0), importance)
        if rubric:    existing["rubric"] = rubric
        if questions: existing["questions"] = questions
        save_mem(mem)
        print(f"🔁 已強化記憶（{layer}層）: {title[:40]}  seen={existing['seen_count']} imp={existing['importance']}")
        return
    tags_raw = flags.get("tags", "")
    pid = flags.get("pid") if isinstance(flags.get("pid"), str) else f"m{int(datetime.now().timestamp())}"
    item = {
        "id": pid,
        "type": flags.get("type", "paper"),
        "domain": domain,
        "title": title,
        "summary": flags.get("summary", "") if isinstance(flags.get("summary"), str) else "",
        "url": url,
        "importance": importance,
        "created": str(date.today()),
        "layer_entered": str(date.today()),
        "last_seen": str(date.today()),
        "seen_count": 1,
        "tags": [t for t in tags_raw.split(",") if t] if isinstance(tags_raw, str) else [],
        "rubric": rubric,
        "questions": questions,
    }
    mem["layers"]["week"]["items"].append(item)
    save_mem(mem)
    tag = "  +rubric" if rubric else "  ⚠無rubric"
    print(f"✅ 新增記憶（week層）: {title[:40]}  imp={importance}{tag}  pid={pid}")

def _learner_passed_ids(mem):
    """學習者已通過審查的 pid 集合（episodic status=passed，含歸檔）。升層資格之一。"""
    ids = {e.get("paper_id") for e in mem["episodic"] if e.get("status") == "passed"}
    ids |= {e.get("paper_id") for e in _load_json_or(LEARNER_ARCHIVE_FILE, [])
            if e.get("status") == "passed"}
    return ids

def _dwell_days(item):
    """該項目在「目前層」已停留的天數（漸進鞏固的時間門檻）。"""
    ref = item.get("layer_entered") or item.get("promoted_on") or item.get("created")
    if not ref:
        return 0
    try:
        return _days_between(ref)
    except Exception:
        return 0

def _qualifies_promotion(item, passed_ids=frozenset(), window=7, target=None):
    """
    升層條件（2026-07-07 修訂：修正 imp>=7 連日直通 long_term 的漏洞）：
      資格   = seen_count>=2 或 learner 已通過 或 importance>=7（imp 只是資格，不能免除停留）
      停留   = 在本層停留 >= 該層窗口的一半（week 層至少 3 天）
      long_term 入口額外門檻 = (learner 通過 且 imp>=8) 或 seen_count>=3
    """
    qual = (item.get("seen_count", 1) >= PROMOTE_SEEN_COUNT
            or item.get("importance", 0) >= PROMOTE_IMPORTANCE
            or item.get("id") in passed_ids)
    if not qual:
        return False
    need = max(3, (window or 7) // 2)
    if _dwell_days(item) < need:
        return False
    if target == "long_term":
        return ((item.get("id") in passed_ids and item.get("importance", 0) >= 8)
                or item.get("seen_count", 1) >= 3)
    return True

def mem_consolidate():
    """
    Memory self-optimization pass (MENTOR side). For each layer bottom→top:
      - qualifying items bubble UP one layer（資格: seen>=2 / learner passed / imp>=7，
        且需在本層停留 >= 窗口一半；long_term 入口需 (passed且imp>=8) 或 seen>=3）
      - stale non-qualifying items older than the layer window DECAY (dropped)
      - long_term never decays
    One consolidation moves an item at most one level up (gradual consolidation).
    """
    mem = load_memory()
    passed_ids = _learner_passed_ids(mem)
    promoted, decayed, decayed_items = [], [], []
    for name, label, window, nxt in MEMORY_LAYERS:
        layer = mem["layers"][name]
        if nxt is None:
            layer["last_consolidated"] = str(date.today())
            continue
        today = str(date.today())
        keep = []
        for it in layer["items"]:
            # items promoted earlier in THIS pass only move one level per run
            if it.get("promoted_on") == today:
                keep.append(it); continue
            if _qualifies_promotion(it, passed_ids, window, nxt):
                it["promoted_from"] = name
                it["promoted_on"] = today
                it["layer_entered"] = today
                it["seen_count"] = 1  # must re-earn the next promotion
                mem["layers"][nxt]["items"].append(it)
                promoted.append((it.get("title", "")[:34], name, nxt))
            elif window is not None and it.get("last_seen") and _days_between(it["last_seen"]) > window:
                decayed.append((it.get("title", "")[:34], name))
                # 淡出不刪除：移入 memory/archive.json（防重判定仍涵蓋）
                it["decayed_from"] = name
                it["decayed_on"] = today
                decayed_items.append(it)
            else:
                keep.append(it)
        layer["items"] = keep
        layer["last_consolidated"] = str(date.today())
    save_mem(mem)
    if decayed_items:
        arch = _load_json_or(MEMORY_ARCHIVE_FILE, [])
        arch.extend(decayed_items)
        os.makedirs(MEMORY_DIR, exist_ok=True)
        save(MEMORY_ARCHIVE_FILE, arch)
    ep_n, pl_n = _archive_rotate()
    print("\n🧠 記憶自優化（consolidation）")
    print("─" * 54)
    if promoted:
        print("  ⬆ 升層:")
        for t, a, b in promoted:
            print(f"     {a}→{b}  {t}")
    if decayed:
        print("  ⬇ 淡出（過期且不重要）:")
        for t, a in decayed:
            print(f"     {a}  {t}")
    if not promoted and not decayed:
        print("  （本次無升層或淡出）")
    counts = {n: len(mem['layers'][n]['items']) for n, *_ in MEMORY_LAYERS}
    print(f"  各層數量: {counts}")
    if decayed_items or ep_n or pl_n:
        print(f"  🗄 歸檔輪替: 淡出→memory/archive {len(decayed_items)} 筆 | "
              f"episodic(>{EPISODIC_ARCHIVE_DAYS}天)→learner_archive {ep_n} 筆 | "
              f"push_log(>{PUSHLOG_ARCHIVE_DAYS}天)→push_log_archive {pl_n} 筆")
    print("─" * 54)
    return {"promoted": promoted, "decayed": decayed}

def _archive_rotate():
    """歸檔輪替（每次 mem_consolidate 附帶執行）：
      - learner.json episodic 超過 EPISODIC_ARCHIVE_DAYS 天 → learner_archive.json（整筆搬移；
        評估 _domain_qa / _learner_passed_ids / 防重 仍讀取歸檔，等級推導不受影響）
      - push_log.json 超過 PUSHLOG_ARCHIVE_DAYS 天 → push_log_archive.json（防重仍讀取）
    主檔因此永遠保持小；歸檔檔只供程式讀取，LLM 不直接 Read。"""
    ep_n = pl_n = 0
    # episodic → learner_archive
    learner, _ = _load_one(LEARNER_FILE, _blank_learner())
    keep, move = [], []
    for e in learner.get("episodic", []):
        try:
            old = _days_between(e.get("date", str(date.today()))) > EPISODIC_ARCHIVE_DAYS
        except Exception:
            old = False
        (move if old else keep).append(e)
    if move:
        arch = _load_json_or(LEARNER_ARCHIVE_FILE, [])
        arch.extend(move)
        save(LEARNER_ARCHIVE_FILE, arch)
        learner["episodic"] = keep
        save(LEARNER_FILE, learner)
        ep_n = len(move)
    # push_log → push_log_archive
    logs = _load_pushlog()
    keep, move = [], []
    for e in logs:
        try:
            old = _days_between(e.get("date", str(date.today()))) > PUSHLOG_ARCHIVE_DAYS
        except Exception:
            old = False
        (move if old else keep).append(e)
    if move:
        arch = _load_json_or(PUSHLOG_ARCHIVE_FILE, [])
        arch.extend(move)
        save(PUSHLOG_ARCHIVE_FILE, arch)
        save(PUSHLOG_FILE, keep)
        pl_n = len(move)
    return ep_n, pl_n

def mem_view(layer_filter=None):
    mem = load_memory()
    print("\n🗂  層級記憶（導師）")
    print("─" * 54)
    for name, label, window, nxt in MEMORY_LAYERS:
        if layer_filter and name != layer_filter:
            continue
        items = mem["layers"][name]["items"]
        print(f"\n  【{label}】({name})  {len(items)} 筆")
        for it in sorted(items, key=lambda x: -x.get("importance", 0)):
            dom = it.get("domain", "?")
            print(f"    ▪ [{dom}] imp{it.get('importance',0)} ×{it.get('seen_count',1)}  {it.get('title','')[:44]}")
    blind = [b for b in mem["blind_spots"] if not b["resolved"]]
    if blind:
        print(f"\n  ⚡ 未解盲區: {[b['concept'] for b in blind]}")
    if mem.get("trends"):
        print(f"  📈 趨勢: {[t.get('name', t) if isinstance(t, dict) else t for t in mem['trends']]}")
    print("─" * 54)

def mem_context():
    """
    Compact memory digest for the morning recommender to read BEFORE searching.
    Prioritizes long-term core, then recent layers, blind spots & trends.
    """
    mem = load_memory()
    print("\n📎 記憶脈絡（推薦前必讀）")
    print("=" * 54)
    for name in ["long_term", "year", "half_year", "month", "week"]:
        items = mem["layers"][name]["items"]
        if not items:
            continue
        label = mem["layers"][name]["label"]
        top = sorted(items, key=lambda x: -x.get("importance", 0))[:4]
        print(f"\n  {label}:")
        for it in top:
            extra = ("  — " + it["summary"][:40]) if it.get("summary") else ""
            print(f"    • [{it.get('domain','?')}] {it.get('title','')[:46]}{extra}")
    blind = [b['concept'] for b in mem["blind_spots"] if not b["resolved"]]
    if blind:
        print(f"\n  ⚡ 補強盲區: {blind}")
    if mem.get("trends"):
        print(f"  📈 追蹤趨勢: {[t.get('name', t) if isinstance(t, dict) else t for t in mem['trends']]}")
    print("\n  → 依上述記憶，今日搜尋時避免重複、優先延續脈絡與補強盲區。")
    print("=" * 54)

def trend_add(flags):
    """Record a detected research trend. --name required, [--domain --note]"""
    mem = load_memory()
    name = flags.get("name")
    if not name or name is True:
        print("需要 --name"); return
    for t in mem["trends"]:
        if isinstance(t, dict) and t.get("name") == name:
            t["last_seen"] = str(date.today())
            t["count"] = t.get("count", 1) + 1
            save_mem(mem)
            print(f"🔁 趨勢強化: {name} ×{t['count']}"); return
    mem["trends"].append({"name": name, "domain": flags.get("domain", "cross"),
                          "note": flags.get("note", "") if isinstance(flags.get("note"), str) else "",
                          "first_seen": str(date.today()),
                          "last_seen": str(date.today()), "count": 1})
    save_mem(mem)
    print(f"📈 新趨勢: {name}")


# ─────────────────────────────────────────────
# learner_state — 自動升降級 + 學習者狀態報告 (LEARNER side)
# ─────────────────────────────────────────────

LEVELS = ["A", "B", "C", "D"]  # 入門 → 機制 → 推導 → 批判
LEVEL_KEY = {"cv": "cv_level", "llm": "llm_level", "diffusion": "diff_level"}

def _domain_qa(mem, domain):
    recs = []
    for e in list(mem["episodic"]) + _load_json_or(LEARNER_ARCHIVE_FILE, []):
        pid = e.get("paper_id")
        dom = PAPERS[pid]["domain"] if pid in PAPERS else e.get("domain")
        if dom == domain:
            recs.extend(dict(q, _pid=pid) for q in e.get("qa_record", []))
    recs.sort(key=lambda q: q.get("date", ""))
    return recs

def _derive_level(mem, state, domain):
    recs = _domain_qa(mem, domain)
    # 深度不打折（北極星）：只有 depth>=2（機制層）的 pass 才計入升級分數
    # 2026-11-11：recall（抽考）紀錄不重複算 pass；抽考失敗照算 fail。
    #   新規則起算日之後的 review pass，需「之後的抽考通過」確認才算 1 分，否則 0.5 分（等級靠證明，不靠一次答對）。
    passes  = [q for q in recs if q.get("result") == "passed" and q.get("depth_score", 0) >= 2
               and q.get("judge") != "recall"]
    shallow = [q for q in recs if q.get("result") == "passed" and q.get("depth_score", 0) < 2
               and q.get("judge") != "recall"]
    fails   = [q for q in recs if q.get("result") == "failed" and q.get("judge") != "recall"]
    _last = {}
    for q in recs:                       # 順帶驗收：同一篇連續兩次答錯才算一次 fail（單次答錯只記盲區）
        if q.get("judge") != "recall":
            continue
        pid = q.get("_pid")
        if q.get("result") == "failed" and _last.get(pid) == "failed":
            fails.append(q); _last[pid] = None
        else:
            _last[pid] = q.get("result")
    confirmed = _recall_confirmed_pass_keys(mem)
    pts = 0.0
    for q in passes:
        if q.get("date", "") < RECALL_RULE_START or (q.get("_pid"), q.get("date")) in confirmed:
            pts += 1.0
        else:
            pts += 0.5
    unconf = sum(1 for q in passes if q.get("date", "") >= RECALL_RULE_START
                 and (q.get("_pid"), q.get("date")) not in confirmed)
    score = pts - 0.5 * len(fails)
    if   score >= 6: idx = 3
    elif score >= 3: idx = 2
    elif score >= 1: idx = 1
    else:            idx = 0
    tail = recs[-2:]
    if len(tail) == 2 and all(q.get("result") == "failed" for q in tail):
        idx = max(0, idx - 1)
    floor = state["learner"].get("level_floor", {}).get(domain)
    if floor in LEVELS:
        idx = max(idx, LEVELS.index(floor))
    avg_depth = round(sum(q.get("depth_score", 0) for q in passes) / max(1, len(passes)), 2)
    return LEVELS[idx], {"passes": len(passes), "fails": len(fails), "shallow": len(shallow),
                         "avg_depth": avg_depth, "score": score, "unconfirmed": unconf}

def learner_state(apply=True):
    """
    Assess learner progress from assessment history and (if apply) auto-adjust
    cv/llm/diff levels by at most one notch of net change per run.
    """
    state = load(STATE_FILE)
    mem = load_memory()
    if "level_floor" not in state["learner"]:
        state["learner"]["level_floor"] = {
            "cv": state["learner"].get("cv_level", "A"),
            "llm": state["learner"].get("llm_level", "A"),
            "diffusion": state["learner"].get("diff_level", "A"),
        }
    print("\n👤 學習者狀態評估")
    print("─" * 54)
    changes = []
    for domain in ["cv", "llm", "diffusion"]:
        key = LEVEL_KEY[domain]
        cur = state["learner"].get(key, "A")
        target, stats = _derive_level(mem, state, domain)
        ci, ti = LEVELS.index(cur), LEVELS.index(target)
        new = cur
        if apply and ti != ci:
            step = 1 if ti > ci else -1
            new = LEVELS[ci + step]
            state["learner"][key] = new
        arrow = f"  {cur}→{new}" if new != cur else f"  {cur}（維持）"
        flag = "⬆" if LEVELS.index(new) > ci else ("⬇" if LEVELS.index(new) < ci else "•")
        sh = f" 淺過{stats['shallow']}(不計分)" if stats.get("shallow") else ""
        if stats.get("unconfirmed"):
            sh += f" 待驗收確認{stats['unconfirmed']}(暫計0.5)"
        print(f"  {flag} {domain.upper():9}{arrow}   通過{stats['passes']} 失敗{stats['fails']} 均深{stats['avg_depth']}{sh}")
        if new != cur:
            changes.append((domain, cur, new))
    b = state["progress"]["domain_balance"]
    print(f"\n  領域平衡: CV={b['cv']} LLM={b['llm']} Diff={b['diffusion']}")
    blind = [x['concept'] for x in mem["blind_spots"] if not x["resolved"]]
    if blind:
        print(f"  ⚡ 待釐清盲區: {blind}")
    # 2026-08-05：不再自動印出連續互動天數（使用者主動要求 streak 指令才顯示，避免造成壓力）。
    if apply:
        save(STATE_FILE, state)
    print("─" * 54)
    return changes


# ─────────────────────────────────────────────
# review / rubric — LLM-as-judge assessment (取代關鍵詞比對)
# ─────────────────────────────────────────────

def _lookup_paper(paper_id):
    """Resolve a paper from curated PAPERS or mentor-memory items.
    Returns (domain, title, rubric_list, questions_list, source)."""
    if paper_id in PAPERS:
        p = PAPERS[paper_id]
        return p["domain"], p["title"], p.get("deep_questions", []), p.get("deep_questions", []), "curated"
    mem = load_memory()
    for name, *_ in MEMORY_LAYERS:
        for it in mem["layers"][name]["items"]:
            if it.get("id") == paper_id or it.get("title", "").strip().lower() == paper_id.strip().lower():
                return it.get("domain", "cross"), it.get("title", paper_id), \
                       it.get("rubric", []), it.get("questions", []), f"memory:{name}"
    return None, None, None, None, None

def rubric(paper_id):
    """Print the stored review rubric + questions so the LLM can judge against it."""
    domain, title, rub, qs, src = _lookup_paper(paper_id)
    if domain is None:
        print(f"找不到 {paper_id}（不在 PAPERS 也不在導師記憶）"); return
    print(f"\n📋 審查標準 — {title}")
    print(f"   來源: {src}  領域: {domain}")
    print("─" * 54)
    if rub:
        print("  【通過所需展現的理解（rubric）】")
        for i, r in enumerate(rub, 1):
            print(f"   {i}. {r}")
    else:
        print("  （此論文尚無 rubric；curated 論文以 deep_questions 為評估依據）")
    if qs and qs is not rub:
        print("\n  【深問】")
        for i, q in enumerate(qs, 1):
            print(f"   Q{i}. {q}")
    print("─" * 54)
    print("  → LLM 依上述標準判讀學習者回答，再以 `review` 記錄裁決。")

def review(flags):
    """
    Record an LLM-judged verdict. The JUDGMENT is made by the LLM (reading the
    rubric via `rubric <id>` + the learner's answer); this command只負責寫回狀態。

    Flags: --paper <id> --result pass|fail
           [--depth 0-4  --domain cv|llm|diffusion
            --blindspots "概念1||概念2"  --note "一句評語"]
    """
    paper_id = flags.get("paper")
    result = flags.get("result")
    if not paper_id or result not in ("pass", "fail"):
        print('用法: review --paper <id> --result pass|fail [--depth N --domain D --blindspots "a||b" --note "..."]')
        return
    passed = result == "pass"
    depth = int(flags.get("depth", 3 if passed else 1))
    domain, title, _rub, _qs, src = _lookup_paper(paper_id)
    if domain is None:
        domain = flags.get("domain", "cross"); title = paper_id
    if isinstance(flags.get("domain"), str):
        domain = flags["domain"]
    blindspots = _split_multi(flags.get("blindspots", ""))
    note = flags.get("note", "") if isinstance(flags.get("note"), str) else ""

    mem = load_memory()
    existing_ids = {e["paper_id"] for e in mem["episodic"]}
    group = get_group_id(PAPERS[paper_id]) if paper_id in PAPERS else f"{domain}_memory"
    if paper_id not in existing_ids:
        mem["episodic"].append({
            "date": str(date.today()), "paper_id": paper_id,
            "domain": domain, "group": group, "status": "reading", "qa_record": []
        })
    for ep in mem["episodic"]:
        if ep["paper_id"] == paper_id:
            ep["status"] = "passed" if passed else "failed"
            ep["qa_record"].append({
                "date": str(date.today()), "judge": "llm",
                "result": "passed" if passed else "failed",
                "depth_score": depth, "note": note[:300], "blindspots": blindspots
            })
            break
    if not passed:
        bid = {b["concept"] for b in mem["blind_spots"]}
        for c in blindspots:
            if c not in bid:
                mem["blind_spots"].append({"concept": c, "detected_date": str(date.today()),
                                           "paper_id": paper_id, "resolved": False})
    else:
        for b in mem["blind_spots"]:
            if b.get("paper_id") == paper_id:
                b["resolved"] = True
    touched = _skill_apply(mem, paper_id, title, "review", passed, depth,
                           _split_multi(flags.get("skills", "")) if isinstance(flags.get("skills"), str) else [])
    save_mem(mem)
    if touched:
        print(f"  🗺 技能地圖更新：{touched}")
    if passed and depth >= 2:
        print("  🔗 已列入順帶驗收：之後討論相關論文時，導師會順便確認這個概念還記得")

    if passed and depth < 2:
        print("  ⚠ pass 但 depth<2（未達機制層）：不計升級分數、不推進領域。請追問至機制層後重判。")
    if passed and depth >= 2 and domain in ("cv", "llm", "diffusion"):
        state = load(STATE_FILE)
        state["progress"]["domain_balance"][domain] += 1
        save(STATE_FILE, state)
        _check_week_completion()

    depth_map = {0: "表層", 1: "表層", 2: "機制層 ✓", 3: "推導層 ✓✓", 4: "批判層 ✓✓✓"}
    print(f"\n{'✅ PASS' if passed else '❌ FAIL'} — {title}  (LLM 裁決)")
    print(f"  深度: {depth_map.get(depth, depth)}   領域: {domain}")
    if note:
        print(f"  評語: {note}")
    if not passed and blindspots:
        print(f"  ⚡ 盲區（重讀後以 review 重判）: {blindspots}")
    return "passed" if passed else "failed"



# ─────────────────────────────────────────────
# 間隔抽考 recall + 技能地圖 skill_map（2026-11-11，借鏡 Jane Street socratic-tutor）
# 狀態完全由 qa_record 推導（judge="recall" 為抽考紀錄），不另存排程 → 不會不同步。
# ─────────────────────────────────────────────
RECALL_INTERVALS = [3, 7, 30, 90, 180]   # 第 n 輪抽考距上次通過的天數
RECALL_RULE_START = "2026-11-10"         # 此日之後的 review pass 需抽考確認才算滿分（之前的不追溯）
SKILL_LABELS = ["0 未聽過", "1 聽過", "2 跟得上", "3 有提示能做", "4 獨立能做", "5 能教/邊界"]

def _all_episodes():
    """[(entry, where)]：where = 'current' | 'archive'。"""
    mem = load_memory()
    out = [(e, "current") for e in mem["episodic"]]
    out += [(e, "archive") for e in _load_json_or(LEARNER_ARCHIVE_FILE, [])]
    return out

def _pid_records(episodes):
    by = {}
    for e, _w in episodes:
        pid = e.get("paper_id")
        if not pid:
            continue
        d = by.setdefault(pid, {"recs": [], "domain": e.get("domain")})
        d["recs"].extend(e.get("qa_record", []))
    for d in by.values():
        d["recs"].sort(key=lambda q: q.get("date", ""))
    return by

def _recall_schedule(recs):
    """依時間重播 qa_record → (stage, anchor_date, next_due) 或 None（未在排程中）。"""
    stage, anchor = None, None
    for q in recs:
        ok = q.get("result") == "passed" and q.get("depth_score", 0) >= 2
        if q.get("judge") == "recall":
            if stage is None:
                continue
            if ok:
                stage, anchor = stage + 1, q.get("date")
            else:
                stage, anchor = 0, q.get("date")   # 答錯：不退出排程，間隔歸零
        else:
            if ok:
                stage, anchor = 0, q.get("date")
            elif q.get("result") == "failed":
                stage, anchor = None, None
    if stage is None or not anchor:
        return None
    gap = RECALL_INTERVALS[min(stage, len(RECALL_INTERVALS) - 1)]
    due = datetime.strptime(anchor, "%Y-%m-%d").date() + timedelta(days=gap)
    return stage, anchor, due

def _recall_confirmed_pass_keys(mem=None):
    """{(pid, date)}：之後被抽考通過（且中間無失敗）確認過的 review pass。"""
    keys = set()
    for pid, d in _pid_records(_all_episodes()).items():
        pending = []
        for q in d["recs"]:
            ok = q.get("result") == "passed" and q.get("depth_score", 0) >= 2
            if q.get("judge") == "recall":
                if ok:
                    keys.update((pid, dt) for dt in pending); pending = []
                else:
                    pending = []
            elif ok:
                pending.append(q.get("date"))
            elif q.get("result") == "failed":
                pending = []
    return keys

def _recall_due_list(include_future=False):
    today = date.today()
    rows = []
    for pid, d in _pid_records(_all_episodes()).items():
        sch = _recall_schedule(d["recs"])
        if not sch:
            continue
        stage, anchor, due = sch
        if anchor == str(today):
            continue
        if due <= today or include_future:
            rows.append({"pid": pid, "stage": stage, "anchor": anchor, "due": due,
                         "overdue": (today - due).days, "domain": d["domain"],
                         "last_note": next((q.get("note", "") for q in reversed(d["recs"]) if q.get("note")), "")})
    rows.sort(key=lambda r: r["due"])
    return rows

def _title_of(pid):
    dom, title, *_ = _lookup_paper(pid)
    return title or pid

def recall_due(flags):
    rows = _recall_due_list(include_future=bool(flags.get("future")))
    print("\n🔁 間隔抽考 recall_due")
    print("─" * 54)
    if not rows:
        print("  今天沒有到期的抽考。"); print("─" * 54); return []
    show = rows if flags.get("all") or flags.get("future") else rows[:1]
    for r in show:
        tag = f"逾期{r['overdue']}天" if r["overdue"] > 0 else ("今天到期" if r["overdue"] == 0 else f"{-r['overdue']}天後")
        print(f"  • {r['pid']}  第{r['stage'] + 1}輪  {tag}  [{r['domain']}]  上次通過 {r['anchor']}")
        print(f"    {_title_of(r['pid'])[:70]}")
        if r["last_note"]:
            print(f"    上次評語（只給導師看，出題時別洩漏）：{r['last_note'][:90]}")
    if len(show) < len(rows):
        print(f"  （另有 {len(rows) - len(show)} 篇到期；一天只抽 1 篇，不用補考。--all 看全部）")
    print("─" * 54)
    print("  （選用）只在使用者主動說「考我」時用；平常改在對話中順帶驗收（recall_related）")
    return rows

def recall(flags):
    pid = flags.get("paper"); result = flags.get("result")
    if not pid or result not in ("pass", "fail"):
        print('用法: recall --paper <id> --result pass|fail [--depth N --blindspots "a||b" --note "..." --skills "a||b"]')
        return
    passed = result == "pass"
    depth = int(flags.get("depth", 2 if passed else 1))
    note = flags.get("note", "") if isinstance(flags.get("note"), str) else ""
    how = flags.get("how") if flags.get("how") in ("mentioned", "asked", "followup") else "asked"
    blind = _split_multi(flags.get("blindspots", "")) if isinstance(flags.get("blindspots"), str) else []
    by = _pid_records(_all_episodes())
    if pid not in by or not _recall_schedule(by[pid]["recs"]):
        print(f"  ⚠ {pid} 不在抽考排程中（尚未以 review 通過 depth≥2，或已退回重學）。"); return
    mem = load_memory()
    entry = next((e for e in mem["episodic"] if e.get("paper_id") == pid), None)
    if entry is None:   # 只在歸檔 → 在現行 episodic 開一筆承接（歸檔不動）
        entry = {"date": str(date.today()), "paper_id": pid, "domain": by[pid]["domain"],
                 "group": f"{by[pid]['domain']}_memory", "status": "passed", "qa_record": []}
        mem["episodic"].append(entry)
    prev_fail = next((q.get("result") == "failed" for q in
                     reversed(by[pid]["recs"]) if q.get("judge") == "recall"), False)
    entry["qa_record"].append({"date": str(date.today()), "judge": "recall", "how": how,
                               "result": "passed" if passed and depth >= 2 else "failed",
                               "depth_score": depth, "note": note[:300], "blindspots": blind})
    if not (passed and depth >= 2):
        have = {b["concept"] for b in mem["blind_spots"]}
        for c in blind:
            if c not in have:
                mem["blind_spots"].append({"concept": c, "detected_date": str(date.today()),
                                           "paper_id": pid, "resolved": False})
    title = _title_of(pid)
    ok = passed and depth >= 2
    touched = []
    if ok or prev_fail:                  # 單次答錯不降技能等級
        touched = _skill_apply(mem, pid, title, "recall", ok, depth,
                               _split_multi(flags.get("skills", "")) if isinstance(flags.get("skills"), str) else [])
    save_mem(mem)
    howzh = {"mentioned": "主動提及", "asked": "被問到", "followup": "追問後"}[how]
    print(f"\n{'✅ 舊概念驗收通過' if ok else '📝 舊概念有缺口'}（{howzh}）— {title}")
    sch = _recall_schedule(_pid_records(_all_episodes())[pid]["recs"])
    if ok:
        print(f"  下次需要驗收：{sch[2]} 之後（第{sch[0] + 1}輪）")
    else:
        print(f"  已記盲區、間隔歸零（{sch[2]} 後再碰到時優先驗收）。" + ("連續第二次 → 計 1 次 fail。" if prev_fail else "單次不扣分。"))
        if blind:
            print(f"  ⚡ 盲區：{blind}")
    if touched:
        print(f"  🗺 技能地圖更新：{touched}")

def recall_related(flags):
    """討論某篇論文時：找出它的 KG 祖先（≤3 層）與同技能的、已通過的舊概念，供導師在對話中順帶驗收。"""
    pid = flags.get("paper")
    if not pid or pid is True:
        print("用法: recall_related --paper <id>"); return []
    nodes = _load_kg().get("nodes", {})
    anc, frontier = {}, [(pid, 0)]
    while frontier:
        cur, d = frontier.pop(0)
        if d >= 3:
            continue
        for p in nodes.get(cur, {}).get("prereqs", []) or []:
            if p not in anc:
                anc[p] = d + 1; frontier.append((p, d + 1))
    sm = load_memory().get("skill_map", {})
    my_skills = set(_skill_match(sm, pid, _title_of(pid)))
    by = _pid_records(_all_episodes())
    today = date.today(); rows = []
    for q, d in by.items():
        if q == pid:
            continue
        sch = _recall_schedule(d["recs"])
        if not sch:
            continue
        shared = my_skills & set(_skill_match(sm, q, _title_of(q)))
        if q not in anc and not shared:
            continue
        stage, anchor, due = sch
        lastb = next((q2.get("blindspots") for q2 in reversed(d["recs"]) if q2.get("blindspots")), [])
        rows.append({"pid": q, "why": f"先修(距{anc[q]}層)" if q in anc else f"同技能{sorted(shared)}",
                     "due": due, "ready": due <= today, "stage": stage, "anchor": anchor,
                     "note": next((q2.get("note", "") for q2 in reversed(d["recs"]) if q2.get("note")), ""),
                     "blind": lastb})
    rows.sort(key=lambda r: (not r["ready"], r["due"]))
    print(f"\n🔗 順帶驗收候選 — {_title_of(pid)[:50]}（只給導師看）")
    print("─" * 54)
    if not rows:
        print("  沒有相關的已通過舊概念。"); print("─" * 54); return []
    for r in rows[:5]:
        st = "✅該驗收了" if r["ready"] else f"…{r['due']}後"
        print(f"  • {r['pid']}  {r['why']}  {st}  上次通過{r['anchor']}")
        if r["blind"]:
            print(f"    舊盲區：{r['blind'][:3]}")
        if r["note"]:
            print(f"    上次評語：{r['note'][:80]}")
    print("─" * 54)
    print("  使用者講對了→recall --how mentioned；講得含糊/錯→追問後 --how followup；")
    print("  沒提到但答案需要→最多問 1 題橋接 --how asked。都不相關就別硬問。")
    return rows

def _skill_aliases(key):
    return [a.strip() for a in key.split("/") if a.strip()]

def _skill_match(skill_map, pid, title):
    hay = f"{pid} {title or ''}"
    hits = []
    for k in skill_map:
        for a in _skill_aliases(k):
            pat = _re.escape(a.lower()).replace(r"\-", "[-_ ]?")
            if _re.search(rf"(?<![a-z0-9]){pat}|{pat}(?![a-z0-9])" if len(a) > 3
                          else rf"(?<![a-z0-9]){pat}(?![a-z0-9])", hay.lower().replace("_", " ")):
                hits.append(k); break
    return hits

def _skill_level(v):
    return v.get("level", v.get("depth", 0)) if isinstance(v, dict) else 0

def _skill_apply(mem, pid, title, kind, passed, depth, explicit=()):
    """依一次評估更新技能等級（0–5）。等級要靠證明：review 最多到 3，抽考通過才到 4，批判級抽考到 5。"""
    sm = mem.setdefault("skill_map", {})
    keys = list(dict.fromkeys(list(explicit) + _skill_match(sm, pid, title)))
    touched = []
    for k in keys:
        v = sm.setdefault(k, {"covered": False, "depth": 0, "last_seen": None})
        cur = _skill_level(v)
        if passed and depth >= 2:
            new = max(cur, 3) if kind == "review" else max(cur, 5 if depth >= 4 else 4)
        elif passed:
            new = max(cur, 2)
        else:
            new = max(1, cur - 1)
        v["level"] = new; v["covered"] = True; v["last_seen"] = str(date.today())
        if new != cur:
            touched.append(f"{k} {cur}→{new}")
    return touched

def skill_map(flags):
    mem = load_memory()
    sm = mem.get("skill_map", {})
    if flags.get("rebuild"):
        # 以 7/3 手動標記為起點，依全部歷史評估重播
        for v in sm.values():
            v["level"] = v.get("depth", 0)
        allrecs = []
        for pid, d in _pid_records(_all_episodes()).items():
            for q in d["recs"]:
                allrecs.append((q.get("date", ""), pid, q))
        allrecs.sort(key=lambda t: t[0])
        for dt, pid, q in allrecs:
            ok = q.get("result") == "passed"
            _skill_apply(mem, pid, _title_of(pid), "recall" if q.get("judge") == "recall" else "review",
                         ok, q.get("depth_score", 0))
            for k in _skill_match(sm, pid, _title_of(pid)):
                sm[k]["last_seen"] = dt
        save_mem(mem)
        print("  ♻ 已依全部歷史重算技能地圖")
    rows = sorted(sm.items(), key=lambda kv: (-_skill_level(kv[1]), kv[0]))
    tot = sum(_skill_level(v) for _, v in rows); mx = 5 * max(1, len(rows))
    pct = round(100 * tot / mx)
    bar = lambda n, w=10: "█" * round(n * w / 5) + "░" * (w - round(n * w / 5))
    print(f"\n🗺 技能地圖                            整體 {bar(tot * 5 / mx)} {pct}%")
    print("─" * 58)
    for k, v in rows:
        lv = _skill_level(v)
        print(f"  {k[:18]:18} [{bar(lv)}] {lv}/5  {SKILL_LABELS[lv][2:]:8} {v.get('last_seen') or ''}")
    print("─" * 58)
    print("  等級規則：review 通過最高 3；之後舊概念驗收通過才到 4；驗收答出邊界/批判(depth4)才到 5")


# ─────────────────────────────────────────────
# paper-kb 整合（2026-11-11）：直接讀 paper-kb 的 SQLite 索引（只讀），不需要 MCP 套件。
# 找 paper-kb 的順序：環境變數 PAPER_KB_ROOT → ../paper-kb（GitHub repo 版面）→ ../paper-rag-mcp（本機掛載）。
# ─────────────────────────────────────────────
def _kb_root():
    cands = [os.environ.get("PAPER_KB_ROOT", ""),
             os.path.join(os.path.dirname(BASE), "paper-kb"),
             os.path.join(os.path.dirname(BASE), "paper-rag-mcp")]
    for c in cands:
        if c and os.path.isdir(os.path.join(c, "src", "paper_kb")):
            return c
    return None

def _kb_db():
    root = _kb_root()
    if not root:
        print("  （找不到 paper-kb：設定環境變數 PAPER_KB_ROOT，或把它放在本專案旁邊的 paper-kb/ 資料夾。略過。）")
        return None, None
    dbp = os.path.join(root, "data", "derived", "index", "papers.db")
    if not os.path.exists(dbp):
        print(f"  （paper-kb 還沒有索引：先在 {root} 執行 maintain.bat 或 python update.py。略過。）")
        return root, None
    if os.path.join(root, "src") not in sys.path:
        sys.path.insert(0, os.path.join(root, "src"))
    from paper_kb import index as _kbi
    return root, (_kbi, _kbi.connect(dbp, readonly=True))

def kb_search(argv):
    q = " ".join(a for a in argv if not a.startswith("--") and not a.isdigit()) if argv else ""
    k = int(argv[argv.index("--k") + 1]) if "--k" in argv else 5
    if not q:
        print('用法: kb_search "<英文關鍵字>" [--k 5]'); return
    root, h = _kb_db()
    if not h:
        return
    kbi, db = h
    try:
        rows = kbi.search(db, q, k=k)
    except ValueError as e:
        print(f"  查詢錯誤：{e}"); return
    print(f"\n📚 paper-kb 全文搜尋：{q}")
    print("─" * 54)
    if not rows:
        print("  沒有命中（只比對關鍵字：請用論文裡會出現的英文字）")
    for r in rows:
        print(f"  • {r['title'][:60]}  [doc_id={r['doc_id']}] p.{r['page']}  {r['section'][:30]}")
        print(f"    {r['snippet'][:160]}")
        print(f"    para_id={r['para_id']}")
    print("─" * 54)

def kb_read(argv):
    if not argv:
        print("用法: kb_read <doc_id|arXiv編號> [--pages 3,4] [--section 關鍵字]"); return
    doc = argv[0]
    pages = [int(x) for x in argv[argv.index("--pages") + 1].split(",")] if "--pages" in argv else None
    section = argv[argv.index("--section") + 1] if "--section" in argv else None
    root, h = _kb_db()
    if not h:
        return
    kbi, db = h
    r = db.execute("SELECT doc_id, title FROM docs WHERE doc_id = ? OR arxiv = ? OR doi = ?", (doc, doc, doc)).fetchone()
    if not r:
        print(f"  paper-kb 裡沒有 {doc}（可先 kb_search 找 doc_id，或 kb_queue 排進下載佇列）"); return
    paras = kbi.get_paras(db, r[0], pages=pages, section=section)
    print(f"\n📄 {r[1]}  [doc_id={r[0]}]")
    if not pages and not section:
        secs = []
        for p in paras:
            if p["section"] and (not secs or secs[-1][0] != p["section"]):
                secs.append((p["section"], p["page"]))
        print("  章節大綱（整篇太長，請用 --pages 或 --section 指定）：")
        for s, pg in secs[:60]:
            print(f"   p.{pg}  {s}")
        return
    total = 0
    for p in paras:
        if total > 12000:
            print("  …（太長，已截斷；請縮小範圍）"); break
        print(f"\n  [p.{p['page']} · {p['section'][:40]} · {p['para_id']}]\n  {p['text']}")
        total += len(p["text"])

def kb_queue(flags):
    url = flags.get("url")
    if not url or url is True:
        print("用法: kb_queue --url <論文網址（arXiv abs/pdf 或 PDF 直連）>"); return
    root = _kb_root()
    if not root:
        print("  （找不到 paper-kb，略過；不影響導師系統。）"); return
    raw = os.path.join(root, "input_raw"); os.makedirs(raw, exist_ok=True)
    qf = os.path.join(raw, "url_queue.txt")
    have = open(qf, encoding="utf-8").read().split() if os.path.exists(qf) else []
    if url in have:
        print("  已在 paper-kb 下載佇列中。"); return
    m = _re.search(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})", url)
    try:
        root2, h = _kb_db() if m else (root, None)
        if h and m and h[1].execute("SELECT 1 FROM docs WHERE arxiv = ?", (m.group(1),)).fetchone():
            print(f"  paper-kb 已經有 arXiv {m.group(1)}，不用再下載。"); return
    except Exception:
        pass
    with open(qf, "a", encoding="utf-8") as f:
        f.write(url + "\n")
    print(f"  📥 已排進 paper-kb 下載佇列（下次 paper-kb 維護時下載、解析、索引）：{url}")

# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 瑣碎記憶 — raw interaction journal
# 設計：導師記憶(memory.json) 與 學習者記憶(learner.json) 保存「結構化、去蕪存菁」的知識；
#       瑣碎記憶(journal/) 保存「未經摘要的原始互動」——使用者每次回話都有價值，
#       日後可回溯重建。每份 journal 以時間點命名，並內嵌當下兩種記憶的快照。
# ─────────────────────────────────────────────

def _memory_snapshot_md():
    """Render a compact markdown snapshot of MENTOR + LEARNER memory at this moment."""
    mem = load_memory()
    try:
        state = load(STATE_FILE)
    except Exception:
        state = {}
    lines = []

    # ── 導師記憶快照 ──
    lines.append("### 📎 導師記憶快照（memory.json）")
    for name, label, *_ in MEMORY_LAYERS:
        items = mem["layers"].get(name, {}).get("items", [])
        if not items:
            continue
        lines.append(f"- **{label}（{name}）**：")
        for it in items:
            imp = it.get("importance", "?")
            seen = it.get("seen_count", 1)
            dom = it.get("domain", "-")
            lines.append(f"    - [{dom}] {it.get('title','')}  ·imp{imp}·seen{seen}")
    trends = mem.get("trends", [])
    if trends:
        lines.append("- **追蹤趨勢**：")
        for t in trends:
            nm = t.get("name", t) if isinstance(t, dict) else t
            lines.append(f"    - {nm}")

    lines.append("")
    lines.append("### 學習者記憶快照（learner.json + state.json）")
    lv = state.get("learner", {})
    if lv:
        lines.append(f"- 等級：CV={lv.get('cv_level','?')} · LLM={lv.get('llm_level','?')} · "
                     f"Diffusion={lv.get('diff_level','?')}（每日{lv.get('daily_minutes','?')}分）")
    prog = state.get("progress", {})
    if prog:
        # 2026-08-05：連續/總天數改用 _streak_stats() 動態推導（不信任可能過期的 state 欄位）；
        # 節流/精簡模式已移除（超輕量模式 light_checkin 取代其功能）。
        _tot, _cur, _last = _streak_stats()
        lines.append(f"- 進度：Week {prog.get('current_week','?')} Day {prog.get('current_day','?')} · "
                     f"{prog.get('quarter','?')} · 總互動{_tot}天/目前連續{_cur}天(最近{_last or '無'})")
        db = prog.get("domain_balance", {})
        if db:
            lines.append(f"- 領域平衡：CV={db.get('cv',0)} LLM={db.get('llm',0)} Diff={db.get('diffusion',0)}")
    bs = mem.get("blind_spots", [])
    if bs:
        lines.append("- 待釐清盲區：")
        for b in bs:
            txt = b.get("concept", b) if isinstance(b, dict) else b
            lines.append(f"    - {txt}")
    epi = mem.get("episodic", [])
    if epi:
        recent = "、".join(str(e.get('paper', e)) if isinstance(e, dict) else str(e) for e in epi[-3:])
        lines.append(f"- episodic 通關紀錄：{len(epi)} 筆（近 3：{recent}）")
    return "\n".join(lines)


def journal_add(flags):
    """Append a raw-interaction journal entry to journal/ , named by timestamp."""
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    now = datetime.now()
    ts_file = now.strftime("%Y-%m-%d_%H%M%S")
    ts_human = now.strftime("%Y-%m-%d %H:%M:%S")

    tag = flags.get("tag")
    slug = ""
    if isinstance(tag, str) and tag.strip():
        slug = "_" + "".join(c if (c.isalnum() or c in "-") else "-" for c in tag.strip())[:40]
    fname = f"{ts_file}{slug}.md"
    fpath = os.path.join(JOURNAL_DIR, fname)

    domain = flags.get("domain") if isinstance(flags.get("domain"), str) else "-"
    title  = flags.get("title")  if isinstance(flags.get("title"), str) else "(未命名互動)"
    user_parts   = _split_multi(flags.get("user", "")   if isinstance(flags.get("user"), str) else "")
    mentor_parts = _split_multi(flags.get("mentor", "") if isinstance(flags.get("mentor"), str) else "")

    md = []
    md.append(f"# 瑣碎記憶 · {ts_human}")
    md.append("")
    md.append(f"- 主題：{title}")
    md.append(f"- 領域：{domain}")
    md.append(f"- 時間：{ts_human}")
    md.append("")
    md.append("## 使用者原始互動（逐字）")
    if user_parts:
        for p in user_parts:
            md.append(f"> {p}")
            md.append("")
    else:
        md.append("_（未提供）_")
        md.append("")
    md.append("## 導師回應／裁決摘要")
    if mentor_parts:
        for p in mentor_parts:
            md.append(f"- {p}")
    else:
        md.append("_（未提供）_")
    md.append("")
    md.append("## 當下記憶快照")
    md.append(_memory_snapshot_md())
    md.append("")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"已寫入瑣碎記憶：journal/{fname}")
    print(f"   主題：{title}（{domain}）")
    print(f"   原始互動 {len(user_parts)} 段 · 導師摘要 {len(mentor_parts)} 段 · 內嵌記憶快照 OK")


def journal_list():
    """List all raw-interaction journal entries, oldest first."""
    if not os.path.isdir(JOURNAL_DIR):
        print("（尚無瑣碎記憶。用 journal_add 建立第一筆。）"); return
    files = sorted(f for f in os.listdir(JOURNAL_DIR) if f.endswith(".md"))
    if not files:
        print("（journal/ 為空。）"); return
    print(f"瑣碎記憶 journal/  共 {len(files)} 筆")
    print("-" * 54)
    for f in files:
        path = os.path.join(JOURNAL_DIR, f)
        first = ""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("- 主題"):
                        first = line.split("：", 1)[-1].strip(); break
        except Exception:
            pass
        print(f"  - {f}   {first}")


# ─────────────────────────────────────────────
# 程式化省 token 層：check_dup / week_plan / daily_brief
#   原則：驗證(重複)、輪轉(想法軸/跨域來源)、規劃骨架、執行盤點 → 全部程式化，不燒 token。
#   LLM 只在「每週讀一次長文做策略註記」與「寫 rubric / 判讀回答 / 選新論文 / 寫 takeaway」時介入。
#   分層閱讀：週規劃(week_plan new)讀一次長文 → 每日(daily_brief)只讀 compact 計畫 + 驗證執行。
# ─────────────────────────────────────────────

import re as _re

WEEKPLAN_FILE = os.path.join(BASE, "week_plan.json")
PUSHLOG_FILE  = os.path.join(BASE, "push_log.json")
DUP_JACCARD   = 0.6  # 標題 token Jaccard ≥ 此值視為疑似重複

IDEA_AXES = [
    "架構改良", "訓練目標與損失", "資料與表徵", "效率與壓縮", "理論分析與界限",
    "反常識/負結果", "綜述/分類體系", "benchmark/評測", "經典重讀", "失敗模式與魯棒性",
]
XDOMAIN_SOURCES = [
    "物理(熱力學/統計力學/OT)", "化學(反應/分子動力學)", "生物神經(預測編碼/自由能)",
    "演化生態(族群動態/演化博弈)", "數學(群論/拓撲/資訊幾何)", "資訊論(率失真/MDL/通道容量)",
    "控制/訊號(狀態空間/濾波/回饋)", "經濟/博弈(機制設計/均衡/拍賣)", "複雜系統(自組織臨界/網路)",
    "認知/語言(範疇化/語用/構式)", "運籌/最佳化(凸分析/對偶/隨機過程)",    "認知/語言(範疇化/語用/構式)", "運籌/最佳化(凸分析/對偶/隨機過程)", "社會學(意見動態/擴散)",
]

def _norm_title(s):
    """Normalize a title for dedup: lowercase, keep alnum + CJK, collapse spaces."""
    if not isinstance(s, str):
        return ""
    s = _re.sub(r"[^\w一-鿿]+", " ", s.lower(), flags=_re.UNICODE)
    return " ".join(s.split())

def _title_tokens(s):
    return set(_norm_title(s).split())

_ARXIV_RE = _re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})", _re.I)
def _arxiv_id(u):
    """Extract a canonical arXiv id from any arxiv URL form (abs/pdf/html, with or without vN)."""
    if not isinstance(u, str):
        return ""
    m = _ARXIV_RE.search(u)
    return m.group(1) if m else ""

def _jaccard(a, b):
    if not a or not b:
        return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0

def _collect_known_papers():
    """Every paper already seen（記憶各層 + 淡出歸檔 + episodic 含歸檔 + push_log 含歸檔）。
    push_log 涵蓋是 wild 軌（輕量、不 mem_add）防重的唯一依據。{title,url,pid,where}"""
    mem = load_memory()
    known = []
    for name, *_ in MEMORY_LAYERS:
        for it in mem["layers"][name]["items"]:
            known.append({"title": it.get("title", ""), "url": it.get("url", "") or "",
                          "pid": it.get("id", ""), "where": f"mem:{name}"})
    for it in _load_json_or(MEMORY_ARCHIVE_FILE, []):
        known.append({"title": it.get("title", ""), "url": it.get("url", "") or "",
                      "pid": it.get("id", ""), "where": "mem:archive"})
    for e in list(mem["episodic"]) + _load_json_or(LEARNER_ARCHIVE_FILE, []):
        pid = e.get("paper_id", "")
        t = PAPERS[pid]["title"] if pid in PAPERS else pid
        url = PAPERS.get(pid, {}).get("url", "") if pid in PAPERS else ""
        known.append({"title": t, "url": url, "pid": pid,
                      "where": f"episodic:{e.get('status', '')}"})
    for e in _load_pushlog() + _load_json_or(PUSHLOG_ARCHIVE_FILE, []):
        for p in e.get("papers", []):
            known.append({"title": p.get("title", "") or p.get("pid", ""), "url": p.get("url", "") or "",
                          "pid": p.get("pid", ""), "where": f"push:{e.get('date','')}:{p.get('role','')}"})
    return known

def check_dup(flags):
    """程式化重複判定，取代 LLM 目視照合黑名單。
       用法: check_dup --title "論文標題" [--url "..."]
       輸出 HIT/疑似/CLEAR；命中(≥0.95)時 exit code 2 供腳本判斷。"""
    title = flags.get("title")
    if not title or title is True:
        print('用法: check_dup --title "論文標題" [--url "..."]'); return
    url = flags.get("url", "") if isinstance(flags.get("url"), str) else ""
    qtok, qnorm = _title_tokens(title), _norm_title(title)
    qaid = _arxiv_id(url)
    best = None
    for k in _collect_known_papers():
        score, why = 0.0, ""
        if url and k["url"] and url.strip() == k["url"].strip():
            score, why = 1.0, "url 完全一致"
        elif qaid and qaid == _arxiv_id(k["url"]):
            score, why = 1.0, f"arXiv id 一致 ({qaid})"
        elif _norm_title(k["title"]) and _norm_title(k["title"]) == qnorm:
            score, why = 1.0, "標題正規化完全一致"
        else:
            j = _jaccard(qtok, _title_tokens(k["title"]))
            score, why = j, f"標題 Jaccard={j:.2f}"
        if best is None or score > best[0]:
            best = (score, k, why)
    if best and best[0] >= DUP_JACCARD:
        s, k, why = best
        tag = "🔴 HIT" if s >= 0.95 else "🟡 疑似"
        print(f"{tag}  {why}")
        print(f"   撞: [{k['where']}] {k['title'][:50]}  pid={k['pid']}")
        print("   → " + ("黑名單命中，勿重推（複習例外須在推薦理由明講）"
                          if s >= 0.95 else "高度相似，人工確認是否為變體再決定"))
        if s >= 0.95:
            sys.exit(2)
    else:
        sc = f"{best[0]:.2f}" if best else "0.00"
        print(f"🟢 CLEAR  最高相似 {sc} < {DUP_JACCARD}，可推")

# ── push_log：每日推播事件（A. 一石三鳥：驗組成 + anchor 硬約束 + 供 daily_brief 推進日 slot）──

PUSH_ROLES = ("main", "xdomain", "finance", "wild", "review")

def _load_pushlog():
    if not os.path.exists(PUSHLOG_FILE):
        return []
    try:
        d = load(PUSHLOG_FILE)
        return d if isinstance(d, list) else []
    except Exception:
        return []

def push_log(flags):
    """
    記錄當日推播（每日推播後必跑）：
      ① 程式化驗組成：3 主領域 + >=1 跨域鏡子 + 1 金融鏡子 + 3 趣味探索 wild
        （2026-08-05：節流/精簡模式已移除，一律要求完整組成；沒力氣深讀時改用 light_checkin）
      ② daily_brief 以 push_log 日期推進「計畫 Day」（不再依賴使用者互動）
      ③ 跨域/金融必填 anchor（回接的主領域機制）→ 北極星硬約束落為資料欄位
      ④ wild 軌輕量制：免 anchor、免 mem_add/rubric；第三欄改填「標題」供防重
        （push_log 是 wild 防重的唯一記錄，check_dup 會掃 push_log 含歸檔）
      ⑤ KG 先修守門程式化（2026-07-16(二)）：main 每篇必須在知識圖譜且 🟢 可推；
        LOCKED（先修未過）或 UNKNOWN（未入圖）與缺 anchor 同級 → exit 3。
        使用者不應看到鎖定論文：呈現前先跑 --dry 預檢（驗全部、不寫檔）。
    用法: push_log --papers "pid::role[::anchor|::title][::url]||..." [--date YYYY-MM-DD] [--dry]
          role ∈ main / xdomain / finance / wild / review；
          xdomain 與 finance 第三欄=anchor（必填）；wild 第三欄=標題（建議填）。
          --dry：呈現給使用者前的預檢——完整驗組成/anchor/KG，但不寫入 push_log。
          檢視: push_log --show [N]（近 N 天，預設 7）
    同日重跑會覆蓋（補推缺軌後重跑即可）。未達標 exit code 3。
    """
    if flags.get("show"):
        n = int(flags["show"]) if flags.get("show") is not True else 7
        logs = [e for e in _load_pushlog() if _days_between(e.get("date", "1970-01-01")) <= n]
        print(f"🗞 push_log 近 {n} 天：{len(logs)} 筆")
        for e in logs:
            comp = e.get("composition", {})
            note = e.get("light_note", ""); interest = e.get("interest", "")
            tag = "　🌤 已打卡" if e.get("user_engaged") else ""
            if e.get("mode") == "light":
                print(f"  {e['date']}  🌤 超輕量打卡" + (f"　備註：{note}" if note else "")
                      + (f"　📍{interest}" if interest else ""))
                continue
            print(f"  {e['date']}  main={comp.get('main',0)} xdomain={comp.get('xdomain',0)} "
                  f"finance={comp.get('finance',0)} wild={comp.get('wild',0)}"
                  + ("" if e.get("ok") else "  ⚠組成未達標") + tag
                  + (f"　備註：{note}" if note else "") + (f"　📍{interest}" if interest else ""))
            for p in e.get("papers", []):
                a = f"  ⚓{p['anchor'][:44]}" if p.get("anchor") else ""
                print(f"     [{p['role']}] {p.get('domain','?')} {p.get('title', p['pid'])[:44]}{a}")
        return
    raw = flags.get("papers")
    if not raw or raw is True:
        print('用法: push_log --papers "pid::role[::anchor|::title]||..."  （role: main/xdomain/finance/wild/review）'); return
    day = flags.get("date") if isinstance(flags.get("date"), str) else str(date.today())
    papers, problems = [], []
    for spec in _split_multi(raw):
        parts = [x.strip() for x in spec.split("::")]
        pid = parts[0]
        role = parts[1] if len(parts) > 1 else "main"
        extra = parts[2] if len(parts) > 2 else ""
        purl = parts[3] if len(parts) > 3 else ""
        if role not in PUSH_ROLES:
            problems.append(f"{pid}: 未知 role '{role}'"); role = "main"
        dom, title, *_rest = _lookup_paper(pid)
        anchor = ""
        if role == "wild":
            # 輕量制：免 mem_add、免 anchor；第三欄當標題（防重用）
            if dom is None:
                dom = "wild"
                title = extra or pid
            elif extra:
                title = title or extra
        else:
            anchor = extra
            if dom is None:
                problems.append(f"{pid}: 不在記憶中（先 mem_add 再 push_log）"); dom, title = "?", pid
            if role in ("xdomain", "finance") and not anchor:
                problems.append(f"{pid}: {role} 缺 anchor（必須寫明回接哪個主領域機制）")
        papers.append({"pid": pid, "title": title, "domain": dom, "role": role, "anchor": anchor, "url": purl})
    # ⑤ KG 先修守門（程式化，僅 main）：LOCKED/UNKNOWN 與缺 anchor 同級
    kg = _load_kg(); kg_passed = _kg_passed()
    for p in papers:
        if p["role"] != "main":
            continue
        node = kg["nodes"].get(p["pid"])
        if node is None:
            problems.append(f"{p['pid']}: ⚠ 不在知識圖譜（先 kg_add 依引用定位，再 kg_check）")
        elif not _kg_recommendable(p["pid"], node, kg_passed):
            unmet = [r for r in node.get("prereqs", []) if r not in kg_passed]
            sugg = [r for r in unmet
                    if r in kg["nodes"] and _kg_recommendable(r, kg["nodes"][r], kg_passed)]
            problems.append(f"{p['pid']}: 🔴 KG LOCKED 缺先修 {unmet}"
                            f"（改推其先修前沿：{sugg or '先擴圖譜'}）")
    comp = {r: sum(1 for p in papers if p["role"] == r) for r in PUSH_ROLES}
    state = load(STATE_FILE)
    # 2026-08-05：節流/精簡模式已移除——超輕量模式（light_checkin）已能涵蓋「沒力氣深讀」的情境，
    # push_log 一律要求完整組成，不再放寬。
    if comp["main"] < 3:     problems.append(f"主領域論文 {comp['main']}/3（CV/LLM/Diffusion 各一）")
    if comp["xdomain"] < 1:  problems.append("跨域鏡子 0 篇（至少 1，越多越好）")
    if comp["finance"] != 1: problems.append(f"金融鏡子 {comp['finance']} 篇（固定 1）")
    if comp["wild"] != 3:    problems.append(f"趣味探索 {comp['wild']}/3（與主領域無關、獨特方法論/反直覺，領域越廣越好）")
    ok = not problems
    dry = bool(flags.get("dry"))
    if not dry:
        prior = _load_pushlog()
        old_entry = next((e for e in prior if e.get("date") == day), None)
        new_entry = {"date": day, "papers": papers, "composition": comp, "ok": ok}
        # 保留同一天先前 light_checkin 留下的互動標記（避免正式推播覆蓋掉「使用者已經打卡」的紀錄）
        if old_entry:
            for k in ("user_engaged", "light_note", "interest"):
                if k in old_entry:
                    new_entry[k] = old_entry[k]
        logs = [e for e in prior if e.get("date") != day]
        logs.append(new_entry)
        save(PUSHLOG_FILE, logs)
    print(f"🗞 push_log {'[--dry 預檢·未寫入]  ' if dry else ''}{day}  共 {len(papers)} 篇  "
          f"main={comp['main']} xdomain={comp['xdomain']} "
          f"finance={comp['finance']} wild={comp['wild']} review={comp['review']}")
    if problems:
        print("  ⚠ 組成/欄位/KG 未達標：")
        for p in problems:
            print(f"     - {p}")
        if dry:
            print("  → 預檢未過：換掉 LOCKED 論文／補缺軌／補 anchor 後再呈現給使用者。")
        else:
            print("  → 已記錄現狀；請補推缺少的軌／換先修前沿／補 anchor 後同日重跑 push_log 覆蓋。")
        sys.exit(3)
    print(f"  ✅ 組成達標；main 全數通過 KG 守門；跨域/金融皆有 anchor；wild 3 篇（輕量制）。"
          + ("  可安心呈現。" if dry else ""))


# ── streak / 超輕量模式（2026-08-05；2026-08-06 移除節流概念 + light_checkin 改為不可破壞性打卡）
# 病灶：連續天數只在舊版 boot()/daily_push() 才會遞增與衰減，但現行每日流程走
#   push_log，從不觸碰 state.json 那組欄位 → 久未互動時數字停在很久以前（顯示錯誤）。
# 修正：一律從 push_log(含歸檔) ∪ episodic(含歸檔) 的原始日期「即時推導」，不維護計數器，
#   永遠正確；且只在使用者主動執行 streak 指令時才顯示——daily_brief/learner_state 等
#   自動流程一律不主動秀「連續 N 天」，避免造成壓力、降低動力。
# 2026-08-06：既然已有 light_checkin 這條「沒力氣就打卡」的路，節流/精簡模式（自動偵測久未互動、
#   放寬 push_log 組成）整個移除——多一套規則反而複雜。改成單一原則：使用者回覆「done」/結束今天，
#   一律要 light_checkin 記一筆（不管今天是深讀還是只看一眼）；只有真的討論/嘗試解題時才額外做
#   詳細記錄（review + journal_add）。light_checkin 因此可能在『今天已經有正式 push_log 推播』之後
#   才呼叫——設計成合併寫入（只加 user_engaged 旗標），不會覆蓋掉當天的推播內容。

def _all_activity_dates():
    """所有『使用者真的有動作』的日期（去重字串集合）——刻意不含系統自動產生的每日推播本身
    （push_log 的 main/xdomain/finance/wild 是排程自動生成，使用者不一定真的看過，計入會虛報streak）。
    只算真實互動訊號：
      ① learner episodic 狀態 teaser_seen/reading/passed/failed（含歸檔）——使用者跑過 teaser/deep/review；
         （不含 hook_seen：那是舊版 daily_push 自動標記，不代表使用者真的看過）
      ② push_log 裡 user_engaged==True 的紀錄（含歸檔）——不論該天是否也有正式推播，
         只要 light_checkin 打過卡就算（一天最多一筆 push_log entry，打卡是合併寫入，見 light_checkin）；
      ③ journal/ 底下的逐字對話檔（檔名 YYYY-MM-DD_...）——真實往返互動的原始紀錄。"""
    dates = set()
    mem = load_memory()
    genuine = ("teaser_seen", "reading", "passed", "failed")
    for e in list(mem["episodic"]) + _load_json_or(LEARNER_ARCHIVE_FILE, []):
        if e.get("status") in genuine and e.get("date"):
            dates.add(e["date"])
    for e in _load_pushlog() + _load_json_or(PUSHLOG_ARCHIVE_FILE, []):
        if e.get("user_engaged") and e.get("date"):
            dates.add(e["date"])
    if os.path.isdir(JOURNAL_DIR):
        for fn in os.listdir(JOURNAL_DIR):
            if len(fn) >= 10 and fn[4] == "-" and fn[7] == "-":
                dates.add(fn[:10])
    return dates

def _streak_stats():
    """回傳 (total_days, current_streak, last_active_date_str_or_None)。純推導、不寫檔。
    current_streak：從『最近一次活動日』往回數連續天數；若最近一次活動日距今天超過 1 天，
    視為已中斷 → 0（不會因為『今天還沒做』就先扣，也不會虛報早就斷掉的連續數）。"""
    dates = _all_activity_dates()
    total = len(dates)
    if not dates:
        return 0, 0, None
    last = max(dates)
    last_d = datetime.strptime(last, "%Y-%m-%d").date()
    gap = (date.today() - last_d).days
    if gap > 1:
        return total, 0, last
    streak, d = 0, last_d
    while str(d) in dates:
        streak += 1
        d -= timedelta(days=1)
    return total, streak, last

def streak():
    """使用者主動查詢才顯示（不在任何自動流程中印出）：總互動天數 + 目前連續天數 + 最近一次日期。
    用法: python3 mentor.py streak"""
    total, cur, last = _streak_stats()
    print("\n📆 習慣統計（僅在你主動查詢時顯示）")
    print("─" * 40)
    print(f"  總互動天數：{total} 天")
    if cur:
        print(f"  目前連續：{cur} 天")
    else:
        print(f"  目前連續：0 天" + (f"（最近一次：{last}，中斷也沒關係，回來就好）" if last else "（還沒開始，隨時都可以）"))
    if last:
        print(f"  最近一次：{last}")
    print("─" * 40)
    return total, cur, last

def light_checkin(flags):
    """使用者說『done』/今天結束了的通用互動打卡——不論今天是深讀還是只看一眼，都要記一筆。
    設計成**合併寫入**：若當天 push_log 已有正式推播紀錄（main/xdomain/finance/wild），
    只加上 user_engaged=True 旗標，**不覆蓋**原本的論文清單；若當天還沒有任何紀錄，才新建一筆
    mode=light 的空白紀錄。因此可以安全地在任何時間點呼叫，不用擔心弄丟推播紀錄。
    用法: light_checkin [--note "..."] [--interest "文字：想往哪個方向/最近感受"] [--date YYYY-MM-DD]
    若帶 --interest：同時寫入 state.json progress.redirect_note，供下次規劃時讀取、
    重新搜尋文獻並調整推薦方向（daily_brief 會提示；處理完用 redirect_clear 清除）。
    註：這裡的 --note 只是一句話標記，不是詳細記錄——真的有討論/嘗試解題時，
    詳細內容要另外用 review + journal_add 記錄（見 CLAUDE.md）。"""
    day = flags.get("date") if isinstance(flags.get("date"), str) else str(date.today())
    note = flags.get("note") if isinstance(flags.get("note"), str) else ""
    interest = flags.get("interest") if isinstance(flags.get("interest"), str) else ""
    logs = _load_pushlog()
    existing = next((e for e in logs if e.get("date") == day), None)
    if existing is not None:
        existing["user_engaged"] = True
        if note:
            existing["light_note"] = note
        if interest:
            existing["interest"] = interest
        merged = True
    else:
        logs.append({"date": day, "papers": [], "composition": {r: 0 for r in PUSH_ROLES},
                     "ok": True, "mode": "light", "user_engaged": True,
                     "light_note": note, "interest": interest})
        merged = False
    save(PUSHLOG_FILE, logs)
    print(f"✅ 今天完成打卡：{day}" + ("（已合併進今天的推播紀錄，內容未受影響）" if merged else "（超輕量，未做正式推播）"))
    if note:
        print(f"   備註：{note}")
    if interest:
        state = load(STATE_FILE)
        state["progress"]["redirect_note"] = {"text": interest, "date": day}
        save(STATE_FILE, state)
        print(f"   📍 已記錄方向回饋：「{interest}」→ 下次規劃會依此重新搜尋、調整推薦。")
        print("   （只是隨口一提也沒關係，之後想到再說都可以）")
    print("   習慣 > 完美 ✓")

def redirect_clear():
    """處理完使用者的方向回饋、重新搜尋並調整推薦後，清掉待處理標記。
    用法: python3 mentor.py redirect_clear"""
    state = load(STATE_FILE)
    if state["progress"].pop("redirect_note", None) is not None:
        save(STATE_FILE, state)
        print("🧹 已清除待處理的方向回饋。")
    else:
        print("（目前沒有待處理的方向回饋）")


def _phase_focus(week):
    """Return (quarter, theme, weekly_goals-dict) for a week from roadmap.json."""
    road = load(ROAD_FILE)
    q = "Q1" if week <= 13 else "Q2" if week <= 26 else "Q3" if week <= 39 else "Q4"
    quarters = road.get("quarters", {})
    theme = quarters.get(q, {}).get("theme", "")
    goals = quarters.get(q, {}).get("weekly_goals", {}).get(str(week), {})
    if isinstance(goals, dict):
        goals = {k: v for k, v in goals.items() if k in ("cv", "llm", "diffusion")}
    return q, theme, goals

def roadmap_set(flags):
    """D. 滾動擴充 52 週藍圖：把某週三軌目標寫回 roadmap.json（內容由 LLM 生成）。
    用法: roadmap_set --week N --cv "..." --llm "..." --diffusion "..."
          [--criteria_cv "a||b" --criteria_llm "..." --criteria_diffusion "..." --criteria_cross "..." --force]
    既有非空目標不覆蓋，除非 --force。"""
    wf = flags.get("week")
    if not wf or wf is True:
        print("需要 --week N"); return
    w = int(wf)
    vals = {d: flags.get(d) for d in ("cv", "llm", "diffusion")}
    if not any(isinstance(v, str) and v for v in vals.values()):
        print("至少提供一軌目標 --cv/--llm/--diffusion"); return
    road = load(ROAD_FILE)
    q = "Q1" if w <= 13 else "Q2" if w <= 26 else "Q3" if w <= 39 else "Q4"
    quarter = road.setdefault("quarters", {}).setdefault(q, {})
    g = quarter.setdefault("weekly_goals", {}).setdefault(str(w), {})
    if any(g.get(d) for d in ("cv", "llm", "diffusion")) and not flags.get("force"):
        print(f"Week {w} 已有目標，未覆蓋（--force 可覆蓋）。現況:")
        for d in ("cv", "llm", "diffusion"):
            if g.get(d): print(f"   {d}: {g[d][:60]}")
        return
    for d, v in vals.items():
        if isinstance(v, str) and v:
            g[d] = v
    crit = {}
    for d in ("cv", "llm", "diffusion", "cross"):
        c = flags.get(f"criteria_{d}")
        if isinstance(c, str) and c:
            crit[d] = _split_multi(c)
    if crit:
        g["completion_criteria"] = {**g.get("completion_criteria", {}), **crit}
    save(ROAD_FILE, road)
    print(f"🗺 roadmap.json 已寫入 Week {w}（{q}）三軌目標。")
    for d in ("cv", "llm", "diffusion"):
        if g.get(d): print(f"   {d}: {g[d][:60]}")


def _print_week_plan(plan):
    lv = plan.get("levels", {})
    print("─" * 54)
    print(f"  Week {plan['week']}  {plan.get('quarter', '')} · {plan.get('theme', '')}")
    print(f"  等級  CV={lv.get('cv')} LLM={lv.get('llm')} Diff={lv.get('diffusion')}")
    pf = plan.get("phase_focus", {})
    for d in ("cv", "llm", "diffusion"):
        if pf.get(d):
            print(f"    {d} focus: {pf[d]}")
    print(f"  黑名單快照: {len(plan.get('blacklist', []))} 筆")
    print("  7 天輪轉（想法軸 / 3 個跨域來源）:")
    for dd in plan["days"]:
        srcs = dd.get("xdomain_sources") or [dd.get("xdomain_source", "")]
        print(f"    Day{dd['day']}  「{dd['idea_axis']}」  ← {' / '.join(srcs)}")
    if plan.get("notes"):
        print(f"  📝 策略註記: {plan['notes']}")
    print("─" * 54)

def week_plan(argv):
    """每週一次規劃（分層閱讀的『長讀』端）。
       week_plan new [--week N] [--notes "..."]  產生 7 天想法軸/跨域輪轉 + 黑名單快照
       week_plan show                            顯示現行週計畫"""
    sub = argv[0] if argv else "show"
    if sub == "new":
        flags = _parse_flags(argv[1:])
        state = load(STATE_FILE)
        wf = flags.get("week")
        w = int(wf) if (wf and wf is not True) else state["progress"]["current_week"]
        abase = state["progress"].get("axis_base", 0)
        xbase = state["progress"].get("xsrc_base", 0)
        levels = {d: state["learner"].get(LEVEL_KEY[d], "A") for d in ("cv", "llm", "diffusion")}
        q, theme, goals = _phase_focus(w)
        if not goals:
            print(f"  ⚠ roadmap.json 尚無 Week {w} 三軌目標（D. 藍圖滾動擴充）：")
            print(f"    → LLM 請依上週結果與 {q} 主題生成本週 cv/llm/diffusion 目標並寫回：")
            print(f'      python3 mentor.py roadmap_set --week {w} --cv "..." --llm "..." --diffusion "..."')
        nx = len(XDOMAIN_SOURCES)
        days = [{
            "day": i + 1,
            "idea_axis": IDEA_AXES[(abase + i) % len(IDEA_AXES)],
            # 3 個跨域來源，供「每主領域各配一篇跨域鏡子」（1–3 篇，鼓勵但不強制）
            "xdomain_sources": [XDOMAIN_SOURCES[(xbase + i + k) % nx] for k in range(3)],
        } for i in range(7)]
        state["progress"]["axis_base"] = (abase + 7) % len(IDEA_AXES)
        state["progress"]["xsrc_base"] = (xbase + 7) % len(XDOMAIN_SOURCES)
        save(STATE_FILE, state)
        seen, bl = set(), []
        for k in _collect_known_papers():
            key = _norm_title(k["title"])
            if not key or key in seen:
                continue
            seen.add(key)
            bl.append({"pid": k["pid"], "title": k["title"][:60], "url": k["url"]})
        plan = {
            "week": w, "generated": str(date.today()), "quarter": q, "theme": theme,
            "levels": levels, "phase_focus": goals, "days": days, "blacklist": bl,
            "notes": flags.get("notes", "") if isinstance(flags.get("notes"), str) else "",
        }
        save(WEEKPLAN_FILE, plan)
        print(f"🗓  已產生 Week {w} 計畫（{len(bl)} 筆黑名單、7 天輪轉已排定；axis_base→{state['progress']['axis_base']}）")
        _print_week_plan(plan)
        return plan
    if not os.path.exists(WEEKPLAN_FILE):
        print("尚無週計畫。執行：python3 mentor.py week_plan new"); return
    plan = load(WEEKPLAN_FILE)
    _print_week_plan(plan)
    return plan

def daily_brief():
    """每日輕量簡報（分層閱讀的『短讀』端）。取代每日 mem_context+mem_view week/month+journal_list 四連 dump。
       讀 week_plan + trimmed memory；並用 episodic 日期程式化驗證本週執行進度。"""
    state = load(STATE_FILE); p = state["progress"]
    mem = load_memory()
    cw = p["current_week"]
    plan = load(WEEKPLAN_FILE) if os.path.exists(WEEKPLAN_FILE) else None
    print("\n🌅 每日簡報 daily_brief")
    print("=" * 54)
    if not plan or plan.get("week") != cw:
        print(f"  ⚠ 本週 (Week {cw}) 尚無計畫或計畫過期。")
        print("  → 先執行（每週一次·讀長文規劃）：python3 mentor.py week_plan new")
        print("=" * 54)
        return None
    gen = plan.get("generated", "0000-00-00")
    active = ("hook_seen", "teaser_seen", "reading", "passed", "failed")
    ep_dates = {e.get("date", "") for e in mem["episodic"]
                if e.get("date", "") >= gen and e.get("status") in active}
    pl_dates = {e.get("date", "") for e in _load_pushlog() if e.get("date", "") >= gen}
    pushed_dates = sorted(ep_dates | pl_dates)  # 推播事件(push_log) ∪ 互動事件(episodic)
    today_str = str(date.today())
    already_today = today_str in pushed_dates
    done = len(pushed_dates)
    slot_idx = max(0, min((done - 1) if already_today else done, 6))
    slot = plan["days"][slot_idx]
    lv = plan.get("levels", {})
    print(f"  {today_str}  Week {cw} · 計畫 Day {slot_idx + 1}/7"
          f"{'（今日已推）' if already_today else ''}")
    print(f"  等級  CV={lv.get('cv')} LLM={lv.get('llm')} Diff={lv.get('diffusion')}")
    rn = p.get("redirect_note")
    if rn:
        print(f"  📍 待處理方向回饋（{rn.get('date','')}）：「{rn.get('text','')}」")
        print("      → 今天請先依此重新搜尋文獻、調整推薦方向；處理後執行 redirect_clear 清除此提示。")
    print(f"  ▸ 今日想法軸：「{slot['idea_axis']}」")
    nm = {"cv": "CV", "llm": "LLM", "diffusion": "Diffusion"}
    srcs = slot.get("xdomain_sources") or [slot.get("xdomain_source", "")]
    print("  ▸ 今日跨域鏡子（1–3 篇，越多越好；鼓勵每主領域各配一篇、來源各不同）:")
    for mn, s in zip(("cv", "llm", "diffusion"), srcs):
        print(f"      {nm[mn]} ← {s}")
    fin_dom = ("llm", "diffusion", "cv")[slot_idx % 3]
    print(f"  ▸ 今日金融鏡子（固定 1 篇）：挑「金融 × {nm[fin_dom]}」論文（必須重講 {nm[fin_dom]} 機制，非純量化金融）")
    print("  ▸ 今日趣味探索 wild（固定 3 篇）：與主領域**無關**的有趣論文——獨特方法論或反直覺結論，")
    print("      可非自然科學（歷史/考古/藝術/語言/社會/人類學...），三篇領域越分散越好。")
    print("      輕量制：免 anchor、免 mem_add/rubric；只需 check_dup 防重，push_log 記 pid::wild::標題。")
    pf = plan.get("phase_focus", {})
    for d in ("cv", "llm", "diffusion"):
        if pf.get(d):
            print(f"      {d} focus: {pf[d]}")
    _kg_frontier_brief()
    recent, _seen_r = [], set()
    def _add_recent(t):
        k = _norm_title(t)
        if k and k not in _seen_r:
            _seen_r.add(k); recent.append(t[:38])
    for e in _load_pushlog():
        try:
            if _days_between(e.get("date", "1970-01-01")) <= 7:
                for p in e.get("papers", []):
                    _add_recent(p.get("title") or p.get("pid", ""))
        except Exception:
            pass
    for e in mem["episodic"]:
        try:
            if _days_between(e.get("date", "1970-01-01")) <= 7:
                pid = e.get("paper_id", "")
                _add_recent(PAPERS[pid]["title"] if pid in PAPERS else pid)
        except Exception:
            pass
    for _lname, *_ in MEMORY_LAYERS:
        for it in mem["layers"][_lname]["items"]:
            try:
                if _days_between(it.get("created", "1970-01-01")) <= 7:
                    _add_recent(it.get("title", ""))
            except Exception:
                pass
    print(f"  🚫 近7天已推（勿重推，共 {len(recent)}）：{recent[:8] if recent else '無'}")
    # 🎲 wild 主題長窗（45 天，含歸檔）——供搜 wild 時肉眼避開「同主題不同論文」反覆。
    # token 便宜（純文字清單），不需 embedding；補足 7 天窗抓不到跨週重複的漏洞。
    wrecent, _wseen = [], set()
    for e in _load_pushlog() + _load_json_or(PUSHLOG_ARCHIVE_FILE, []):
        try:
            if _days_between(e.get("date", "1970-01-01")) <= 45:
                for p in e.get("papers", []):
                    if p.get("role") != "wild":
                        continue
                    t = p.get("title") or p.get("pid", "")
                    k = _norm_title(t)
                    if k and k not in _wseen:
                        _wseen.add(k); wrecent.append(t[:40])
        except Exception:
            pass
    if wrecent:
        print(f"  🎲 近45天 wild 已推主題（{len(wrecent)} 則，搜 wild 時避開同主題反覆）：{wrecent}")
    blind = [b["concept"] for b in mem["blind_spots"] if not b["resolved"]]
    if blind:
        print(f"  ⚡ 待補盲區：{blind}")
    if mem.get("trends"):
        tn = [t.get("name", t) if isinstance(t, dict) else t for t in mem["trends"]]
        print(f"  📈 趨勢：{tn[:6]}")
    print(f"  ✅ 本週執行：{done}/7 天  {pushed_dates}")
    print("=" * 54)
    print("  流程：①用今日想法軸+跨域來源上網找新論文（各領域符合 level）+ 3 篇 wild")
    print("        ②每篇先 check_dup --title 驗重複 → ③主/跨域/金融 mem_add(含rubric,--pid)；wild 免 mem_add")
    print("        ④呈現給使用者 → ⑤push_log 記錄組成(3主+≥1跨域+1金融+3wild；跨域/金融附anchor，wild附標題)")
    print("        ⑥收尾 mem_consolidate + learner_state + snapshot")
    return plan


def integrity():
    """F. 檔案完整性檢查（每日流程開頭必跑）：mentor.py 可編譯 + 各 JSON 可解析。
    有損壞 → exit 4：停止流程並先修檔案，禁止手改 JSON 繞過主程式。"""
    import py_compile
    ok = True
    print("🔎 integrity 檔案完整性檢查")
    try:
        py_compile.compile(os.path.abspath(__file__), doraise=True)
        print("  ✅ mentor.py 編譯 OK")
    except Exception as ex:
        ok = False; print(f"  ❌ mentor.py 編譯失敗: {ex}")
    # 尾行哨兵（2026-07-17）：防「截斷點恰落在註解中→py_compile 假陽性」（沙箱 mount 曾同步到截斷版）
    try:
        with open(os.path.abspath(__file__), "rb") as _f:
            _tail = _f.read().decode("utf-8", "replace")[-200:]
        if "EOF-SENTINEL" in _tail:
            print("  ✅ mentor.py 尾行哨兵 OK（檔案未截斷）")
        else:
            ok = False; print("  ❌ mentor.py 缺尾行哨兵 EOF-SENTINEL —— 檔案可能是截斷版（沙箱 mount 同步不全），停手、勿在此副本上執行！")
    except Exception as ex:
        ok = False; print(f"  ❌ 尾行哨兵檢查失敗: {ex}")
    files = [STATE_FILE, LEARNER_FILE, ROAD_FILE, WEEKPLAN_FILE, PUSHLOG_FILE, KG_FILE,
             LEARNER_ARCHIVE_FILE, PUSHLOG_ARCHIVE_FILE,
             os.path.join(MEMORY_DIR, "meta.json"),
             os.path.join(MEMORY_DIR, "trends.json"),
             MEMORY_ARCHIVE_FILE] + [_mentor_layer_path(n) for n, *_ in MEMORY_LAYERS]
    for f in files:
        base = os.path.relpath(f, BASE)
        if not os.path.exists(f):
            print(f"  •  {base} 不存在（可接受）"); continue
        try:
            load(f); print(f"  ✅ {base} JSON OK")
        except Exception as ex:
            ok = False; print(f"  ❌ {base} 解析失敗: {ex}")
    if os.path.exists(MEMORY_FILE):
        print("  ⚠ 遺留單檔 memory.json 仍存在（正常情況應已遷移為 memory/ 切檔）")
    if ok:
        print("  → 完整性 OK，可進行每日流程。")
    else:
        print("  → 有損壞：停止流程、先修復檔案（禁止手改 JSON 繞過主程式）。")
        sys.exit(4)


# ─────────────────────────────────────────────
# Knowledge Graph — 先修依賴 DAG（2026-07-16）
# 目的：粗粒度 A/B/C 等級太鈍，會放行跳級（例：Diffusion=A 就推 EDA，但沒過 EDM/SDE）。
#       改用「先修依賴圖」精細守門——主領域推薦只能落在『先修全部通過』的前沿節點。
# 判準：passed = 該 pid 有 depth>=2（機制層）的 review pass（深度不打折·北極星）。
# 例外（刻意保留跳躍/點火）：spontaneous=True 的節點（跨域/金融/憑空跳躍）豁免先修，可推；
#       wild 軌不進圖譜（純點火）。禁止的是：對『有先修卻未通過先修』的節點直接跳推。
# 每天搜到新論文 → kg_add 依其引用/概念依賴放進圖譜相應位置；圖譜可分叉、可跳接、可憑空生。
# (sync-touch 2026-07-17: 觸發沙箱 mount 重新同步，無功能變更)
# ─────────────────────────────────────────────

KG_FILE = os.path.join(BASE, "kg.json")

def _blank_kg():
    return {"meta": {"created": str(date.today()), "last_updated": str(date.today()),
                     "note": "prerequisite DAG; passed = depth>=2 review pass"},
            "nodes": {}}

def _load_kg():
    if not os.path.exists(KG_FILE):
        kg = _blank_kg(); _save_kg(kg); return kg
    return load(KG_FILE)

def _save_kg(kg):
    save(KG_FILE, kg)

def _kg_passed():
    """學習者已『機制層(depth>=2)通過』的 pid 集合——先修解鎖的判準（含歸檔）。"""
    mem = load_memory()
    recs = list(mem["episodic"]) + _load_json_or(LEARNER_ARCHIVE_FILE, [])
    passed = set()
    for e in recs:
        pid = e.get("paper_id")
        for q in e.get("qa_record", []):
            if q.get("result") == "passed" and q.get("depth_score", 0) >= 2:
                passed.add(pid)
    return passed

def _kg_seen():
    mem = load_memory()
    return ({e.get("paper_id") for e in mem["episodic"]}
            | {e.get("paper_id") for e in _load_json_or(LEARNER_ARCHIVE_FILE, [])})

def _kg_recommendable(pid, node, passed):
    """該節點現在能否被主領域推薦：先修全通過 / 無先修 / 跳躍節點 → True。"""
    if node.get("spontaneous") or not node.get("prereqs"):
        return True
    return not [r for r in node["prereqs"] if r not in passed]

# 骨幹種子（首次 kg_seed 建立；之後靠 kg_add 逐日長大）
KG_SEED = {
    # ── diffusion 依賴鏈（正是這次跳級的重災區）──
    "ddpm":          ("diffusion", 1, [],              "DDPM 去噪擴散機率模型：離散前向加噪/反向去噪"),
    "ddim":          ("diffusion", 2, ["ddpm"],        "DDIM 確定性採樣（ODE 視角起點）"),
    "score_sde":     ("diffusion", 2, ["ddpm"],        "Score-based SDE/ODE 連續時間統一（Song 2021）"),
    "ldm":           ("diffusion", 3, ["ddpm"],        "Latent Diffusion 潛在空間擴散"),
    "flow_matching": ("diffusion", 3, ["score_sde"],   "Flow Matching 回歸式連續流訓練"),
    "edm":           ("diffusion", 3, ["score_sde"],   "EDM 設計空間旋鈕統一（Karras 2022）"),
    "eda-arb":       ("diffusion", 4, ["edm"],         "EDA 任意噪聲設計空間（今日主領域推薦）"),
    # ── llm 依賴鏈 ──
    "attention":     ("llm", 1, [],                    "Self-Attention QKV 機制"),
    "bert":          ("llm", 1, [],                    "BERT encoder-only 預訓練"),
    "rope":          ("llm", 2, ["attention"],         "RoPE 旋轉位置編碼"),
    "kv_cache":      ("llm", 2, ["attention"],         "KV Cache 自回歸推理快取"),
    "instructgpt":   ("llm", 3, ["attention"],         "InstructGPT / RLHF 對齊"),
    "infokv":        ("llm", 3, ["kv_cache"],          "InfoKV 資訊論 KV 壓縮（今日主領域推薦）"),
    # ── cv 依賴鏈（學習者已在機制層，多為前沿/已過）──
    "detr":          ("cv", 1, [],                     "DETR set prediction + 二分匹配"),
    "dab_detr":      ("cv", 2, ["detr"],               "DAB-DETR 動態 anchor query"),
    "dn_detr":       ("cv", 2, ["detr"],               "DN-DETR query denoising 加速收斂"),
    "deim_matching": ("cv", 2, ["detr"],               "DEIM 匹配改良"),
    "cv_ha_detr":    ("cv", 2, ["detr"],               "HA-DETR 即時化"),
    "rtp_detr":      ("cv", 2, ["detr"],               "RT-DETR NMS-free 即時偵測"),
    "detr-assign-div": ("cv", 2, ["detr"],             "DETR 多元標籤指派"),
    "dsdet":         ("cv", 3, ["detr"],               "DS-Det 單query範式+注意力解耦（今日主領域推薦）"),
    # ── 跨域/金融：跳躍節點（豁免先修）──
    "imp-control":   ("cv", 3, [],                     "內模原理 → DETR query 作物件內模（跨域）"),
    "turing-morph":  ("diffusion", 3, [],              "Turing 反應擴散 → diffusion 反向結構湧現（跨域）"),
    "spence-signal": ("llm", 3, [],                    "Spence 訊號賽局 → attention 資訊篩選（金融）"),
}
_KG_SPONTANEOUS = {"imp-control", "turing-morph", "spence-signal"}

def kg_seed(force=False):
    kg = _load_kg()
    for pid, (dom, lv, pre, title) in KG_SEED.items():
        if pid in kg["nodes"] and not force:
            n = kg["nodes"][pid]
            n.setdefault("domain", dom); n.setdefault("level", lv); n.setdefault("title", title)
            if not n.get("prereqs"):
                n["prereqs"] = list(pre)
        else:
            kg["nodes"][pid] = {"title": title, "domain": dom, "level": lv,
                                "prereqs": list(pre), "added": str(date.today())}
        if pid in _KG_SPONTANEOUS:
            kg["nodes"][pid]["spontaneous"] = True
    _save_kg(kg)
    print(f"✅ kg_seed 完成，共 {len(kg['nodes'])} 節點。")
    kg_frontier()

def kg_add(flags):
    """把（搜到的）論文放進知識圖譜相應位置。
    用法: kg_add --id <pid> --title "..." --domain <cv|llm|diffusion|...>
          [--prereqs "a||b"] [--level N] [--url ..] [--note ..] [--spontaneous] [--replace]
    --spontaneous：跨域/金融/憑空跳躍節點，豁免先修守門。"""
    pid = flags.get("id")
    if not pid or pid is True:
        print(kg_add.__doc__); return
    kg = _load_kg()
    node = kg["nodes"].get(pid, {"added": str(date.today()), "prereqs": []})
    for k in ("title", "domain", "url", "note"):
        if isinstance(flags.get(k), str):
            node[k] = flags[k]
    if "level" in flags:
        try: node["level"] = int(flags["level"])
        except Exception: pass
    if flags.get("spontaneous"):
        node["spontaneous"] = True
    if isinstance(flags.get("prereqs"), str):
        new_pre = _split_multi(flags["prereqs"])
        node["prereqs"] = (new_pre if flags.get("replace")
                           else sorted(set(node.get("prereqs", [])) | set(new_pre)))
    node.setdefault("title", pid); node.setdefault("domain", "?"); node.setdefault("prereqs", [])
    kg["nodes"][pid] = node
    _save_kg(kg)
    missing = [r for r in node["prereqs"] if r not in kg["nodes"]]
    tag = "✨跳躍" if node.get("spontaneous") else ""
    print(f"✅ kg_add {pid} {tag}  domain={node['domain']}  L{node.get('level','?')}  prereqs={node['prereqs'] or '無'}")
    if missing:
        print(f"  ⚠ 這些先修尚未建節點（記得補 kg_add，否則會被視為未通過而鎖住）：{missing}")

def kg_link(flags):
    """增/刪先修邊。用法: kg_link --id <pid> --prereqs "a||b" [--remove]"""
    pid = flags.get("id")
    pre = _split_multi(flags["prereqs"]) if isinstance(flags.get("prereqs"), str) else []
    if not pid or not pre:
        print('用法: kg_link --id <pid> --prereqs "a||b" [--remove]'); return
    kg = _load_kg()
    if pid not in kg["nodes"]:
        print(f"⚠ 節點不存在: {pid}（先 kg_add）"); return
    cur = set(kg["nodes"][pid].get("prereqs", []))
    cur = (cur - set(pre)) if flags.get("remove") else (cur | set(pre))
    kg["nodes"][pid]["prereqs"] = sorted(cur)
    _save_kg(kg)
    print(f"✅ kg_link {pid} prereqs={sorted(cur) or '無'}")

def kg_check(flags):
    """守門：某節點現在能否被『主領域』推薦。用法: kg_check --id <pid>
    🟢=可推（前沿/入門/跳躍）；🔴 LOCKED=先修未過，禁止跳推（exit 3）；UNKNOWN=未建節點（exit 2）。"""
    pid = flags.get("id")
    if not pid or pid is True:
        print("用法: kg_check --id <pid>"); return
    kg = _load_kg(); passed = _kg_passed()
    node = kg["nodes"].get(pid)
    if not node:
        print(f"⚠ UNKNOWN  {pid} 尚未在知識圖譜——請先 kg_add 定位它（依其引用放到相應位置），再判可否推。")
        sys.exit(2)
    if node.get("spontaneous"):
        print(f"🟢 OPEN（跳躍節點）  {pid}：豁免先修，可推（跨域/金融/憑空點火）。"); return
    if not node.get("prereqs"):
        print(f"🟢 OPEN（入門節點）  {pid}：無先修，可推。"); return
    unmet = [r for r in node["prereqs"] if r not in passed]
    if not unmet:
        print(f"🟢 FRONTIER  {pid}：先修全部通過，可推。"); return
    print(f"🔴 LOCKED  {pid}：缺先修（尚未機制層 depth≥2 通過）：{unmet}")
    sugg = [r for r in unmet if r in kg["nodes"] and _kg_recommendable(r, kg["nodes"][r], passed)]
    if sugg:
        print(f"  → 改推其先修前沿：{sugg}")
    print("  ⛔ 禁止跳過先修直接推此節點（北極星：未通過先期知識不得跳躍）。")
    sys.exit(3)

def kg_frontier(domain=None):
    """列出各主領域『現在可推』的前沿節點（主領域推薦的天花板）。"""
    kg = _load_kg(); passed = _kg_passed()
    doms = [domain] if domain else ["cv", "llm", "diffusion"]
    print("\n🎓 知識圖譜前沿 kg_frontier（main 三篇只能落在 🔓；🔒 需先補先修）")
    print("─" * 54)
    for d in doms:
        nodes = {p: n for p, n in kg["nodes"].items() if n.get("domain") == d}
        if not nodes:
            print(f"  {d.upper()}: （圖譜尚無節點，先 kg_seed / kg_add）"); continue
        fr, lk, done = [], [], []
        for p, n in nodes.items():
            if p in passed: done.append(p); continue
            unmet = [r for r in n.get("prereqs", []) if r not in passed]
            if not unmet or n.get("spontaneous"): fr.append(p)
            else: lk.append((p, unmet))
        print(f"  {d.upper()}  ✅已過{len(done)} | 🔓前沿{len(fr)} | 🔒鎖定{len(lk)}")
        for p in fr:
            sp = "✨" if nodes[p].get("spontaneous") else "🔓"
            print(f"    {sp} {p}  L{nodes[p].get('level','?')}  {nodes[p].get('title','')[:40]}")
        for p, um in lk[:8]:
            print(f"    🔒 {p}  缺:{um}")
    print("─" * 54)
    print("  規則：main 每篇先 kg_check 為 🟢 才可推；🔴 就改推其先修前沿（禁止跳級）。")

def kg_show(domain=None):
    """以樹狀印出先修 DAG + 學習者進度。"""
    kg = _load_kg(); passed = _kg_passed(); seen = _kg_seen()
    doms = [domain] if domain else ["cv", "llm", "diffusion"]
    for d in doms:
        nodes = {p: n for p, n in kg["nodes"].items() if n.get("domain") == d}
        print(f"\n📚 {d.upper()} 知識圖譜（先修 DAG）")
        print("─" * 54)
        if not nodes:
            print("  （尚無節點）"); continue
        def mark(p):
            n = nodes[p]
            if p in passed: return "✅"
            if n.get("spontaneous"): return "✨"
            unmet = [r for r in n.get("prereqs", []) if r not in passed]
            return "🔓" if not unmet else ("👁" if p in seen else "🔒")
        roots = [p for p, n in nodes.items()
                 if not [r for r in n.get("prereqs", []) if r in nodes]]
        printed = set()
        def walk(p, prefix="", last=True):
            if p in printed: return
            printed.add(p)
            print(f"  {prefix}{'└─' if last else '├─'} {mark(p)} {p} L{nodes[p].get('level','?')} {nodes[p].get('title','')[:30]}")
            kids = [c for c, n in nodes.items() if p in n.get("prereqs", []) and c not in printed]
            for i, c in enumerate(kids):
                walk(c, prefix + ("   " if last else "│  "), i == len(kids) - 1)
        for i, r in enumerate(roots):
            walk(r, "", i == len(roots) - 1)
        for p in nodes:
            if p not in printed:
                print(f"  └─ {mark(p)} {p} L{nodes[p].get('level','?')} {nodes[p].get('title','')[:30]}")
                printed.add(p)
    print("\n  ✅機制層通過  🔓前沿(可推)  ✨跳躍節點  👁見過未過  🔒先修未完成")
    print("─" * 54)

def _kg_frontier_brief():
    """daily_brief 內嵌用：每主領域列出可推前沿 pid。"""
    kg = _load_kg()
    if not kg.get("nodes"):
        return
    passed = _kg_passed()
    print("  ▸ 🎓 知識圖譜前沿（main 三篇只能落在這些 🔓；有先修未過的節點禁止跳推）：")
    for d in ("cv", "llm", "diffusion"):
        nodes = {p: n for p, n in kg["nodes"].items() if n.get("domain") == d}
        fr = [p for p, n in nodes.items()
              if p not in passed and _kg_recommendable(p, n, passed)]
        print(f"      {d.upper()} 🔓 {fr if fr else '（無—先擴圖譜或補先修，改用入門節點）'}")


# ---------------------------------------------
# CLI
# ---------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    if   cmd == "boot":    boot()
    elif cmd == "daily":   boot(); daily_push()
    elif cmd == "teaser":  teaser(sys.argv[2]) if len(sys.argv) > 2 else print("需要 paper_id")
    elif cmd == "deep":    deep(sys.argv[2]) if len(sys.argv) > 2 else print("需要 paper_id")
    elif cmd == "assess":
        if len(sys.argv) < 4: print('用法: assess <id> "<answer>"'); return
        assess(sys.argv[2], sys.argv[3])
    elif cmd == "groups":  show_groups()
    elif cmd == "tree":    prereq_tree(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "status":  status()
    elif cmd == "snapshot": snapshot()
    elif cmd == "weekly_review":
        if len(sys.argv) < 6: print("需要 week + 3個回答"); return
        weekly_review(int(sys.argv[2]), sys.argv[3:6])
    elif cmd == "calibrate":
        if len(sys.argv) < 7: print("需要 cv llm diff minutes motivation"); return
        calibrate(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif cmd == "load_snapshot":
        load_snapshot(json.loads(" ".join(sys.argv[2:])))
    elif cmd == "mem_add":         mem_add(_parse_flags(sys.argv[2:]))
    elif cmd == "mem_consolidate": mem_consolidate()
    elif cmd == "mem_view":        mem_view(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "mem_context":     mem_context()
    elif cmd == "trend_add":       trend_add(_parse_flags(sys.argv[2:]))
    elif cmd == "rubric":          rubric(sys.argv[2]) if len(sys.argv) > 2 else print("需要 paper_id")
    elif cmd == "review":          review(_parse_flags(sys.argv[2:]))
    elif cmd == "learner_state":   learner_state()
    elif cmd == "reset_learner":   reset_learner()
    elif cmd == "journal_add":     journal_add(_parse_flags(sys.argv[2:]))
    elif cmd == "journal_list":    journal_list()
    elif cmd == "paper_xlsx":      import paperlog; paperlog.main(sys.argv[2:])
    elif cmd == "check_dup":       check_dup(_parse_flags(sys.argv[2:]))
    elif cmd == "week_plan":       week_plan(sys.argv[2:])
    elif cmd == "daily_brief":     daily_brief()
    elif cmd == "push_log":        push_log(_parse_flags(sys.argv[2:]))
    elif cmd == "roadmap_set":     roadmap_set(_parse_flags(sys.argv[2:]))
    elif cmd == "kg_seed":         kg_seed("--force" in sys.argv)
    elif cmd == "kg_add":          kg_add(_parse_flags(sys.argv[2:]))
    elif cmd == "kg_link":         kg_link(_parse_flags(sys.argv[2:]))
    elif cmd == "kg_check":        kg_check(_parse_flags(sys.argv[2:]))
    elif cmd == "kg_frontier":     kg_frontier(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "kg_show":         kg_show(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "integrity":       integrity()
    elif cmd == "streak":          streak()
    elif cmd == "light_checkin":   light_checkin(_parse_flags(sys.argv[2:]))
    elif cmd == "redirect_clear":  redirect_clear()
    elif cmd == "recall_due":      recall_due(_parse_flags(sys.argv[2:]))
    elif cmd == "recall_related":  recall_related(_parse_flags(sys.argv[2:]))
    elif cmd == "recall":          recall(_parse_flags(sys.argv[2:]))
    elif cmd == "skill_map":       skill_map(_parse_flags(sys.argv[2:]))
    elif cmd == "kb_search":       kb_search(sys.argv[2:])
    elif cmd == "kb_read":         kb_read(sys.argv[2:])
    elif cmd == "kb_queue":        kb_queue(_parse_flags(sys.argv[2:]))
    else:
        print(f"未知指令: {cmd}"); print(__doc__)

if __name__ == "__main__":
    main()
# rev: 2026-07-11 wild-track + memory-split + archive-rotation
# sync-touch: 2026-07-16b (daily run; force sandbox resync after stale mount)
# rev: 2026-11-11d fresh-install state.json bootstrap
# rev: 2026-11-11c paper-kb integration (kb_search/kb_read/kb_queue)
# rev: 2026-11-11b embedded-recall(recall_related), no standalone quiz
# rev: 2026-11-11 spaced-recall + skill_map(0-5) + recall-confirmed promotion
# EOF-SENTINEL: mentor.py 完整結尾（integrity 驗此標記；此行必須在檔案最後）
