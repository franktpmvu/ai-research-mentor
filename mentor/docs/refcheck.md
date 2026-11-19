# 文獻強制核實（refcheck）

> 目錄：../CLAUDE.md

## 什麼時候用
- **任何文獻要講出口、進記憶、推播、寫試算表之前**。沒有略過開關。
- 在對話裡提到任何具體文獻（作者、年份、標題、編號）之前。

## 程式把關的三個入口
| 入口 | 檢查什麼 | 未過 |
|---|---|---|
| `mem_add` | 標題＋網址 | exit 5，不寫入 |
| `push_log`（含 `--dry`） | main：標題＋網址；xdomain／finance／wild：必須附第四欄網址且已核實 | 列為 problems，exit 3 |
| `paper_xlsx` | 主文獻＋D 欄【補強文獻】每一條 | 整筆不寫入 |

## 怎麼做（在專案資料夾執行）
- **arXiv 文獻（自動）**：
  `python3 refcheck.py check --title "正式標題" --url <arXiv或論文網址> [--authors "Lee et al."] [--year 2018]`
  （走 arXiv 官方 API＋本機 paper-kb）
- **非 arXiv（期刊、書、部落格、新聞）**：本機只連得到 arXiv，所以先**用網頁工具實際打開頁面**，抄下頁面上的標題，再登記：
  `python3 refcheck.py manual --seen-title "頁面上的標題" --evidence <打開的網址> --authors "..." --year 2024 --note "期刊/卷期"`
  程式會拒絕：標題對不上、證據不是網址、其實是 arXiv 文獻（arXiv 一律走自動）。
- 稽核整份試算表：`python3 refcheck.py audit_xlsx`；看登記簿：`python3 refcheck.py ledger`。
- 查不到 → **不要講出具體出處**，改說「我不確定出處」。
- 數字細節（章節號、頁碼、年份、期刊）一律以核實結果為準，不憑記憶補。

## 【補強文獻】格式（paper_xlsx 逐條檢查）
每條用「；」或換行分開，每條都要「正式英文標題＋識別碼」：
```
【補強文獻】Energy-based Out-of-distribution Detection [arXiv:2010.03759]；Loss of plasticity in deep continual learning [url:https://www.amii.ca/research/loss-of-plasticity-in-deep-continual-learning] 補可塑性
```
識別碼三選一：`[arXiv:編號]`、`[doi:10.xxx/yyy]`、`[url:https://...]`。程式會拿識別碼查到的正式標題回頭比對（防張冠李戴）。

## 驗收標準
- 三個入口都沒有被拒；`refcheck.py ledger` 裡查得到每一筆用過的文獻。

## 能力限界
- 自動化只涵蓋 arXiv 與本機論文庫；其他來源靠「真的打開頁面＋登記證據網址」，程式驗得了標題一致與格式，驗不了你是否讀過內容（使用者可點證據網址抽查）。
- 跨域／金融鏡子核實的是**出處存在**，不是類比本身正確。

## 存放位置
- `ref_ledger.json`（只存公開書目資料；查過一次就記住）。
- 程式：`refcheck.py`（也可用 `python3 mentor.py refcheck ...`）。
