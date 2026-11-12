# 文獻強制核實（refcheck）— docs/refcheck.md

> 入口：../CLAUDE.md。2026-11-12 使用者要求：**每一筆文獻都必須是真的，而且核實這一步要被強制驗證，不能靠自律。**
> 起因：稽核發現導師記憶裡有連結指錯論文、把論文小節標題當成論文標題、編出副標題的情況；試算表也有標題記錯（ReDiF）。

## 鐵則
1. **沒核實的文獻不能出現在任何紀錄或推播裡**。程式在三個入口把關，未過就拒絕（沒有略過開關）：
   | 入口 | 檢查什麼 | 未過 |
   |---|---|---|
   | `mem_add`（新論文進記憶） | 標題＋網址 | exit 5，不寫入 |
   | `push_log`（含 `--dry` 預檢） | main：標題＋網址；跨域/金融/wild：**必須附出處網址（第四欄）且網址已核實** | 列為 problems，exit 3 |
   | `paper_xlsx`（done 寫試算表） | 主文獻＋D 欄【補強文獻】每一條 | 不寫入 |
2. **在對話裡提到的任何具體文獻（作者、年份、標題、編號），講之前先核實**：有 arXiv 編號就 `refcheck check`；沒有就先上網打開頁面，再 `manual` 登記。查不到就不要講出具體出處，改說「我不確定出處」。
3. 數字細節（章節號、頁碼、年份、期刊）也要以核實結果為準，不要憑記憶補。

## 怎麼核實（全部在專案資料夾執行）
- 自動（arXiv 官方 API + 本機 paper-kb 論文庫）：
  `python3 refcheck.py check --title "正式標題" --url <arXiv或論文網址> [--authors "Lee et al."] [--year 2018]`
- 非 arXiv（期刊、書、部落格、新聞）：本機只連得到 arXiv，所以要**先用網頁工具實際打開頁面**，抄下頁面上的標題，再登記：
  `python3 refcheck.py manual --seen-title "頁面上的標題" --evidence <打開的網址> --authors "..." --year 2024 --note "期刊/卷期"`
  程式會拒絕：標題對不上、證據不是網址、或其實是 arXiv 文獻（arXiv 一律走自動）。
- 稽核整份試算表：`python3 refcheck.py audit_xlsx`；看登記簿：`python3 refcheck.py ledger`。
- 結果存在 `ref_ledger.json`（只有公開書目資料）。查過一次就記住。

## 【補強文獻】格式（paper_xlsx 會逐條檢查）
每條用「；」或換行分開，每條都要有**正式英文標題＋識別碼**：
```
【補強文獻】Energy-based Out-of-distribution Detection [arXiv:2010.03759]；Loss of plasticity in deep continual learning [url:https://www.amii.ca/research/loss-of-plasticity-in-deep-continual-learning] 補可塑性
```
識別碼三選一：`[arXiv:編號]`、`[doi:10.xxx/yyy]`、`[url:https://...]`。程式會拿識別碼查到的正式標題回頭比對你寫的標題（防「編號對、標題張冠李戴」）。

## 誠實限界
- 自動化只涵蓋 arXiv 與本機論文庫；其他來源靠「導師真的打開頁面＋登記證據網址」，程式能驗標題一致與格式，但無法替你確認導師真的讀過內容——使用者可以隨時點證據網址抽查。
- 推播的跨域/金融鏡子是「借概念重講機制」，核實的是**出處**存在，不是類比本身正確。
