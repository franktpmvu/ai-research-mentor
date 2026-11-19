# 系統維護（改 mentor.py、除錯）

> 目錄：../CLAUDE.md

## 什麼時候用
- 要修改 `mentor.py` 或其他程式。
- `integrity` 失敗、系統報錯。

## 修改 mentor.py 的鐵則
1. **一律從沙箱端（bash）寫入**：用 python 讀舊檔 → 程式化替換（每個 anchor 先 assert 唯一）→ 寫回 mount 路徑。
   **禁止用 host 端 Edit／Write 工具直接改 mentor.py**（沙箱對這個檔的大小快取會凍結，host 端改大後尾段會被截掉）。
2. 檔案最後一行必須含 `EOF-SENTINEL`，改檔後要保留在檔尾。
3. 改前先備份到 `archive/<描述>_<日期>/`。
4. 新功能盡量放在獨立 .py（如 `paperlog.py`），mentor.py 只加一行指令分派，降低截斷風險。
5. 測試用隔離副本（例如 `/tmp/test_atomic`），不要汙染真實 `push_log.json`／`state.json`。

## 驗收標準（改完必做，雙側驗證）
- 沙箱端：`wc -l mentor.py`、`python3 -m py_compile mentor.py`、`python3 mentor.py integrity` 全過。
- host 端：讀檔尾確認 `EOF-SENTINEL` 存在。
- 對應的細則與 changelog 已更新（`changelog/README.md`）。

## integrity 失敗時
- 停止每日流程，先修檔；**絕對禁止手改 JSON 繞過主程式**。
- exit 4（缺 EOF-SENTINEL）＝ mentor.py 被截斷：從沙箱端用完整版寫回，再雙側驗證。
- JSON 損壞：從 `archive/` 找最近備份還原。

## 存放位置
- 備份：`archive/`。
- 檔案全表：`file_map.md`。
