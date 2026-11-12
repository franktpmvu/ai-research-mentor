"""sheetsync.py — 把 論文閱讀.xlsx 指定列匯出成 Google Sheet 可直接寫入的 JSON。

本機 xlsx 是主檔；Google Sheet 是同列號的鏡像。程式本身不連網、不需要 Google 憑證：
它只輸出 {"range": ..., "values": ...}，由導師用 Google Sheets 連接器的 update_values 寫入。
Sheet 的 ID 是個人設定，寫在 profile.md（不上傳 GitHub）。

用法：
  python3 sheetsync.py rows 68          # 單列
  python3 sheetsync.py rows 65-68       # 連續多列
  python3 sheetsync.py header           # 表頭（第 1 列）
"""
import json, os, sys
from datetime import date, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(BASE, "論文閱讀.xlsx")
SHEET_TAB = "工作表1"
NCOL = 13                      # A–M，與 paperlog.HEADERS 一致
CELL_MAX = 49000               # Google Sheets 單格上限 50000 字


def _cell(v):
    if v is None:
        return ""              # 空字串＝清空雲端該格，保持鏡像一致
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y/%m/%d")
    if isinstance(v, float) and v.is_integer():
        return int(v)
    s = v if isinstance(v, (int, float)) else str(v)
    if isinstance(s, str) and len(s) > CELL_MAX:
        s = s[:CELL_MAX] + "\n…（超過 Google Sheets 單格上限，完整內容見本機 xlsx）"
    return s


def _col(n):
    return chr(ord("A") + n - 1)


def export(r1, r2):
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    vals = [[_cell(ws.cell(r, c).value) for c in range(1, NCOL + 1)] for r in range(r1, r2 + 1)]
    return {"range": f"{SHEET_TAB}!A{r1}:{_col(NCOL)}{r2}", "values": vals}


def main(argv):
    if not argv or argv[0] not in ("rows", "header"):
        print(__doc__); sys.exit(1)
    if argv[0] == "header":
        out = export(1, 1)
    else:
        spec = argv[1]
        a, _, b = spec.partition("-")
        r1, r2 = int(a), int(b or a)
        if r1 < 2 or r2 < r1:
            raise SystemExit("❌ 列號需 ≥2 且起 ≤ 迄")
        out = export(r1, r2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
