# -*- coding: utf-8 -*-
"""paperlog.py — 把「真的有討論的論文」自動寫進 論文閱讀.xlsx（由 mentor.py paper_xlsx 呼叫）。

欄位規則（使用者 2026-11-02 定案）：
  C note      = 使用者打的字，逐字複製。只從 journal/ 的「使用者原始互動（逐字）」段落用程式擷取，
                 絕不手打、不改寫、不加任何標記。
  D question  = 導師的話，可精煉；格式自由（問題→解法→關鍵機制、導師回應、未釐清、補強文獻…）。
  H 以後      = 額外資訊欄（領域/判定/paper_id/背景知識/journal）。
"""
import os, re, sys, json, glob, shutil
from datetime import datetime, date

BASE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(BASE, "論文閱讀.xlsx")
LOCK = os.path.join(BASE, "~$論文閱讀.xlsx")          # Excel 開檔時產生的 owner file
PENDING = os.path.join(BASE, "paper_xlsx_pending.json")
BAK_DIR = os.path.join(BASE, "archive", "xlsx_bak")
BAK_SLOTS = 10
JOURNAL_DIR = os.path.join(BASE, "journal")

HEADERS = {1: "why we needs to read paper?", 2: "paper title", 3: "note", 4: "question",
           5: "URL", 6: "year", 7: "author",
           8: "領域", 9: "判定", 10: "paper_id", 11: "背景知識", 12: "journal",
           13: "對話脈絡（導師→你）"}
NCOL = max(HEADERS)
COL = {v: k for k, v in HEADERS.items()}


def _flags(args):
    out, i = {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            k = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                out[k] = args[i + 1]; i += 2
            else:
                out[k] = True; i += 1
        else:
            i += 1
    return out


def _load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ---------- note：從 journal 逐字擷取 ----------
def extract_user_text(jpath):
    """回傳 journal 中「使用者原始互動（逐字）」段落的原文，每段之間空一行。"""
    with open(jpath, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out, inside, cur = [], False, []
    for ln in lines:
        if ln.startswith("## "):
            if inside:
                break
            inside = ln.startswith("## 使用者原始互動")
            continue
        if not inside:
            continue
        if ln.startswith("> "):
            if cur:
                out.append("\n".join(cur))
            cur = [ln[2:]]
        elif ln == ">":
            if cur:
                out.append("\n".join(cur))
            cur = [""]
        elif ln == "":
            if cur:
                out.append("\n".join(cur)); cur = []
        else:
            if cur:                       # 多行輸入的續行
                cur.append(ln)
    if cur:
        out.append("\n".join(cur))
    out = [p for p in out if p.strip() and p.strip() != "_（未提供）_"]
    return "\n\n".join(out)


def user_paragraphs(jfiles):
    out = []
    for j in jfiles:
        t = extract_user_text(j)
        if t:
            out += t.split("\n\n")
    return out


def build_context(tmpl, paras):
    """tmpl 內用 {U1}{U2}… 代表使用者第 n 段原話；程式代入逐字原文，且每段必須剛好用一次。"""
    used = [int(n) for n in re.findall(r"\{U(\d+)\}", tmpl)]
    need = list(range(1, len(paras) + 1))
    if sorted(used) != need:
        raise SystemExit(f"❌ --context 的 {{U#}} 必須剛好涵蓋 U1..U{len(paras)} 各一次；目前：{sorted(used)}")
    return re.sub(r"\{U(\d+)\}", lambda m: paras[int(m.group(1)) - 1], tmpl)


def _resolve_journals(spec):
    files = []
    for part in [s.strip() for s in str(spec).split(",") if s.strip()]:
        cand = part if os.path.isabs(part) else os.path.join(JOURNAL_DIR, os.path.basename(part))
        hits = sorted(glob.glob(cand)) or sorted(glob.glob(os.path.join(JOURNAL_DIR, part)))
        if not hits:
            raise SystemExit(f"❌ 找不到 journal：{part}")
        files += hits
    seen, uniq = set(), []
    for f in files:
        if f not in seen:
            seen.add(f); uniq.append(f)
    return uniq


# ---------- 其他欄位的預設來源 ----------
def _kg_node(pid):
    kg = _load(os.path.join(BASE, "kg.json"), {})
    nodes = kg.get("nodes", kg) if isinstance(kg, dict) else {}
    return nodes.get(pid, {}) if isinstance(nodes, dict) else {}, nodes


def _verdict(pid):
    lj = _load(os.path.join(BASE, "learner.json"), {})
    best = None
    for ep in lj.get("episodic", []) if isinstance(lj.get("episodic"), list) else []:
        if ep.get("paper_id") != pid:
            continue
        for q in ep.get("qa_record", []) or []:
            best = q
        if best is None:
            best = {"result": ep.get("status")}
    if not best:
        return ""
    r = best.get("result", "")
    d = best.get("depth_score")
    return f"{r} d{d}" if d is not None else str(r)


def _norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = u.replace("arxiv.org/pdf/", "arxiv.org/abs/").removesuffix(".pdf")
    return re.sub(r"v\d+$", "", u).rstrip("/")


def _norm_title(t):
    return re.sub(r"[^0-9a-z一-鿿]", "", (t or "").lower())


def _text(v):
    if not isinstance(v, str):
        return ""
    if os.path.isfile(v):                         # 允許傳檔案路徑，避免 shell 跳脫地獄
        with open(v, encoding="utf-8") as f:
            return f.read().strip()
    return v.replace("||", "\n").strip()


# ---------- xlsx 寫入 ----------
def _backup():
    os.makedirs(BAK_DIR, exist_ok=True)
    slots = [os.path.join(BAK_DIR, f"論文閱讀_bak{i}.xlsx") for i in range(BAK_SLOTS)]
    missing = [s for s in slots if not os.path.exists(s)]
    target = missing[0] if missing else min(slots, key=os.path.getmtime)
    shutil.copyfile(XLSX, target)                 # 輪替覆寫，不需要刪檔權限
    return target


def _write(entry, dry=False):
    import openpyxl
    from copy import copy
    from openpyxl.styles import Alignment

    wb = openpyxl.load_workbook(XLSX)
    wbv = openpyxl.load_workbook(XLSX, data_only=True)
    ws, wsv = wb.worksheets[0], wbv.worksheets[0]

    # 1) 補表頭（只補空的）
    for c, h in HEADERS.items():
        if ws.cell(1, c).value in (None, ""):
            ws.cell(1, c).value = h
    # 2) A 欄自我參照 NOW() 公式 → 凍結成固定日期（openpyxl 存檔會丟掉公式快取，不凍結舊日期會壞）
    frozen = 0
    last = 1
    for r in range(2, ws.max_row + 1):
        b = ws.cell(r, 2).value
        if b not in (None, ""):
            last = r
            a = ws.cell(r, 1)
            if isinstance(a.value, str) and a.value.startswith("="):
                cached = wsv.cell(r, 1).value
                if isinstance(cached, str):          # TEXT() 公式的快取是字串
                    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
                        try:
                            cached = datetime.strptime(cached.strip(), fmt); break
                        except ValueError:
                            pass
                if isinstance(cached, (datetime, date)):
                    a.value = cached; a.number_format = "yyyy/mm/dd"; frozen += 1
                else:
                    raise SystemExit(f"❌ 第 {r} 列 A 欄公式沒有可用的日期快取（{cached!r}），停手不寫，避免日期被洗掉")
        y = ws.cell(r, 6)
        if isinstance(y.value, float) and y.value.is_integer():
            y.value = int(y.value)

    # 3) 找既有列（paper_id → URL → 標題）
    row = None
    for r in range(2, last + 1):
        if entry["pid"] and str(ws.cell(r, 10).value or "") == entry["pid"]:
            row = r; break
    if row is None and entry["url"]:
        for r in range(2, last + 1):
            if _norm_url(ws.cell(r, 5).value) == _norm_url(entry["url"]):
                row = r; break
    if row is None and entry["title"]:
        for r in range(2, last + 1):
            if _norm_title(ws.cell(r, 2).value) == _norm_title(entry["title"]):
                row = r; break

    wrap = Alignment(wrap_text=True, vertical="top")
    if row is not None and entry.get("replace"):
        mode = "覆寫"
        ws.cell(row, 3).value = entry["note"] or None
        ws.cell(row, 4).value = entry["question"] or None
        ws.cell(row, 12).value = "\n".join(entry["journals"]) or None
        ws.cell(row, 13).value = entry["context"] or None
        if entry["bg"]:
            ws.cell(row, 11).value = entry["bg"]
    elif row is None:
        row = last + 1
        mode = "新增"
        src = last if last >= 2 else None
        if src:
            for c in range(1, NCOL + 1):
                s, d = ws.cell(src, c), ws.cell(row, c)
                if s.has_style:
                    d.font = copy(s.font); d.border = copy(s.border); d.fill = copy(s.fill)
        ws.cell(row, 1).value = datetime.strptime(entry["date"], "%Y-%m-%d")
        ws.cell(row, 1).number_format = "yyyy/mm/dd"
        ws.cell(row, 2).value = entry["title"]
        ws.cell(row, 3).value = entry["note"] or None
        ws.cell(row, 4).value = entry["question"] or None
        ws.cell(row, 12).value = "\n".join(entry["journals"]) or None
        ws.cell(row, 13).value = entry["context"] or None
    else:
        mode = "追記"
        old_j = str(ws.cell(row, 12).value or "")
        new_j = [j for j in entry["journals"] if j not in old_j]
        if not new_j and entry["journals"]:
            print("ℹ️  這些 journal 都已寫過此列，跳過（冪等）。")
            return None
        # note 只能有使用者的字：直接接在後面，不加日期標記
        new_note = "\n\n".join(extract_user_text(os.path.join(JOURNAL_DIR, j)) for j in new_j) \
            if new_j else entry["note"]
        oc = ws.cell(row, 3).value
        if new_note:
            ws.cell(row, 3).value = (str(oc) + "\n\n" + new_note) if oc else new_note
        od = ws.cell(row, 4).value
        if entry["question"]:
            tag = f"[{entry['date'][5:].replace('-', '/')} 追記]\n"
            ws.cell(row, 4).value = (str(od) + "\n\n" + tag + entry["question"]) if od else entry["question"]
        if entry["context"]:
            om = ws.cell(row, 13).value
            tag = f"[{entry['date'][5:].replace('-', '/')} 追記]\n"
            ws.cell(row, 13).value = (str(om) + "\n\n" + tag + entry["context"]) if om else entry["context"]
        if new_j:
            ws.cell(row, 12).value = (old_j + "\n" if old_j else "") + "\n".join(new_j)
        if not ws.cell(row, 2).value:
            ws.cell(row, 2).value = entry["title"]

    def setv(c, v):
        if v not in (None, ""):
            ws.cell(row, c).value = v
    setv(5, entry["url"]); setv(6, entry["year"]); setv(7, entry["authors"])
    setv(8, entry["domain"]); setv(9, entry["verdict"]); setv(10, entry["pid"])
    if entry["bg"] and not ws.cell(row, 11).value:
        ws.cell(row, 11).value = entry["bg"]
    for c in range(1, NCOL + 1):
        ws.cell(row, c).alignment = wrap

    for col, w in {"F": 7, "G": 22, "H": 9, "I": 10, "J": 16, "K": 30, "L": 34, "M": 60}.items():
        if not ws.column_dimensions[col].width or ws.column_dimensions[col].width < w:
            ws.column_dimensions[col].width = w

    print(f"📝 {mode} → 第 {row} 列｜{entry['title']}")
    if frozen:
        print(f"   A 欄凍結 {frozen} 個日期公式為固定值")
    if dry:
        print("—— dry run：未寫入 ——")
        for c in range(1, NCOL + 1):
            v = ws.cell(row, c).value
            print(f"   [{HEADERS[c]}] {str(v)[:300] if v is not None else ''}")
        return row
    bak = _backup()
    wb.save(XLSX)
    # 驗證
    chk = openpyxl.load_workbook(XLSX).worksheets[0]
    assert chk.cell(row, 2).value, "寫入後驗證失敗：標題為空"
    print(f"✅ 已寫入 論文閱讀.xlsx（備份：archive/xlsx_bak/{os.path.basename(bak)}）")
    return row


def build_entry(f):
    pid = f.get("pid") if isinstance(f.get("pid"), str) else ""
    node, _ = _kg_node(pid) if pid else ({}, {})
    if not isinstance(f.get("journal"), str):
        raise SystemExit("❌ 需要 --journal：note 欄只能從 journal 逐字擷取")
    jfiles = _resolve_journals(f["journal"])
    note = "\n\n".join(t for t in (extract_user_text(j) for j in jfiles) if t)
    ctx_t = _text(f.get("context"))
    if not ctx_t:
        raise SystemExit("❌ 需要 --context：導師提問與 {U#} 原話交錯的對話脈絡（幾年後回看才讀得懂）")
    context = build_context(ctx_t, user_paragraphs(jfiles))
    _, nodes = _kg_node("")
    bg = _text(f.get("bg"))
    if not bg and node.get("prereqs"):
        bg = "先修：" + "、".join((nodes.get(p, {}) or {}).get("title", p) for p in node["prereqs"])
    d = f.get("date") if isinstance(f.get("date"), str) else \
        re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(jfiles[0])).group(1)
    year = f.get("year")
    return {
        "pid": pid,
        "title": _text(f.get("title")) or node.get("title", pid),
        "url": _text(f.get("url")) or node.get("url", ""),
        "year": int(year) if isinstance(year, str) and year.isdigit() else None,
        "authors": _text(f.get("authors")),
        "domain": _text(f.get("domain")) or node.get("domain", ""),
        "verdict": _text(f.get("verdict")) or (_verdict(pid) if pid else ""),
        "bg": bg,
        "note": note,
        "question": _text(f.get("question")),
        "journals": [os.path.basename(j) for j in jfiles],
        "context": context,
        "replace": bool(f.get("replace")),
        "date": d,
    }


def _queue(entry):
    q = _load(PENDING, [])
    q.append(entry)
    with open(PENDING, "w", encoding="utf-8") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=2)


def flush():
    q = _load(PENDING, [])
    if not q:
        return
    if os.path.exists(LOCK):
        print(f"⏳ 待寫佇列 {len(q)} 筆，Excel 仍開著，下次再補。"); return
    left = []
    for e in q:
        try:
            _write(e)
        except Exception as ex:
            print(f"⚠️ 補寫失敗：{e.get('title')}｜{ex}"); left.append(e)
    with open(PENDING, "w", encoding="utf-8") as fh:
        json.dump(left, fh, ensure_ascii=False, indent=2)
    print(f"🔁 待寫佇列處理完：剩 {len(left)} 筆")


def main(argv):
    f = _flags(argv)
    if f.get("flush"):
        flush(); return
    entry = build_entry(f)
    if not entry["note"]:
        print("⚠️ journal 裡沒有使用者原話，note 會是空的")
    if f.get("dry"):
        _write(entry, dry=True); return
    flush()
    if os.path.exists(LOCK):
        _queue(entry)
        print("⏳ 論文閱讀.xlsx 正被 Excel 開著 → 已存進 paper_xlsx_pending.json，關檔後下次 done 自動補寫")
        return
    _write(entry)


if __name__ == "__main__":
    main(sys.argv[1:])
