# AI Research Mentor

[English](README.md) | **繁體中文**

用「原子習慣」的方式，讓 AI 當你的研究導師：每天推幾篇論文、用提問帶你把機制講對、記住你學到哪裡。
再配一個地端論文知識庫，讓導師講機制前能先翻你讀過的論文原文。

| 資料夾 | 是什麼 | 需要什麼 |
|---|---|---|
| [`mentor/`](mentor/) | 導師系統：每日推播、深讀評估、知識圖譜先修守門、記憶系統、技能地圖、營養學小軌 | Python 3.10+（不用裝套件；寫 Excel 紀錄才需要 `openpyxl`） |
| [`paper-kb/`](paper-kb/) | 論文知識庫：PDF → 帶頁碼的全文索引，提供 MCP server 給任何 AI 用 | Python 3.11+、`pip install -r requirements.txt` |

兩者可以分開用；放在一起時會自動串起來（見下方「整合」）。

## 安裝

```bash
git clone https://github.com/franktpmvu/ai-research-mentor.git
cd ai-research-mentor

# 1. 導師系統：不用安裝，直接能跑
python3 mentor/mentor.py integrity      # 檢查 → 第一次執行會自動建立狀態檔

# 2. 論文知識庫（選用）
cd paper-kb
pip install -r requirements.txt         # Windows 可直接雙擊 maintain.bat，會自動建 .venv
# 把 PDF 丟進 paper-kb/input_raw/inbox/，然後：
python update.py
```

## 使用

導師系統是**給 AI 讀的規則＋給 AI 跑的指令**，本身不是聊天程式。用法是讓 Claude（Claude Code、Claude 桌面版等能讀資料夾、跑指令的 AI）打開 `mentor/` 資料夾：

1. AI 會先讀 `mentor/CLAUDE.md`（規則入口），再照裡面的對照表讀 `mentor/docs/`。
2. 對它說「跑今天的推播」→ 它會照 `docs/daily_push.md` 搜論文、驗重複、守先修、推給你。
3. 你回覆討論 → 它用提問帶你把機制講對（一次一題、不直接給答案），並記錄你的程度。
4. 說「done」→ 收尾、打卡、寫紀錄。沒力氣時只打卡也算（習慣 > 完美）。
5. 想每天自動推：用 Claude 的排程功能，排程內容只要寫「讀 `mentor/CLAUDE.md` 照規則跑每日推播」。

所有指令見 [`mentor/docs/commands.md`](mentor/docs/commands.md)；論文知識庫的工具見 [`paper-kb/README.md`](paper-kb/README.md)。

## 文獻強制核實

LLM 會記錯標題、甚至編出不存在的論文。`mentor/refcheck.py` 用 arXiv 官方 API 與本機 paper-kb 核對每一筆文獻；其他來源（期刊、書、部落格）必須上網打開並登記證據網址。程式在三個入口把關、沒有略過開關：論文進記憶（`mem_add`）、每日推播（`push_log`，每篇都要有已核實的出處網址）、閱讀紀錄（`paper_xlsx`，主文獻與每一條補強文獻）。規則見 [`mentor/docs/refcheck.md`](mentor/docs/refcheck.md)。

## 個人設定（唯一需要自己填的地方，都不會上傳）

| 檔案 | 內容 | 沒有的話 |
|---|---|---|
| `mentor/profile.md` | 你的背景、目標、學習時常卡的地方、偏好 | 用 `profile.example.md` 的通用預設 |
| `paper-kb/config.json` | 哪些 PDF 是你自己發表的論文（用來建「你引用了誰」） | 視為沒有，其他功能照常 |

複製範本再改：`cp mentor/profile.example.md mentor/profile.md`、`cp paper-kb/config.example.json paper-kb/config.json`。

## 整合（兩者放在同一層時自動生效）

- **講機制前先核對原文**：導師用 `kb_search` / `kb_read` 直接讀 paper-kb 的索引（不需要 MCP），講解時附頁碼。
- **讀完的論文自動收進知識庫**：done 收尾時 `kb_queue --url ...` 把論文網址排進 `paper-kb/input_raw/url_queue.txt`，paper-kb 下次維護時自動下載、解析、索引。
- paper-kb 不在旁邊時，可用環境變數 `PAPER_KB_ROOT` 指定位置；找不到就自動略過，導師系統照常運作。

細節：[`mentor/docs/paper_kb.md`](mentor/docs/paper_kb.md)。

## 不上傳的東西

你的學習紀錄（`state.json`、`learner.json`、`journal/`、`memory/`…）、個人設定、論文 PDF 與索引都在 `.gitignore` 裡。repo 只有程式、規則文件和範本。

## 致謝

`mentor/docs/learner_eval.md` 的蘇格拉底式提問規則與技能地圖（0–5 級），參考了 Jane Street 的 [agent_skills / socratic-tutor](https://github.com/janestreet/agent_skills)（MIT）。

## 授權

[MIT](LICENSE)
