# 完整性檢查（integrity）

> 目錄：../CLAUDE.md

## 什麼時候用
- 每日排程的**第一步**，任何其他指令之前。
- 改完 `mentor.py` 之後。

## 怎麼做
```
python3 -m py_compile mentor.py && python3 mentor.py integrity
```
`integrity` 檢查：mentor.py 可編譯、檔尾含 `EOF-SENTINEL`（防截斷）、所有狀態 JSON 可解析、kg.json 的跨檔參照（先修 slug 沒有孤兒、主領域節點有先修或標為入門）。

## 驗收標準
- 通過：沒有錯誤訊息、exit 0 → 才能繼續後續流程。
- 失敗（含 exit 4 = 檔尾哨兵遺失）：**停止流程，先修檔**。修法見 `dev_maintenance.md`。
- **絕對禁止手改 JSON 繞過主程式**（會造成漏 push_log、漏輪轉推進等狀態不一致）。

## 存放位置
- 檢查對象：`mentor.py`、`state.json`、`learner.json`、`push_log.json`、`kg.json`、`memory/*.json` 等（完整清單見 `file_map.md`）。
- 本步驟不寫任何檔。
