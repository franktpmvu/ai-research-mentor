# -*- coding: utf-8 -*-
"""refcheck.py — 文獻真實性強制核實（2026-11-12 新增）

為什麼有這個檔：導師（LLM）會「記錯標題」甚至「編出不存在的文獻」。
規則：任何要寫進紀錄或推播給使用者的文獻，都必須先在這裡被核實，否則程式拒絕寫入。

核實來源（依序，全部程式化、不靠 LLM 自律）：
  1. arXiv 官方 API（有 arXiv 編號的，用編號查；沒有編號的，用標題搜）
  2. paper-kb 本機論文庫（使用者自己下載、已解析的 PDF；比對 arXiv 編號／DOI／標題）
  3. 人工登記（web-manual）：前兩者都查不到的（期刊、書、部落格），導師必須真的上網打開頁面，
     用 `manual` 指令登記「看到的標題 + 證據網址」，登記時程式會比對標題一致才收。

結果寫在 ref_ledger.json（同一篇查過一次就記住，下次不用再連網）。

指令：
  python3 refcheck.py check --title "..." [--url ...] [--authors "Lee et al."] [--year 2018]
  python3 refcheck.py text <檔案>            檢查文字裡的【補強文獻】段（格式見下）
  python3 refcheck.py manual --title "..." --seen-title "..." --evidence <網址> [--authors] [--year] [--note]
  python3 refcheck.py audit_xlsx [--rows 2-80]  掃 論文閱讀.xlsx 全部列，列出未核實／標題不符
  python3 refcheck.py ledger [--bad]          看登記簿

【補強文獻】格式（paper_xlsx 會強制檢查）：每條一行或用「；」分隔，每條都要有
  「正式英文標題 + 識別碼」，識別碼是 [arXiv:2010.03759]、[doi:10.xxx/yyy] 或 [url:https://...] 其中之一。
  例：Energy-based Out-of-distribution Detection [arXiv:2010.03759]
  可以在後面加中文說明，但標題必須是論文的正式標題（程式會拿去比對）。
"""
import os, re, sys, json, time, difflib, unicodedata, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(BASE, "ref_ledger.json")
XLSX = os.path.join(BASE, "論文閱讀.xlsx")
ARXIV_API = "https://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
TITLE_OK = 0.88          # 標題相似度門檻（正規化後）

ARX_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf|html)/|arxiv\s*[:：]\s*|\[arxiv\s*[:：]\s*)"
    r"((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[a-z]{2})?/\d{7}))(?:v\d+)?", re.I)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"<>，。；、\]\)）]+)", re.I)
URL_RE = re.compile(r"https?://[^\s\"<>，。；、\]）]+", re.I)


# ---------------- 正規化與比對 ----------------
def norm(t):
    t = unicodedata.normalize("NFKC", str(t or "")).lower()
    t = t.replace("‐", "-").replace("–", "-").replace("—", "-")
    t = re.sub(r"[^0-9a-z一-鿿]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _strip_paren(t):
    return re.sub(r"\s*[\(（][^\)）]*[\)）]\s*$", "", str(t or "")).strip()

def title_sim(claimed, true):
    a, b = norm(claimed), norm(true)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    best = difflib.SequenceMatcher(None, a, b).ratio()
    a2 = norm(_strip_paren(claimed))
    if a2:
        best = max(best, difflib.SequenceMatcher(None, a2, b).ratio())
    # 只寫了主標題（冒號前）也算：例如 "RT-DETRv4" vs 完整標題 → 不算；"DEIM: DETR with ..." 完整 → 算
    if ":" in str(true):
        head = norm(str(true).split(":")[0])
        if len(head) >= 12 and a2 == head:
            best = max(best, 0.9)
    return best

def coverage(entry_text, true):
    """正式標題的詞有多少出現在 entry 裡（補強文獻那種「標題+說明」用）。"""
    tt = [w for w in norm(true).split() if len(w) > 1]
    et = set(norm(entry_text).split())
    if not tt:
        return 0.0
    return sum(1 for w in tt if w in et) / len(tt)

def first_surname(authors):
    s = re.sub(r"\bet\s*al\.?.*$", "", str(authors or ""), flags=re.I)
    s = re.split(r"[,;&，、]| and ", s)[0]
    s = re.sub(r"\(.*?\)", "", s).strip()
    toks = [t for t in re.split(r"\s+", s) if t]
    if not toks:
        return ""
    # "Kimin Lee" → lee；"Malaisree P" → malaisree；"Takehi" → takehi
    cand = [t for t in toks if len(t.strip(".")) > 1]
    return norm(cand[-1] if len(cand) >= 2 else (cand[0] if cand else toks[0]))

def author_ok(claimed, authors_list):
    sn = first_surname(claimed)
    if not sn:
        return None
    names = [norm(a) for a in authors_list]
    return any(f" {sn} " in f" {n} " for n in names)


# ---------------- 登記簿 ----------------
def _load_ledger():
    try:
        with open(LEDGER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"entries": {}}

def _save_ledger(L):
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(L, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LEDGER)

def _key(arxiv="", doi="", url="", title=""):
    if arxiv: return "arxiv:" + arxiv.lower()
    if doi:   return "doi:" + doi.lower().rstrip(".")
    if url:   return "url:" + url.split("#")[0].rstrip("/").lower()
    return "title:" + norm(title)

def ids_from(text):
    text = str(text or "")
    a = ARX_RE.search(text)
    d = DOI_RE.search(text)
    u = URL_RE.search(text)
    return (a.group(1) if a else ""), (d.group(1).rstrip(".") if d else ""), (u.group(0) if u else "")


# ---------------- 來源 1：arXiv ----------------
_last_call = [0.0]
def _arxiv_query(params):
    wait = 3.1 - (time.time() - _last_call[0])      # arXiv 要求呼叫間隔 ≥3 秒
    if wait > 0:
        time.sleep(wait)
    url = ARXIV_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "ai-research-mentor-refcheck/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            _last_call[0] = time.time()
            break
        except Exception as ex:
            _last_call[0] = time.time()
            if attempt == 2:
                raise RuntimeError(f"arXiv API 連不上：{ex}")
            time.sleep(4)
    root = ET.fromstring(data)
    out = []
    for e in root.findall(ATOM + "entry"):
        eid = (e.findtext(ATOM + "id") or "").strip()
        title = re.sub(r"\s+", " ", e.findtext(ATOM + "title") or "").strip()
        if "api/errors" in eid or title.lower() == "error":
            continue
        m = re.search(r"abs/(.+?)(v\d+)?$", eid)
        out.append({
            "arxiv": m.group(1) if m else "",
            "title": title,
            "authors": [(a.findtext(ATOM + "name") or "").strip() for a in e.findall(ATOM + "author")],
            "year": (e.findtext(ATOM + "published") or "")[:4],
        })
    return out

def arxiv_by_ids(ids):
    res = {}
    ids = [i for i in dict.fromkeys(ids) if i]
    for k in range(0, len(ids), 40):
        chunk = ids[k:k + 40]
        for rec in _arxiv_query({"id_list": ",".join(chunk), "max_results": len(chunk)}):
            res[rec["arxiv"].lower()] = rec
    return res

def arxiv_by_title(title):
    t = re.sub(r"[^0-9A-Za-z\s]", " ", _strip_paren(title))
    stop = {"for", "and", "the", "with", "from", "via", "into", "using", "of", "to", "in", "on",
            "or", "not", "an", "by", "at", "is", "are", "as", "its", "how", "what", "why", "when"}
    words = [w for w in t.split() if len(w) > 1 and w.lower() not in stop][:10]
    if not words:
        return None
    q = " AND ".join(f"ti:{w}" for w in words)
    best, bs = None, 0.0
    for rec in _arxiv_query({"search_query": q, "max_results": 10}):
        s = title_sim(title, rec["title"])
        if s > bs:
            best, bs = rec, s
    return best if bs >= TITLE_OK else None


# ---------------- 來源 2：paper-kb 本機論文庫 ----------------
def _kb_docs():
    import sqlite3
    for root in [os.environ.get("PAPER_KB_ROOT", ""),
                 os.path.join(os.path.dirname(BASE), "paper-kb"),
                 os.path.join(os.path.dirname(BASE), "paper-rag-mcp")]:
        dbp = os.path.join(root, "data", "derived", "index", "papers.db") if root else ""
        if dbp and os.path.exists(dbp):
            c = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
            rows = c.execute("select doc_id,title,arxiv,doi,path from docs").fetchall()
            c.close()
            return rows
    return []

_KB = None
def kb_lookup(title="", arxiv="", doi=""):
    global _KB
    if _KB is None:
        _KB = _kb_docs()
    for doc_id, t, a, d, p in _KB:
        if arxiv and a and a.lower() == arxiv.lower():
            return {"doc_id": doc_id, "title": t, "path": p, "how": "arxiv"}
        if doi and d and d.lower().rstrip(").") == doi.lower():
            return {"doc_id": doc_id, "title": t, "path": p, "how": "doi"}
    if title:
        best, bs = None, 0.0
        for doc_id, t, a, d, p in _KB:
            s = title_sim(title, t)
            if s > bs:
                best, bs = (doc_id, t, p), s
        if best and bs >= 0.92:
            return {"doc_id": best[0], "title": best[1], "path": best[2], "how": "title"}
    return None


# ---------------- 主判定 ----------------
def verify(title="", url="", authors="", year="", arxiv="", doi="", offline=False, record=True):
    """回傳 dict：status ∈ verified / mismatch / not_found / unverifiable。
    mismatch = 文獻存在但標題或作者對不上（會附正確資訊）。"""
    a2, d2, u2 = ids_from(url)
    arxiv = arxiv or a2
    doi = doi or d2
    url = url or u2
    L = _load_ledger()
    key = _key(arxiv, doi, url if not (arxiv or doi) else "", title)
    res = {"title": title, "url": url, "arxiv": arxiv, "doi": doi, "authors_claimed": authors,
           "year_claimed": str(year or ""), "checked_at": datetime.now().isoformat(timespec="seconds")}

    # 0. 登記簿（含人工登記）
    hit = L["entries"].get(key) or (L["entries"].get(_key(title=title)) if title else None)
    if hit and hit.get("true_title"):
        sim = title_sim(title, hit["true_title"]) if title else 1.0
        if sim >= TITLE_OK or (not title):
            ok_a = author_ok(authors, hit.get("authors", [])) if authors and hit.get("authors") else None
            st = "verified" if ok_a in (None, True) else "mismatch"
            return dict(res, **{k: hit.get(k) for k in ("true_title", "authors", "true_year", "source", "evidence")},
                        status=st, title_sim=round(sim, 3), author_ok=ok_a, cached=True,
                        problem="" if st == "verified" else f"第一作者對不上：登記為 {hit.get('authors', [])[:3]}")

    rec, source, evidence = None, "", ""
    # 1. arXiv
    if not offline:
        try:
            if arxiv:
                rec = arxiv_by_ids([arxiv]).get(arxiv.lower())
                if rec is None:
                    out = dict(res, status="not_found", problem=f"arXiv:{arxiv} 不存在")
                    return out
                source, evidence = "arxiv-api", f"https://arxiv.org/abs/{rec['arxiv']}"
            elif title and not doi:
                rec = arxiv_by_title(title)
                if rec:
                    source, evidence = "arxiv-api(title)", f"https://arxiv.org/abs/{rec['arxiv']}"
        except RuntimeError as ex:
            res["net_error"] = str(ex)
    # 2. paper-kb
    if rec is None:
        kb = kb_lookup(title, arxiv, doi)
        if kb:
            rec = {"title": kb["title"], "authors": [], "year": "", "arxiv": arxiv}
            source, evidence = f"paper-kb({kb['how']})", f"paper-kb:{kb['doc_id']} {kb['path']}"
    if rec is None:
        why = "（有 DOI／網址但不在 arXiv 與本機論文庫，需上網打開頁面後用 manual 登記）" if (doi or url) \
              else "（arXiv 與本機論文庫都找不到；若確定存在，上網查到後用 manual 登記證據網址）"
        return dict(res, status="unverifiable" if (doi or url) else "not_found", problem="查無此文獻" + why)

    sim = title_sim(title, rec["title"]) if title else 1.0
    ok_a = author_ok(authors, rec["authors"]) if authors and rec.get("authors") else None
    problems = []
    if title and sim < TITLE_OK:
        problems.append(f"標題不符：正式標題是「{rec['title']}」")
    if ok_a is False:
        problems.append(f"第一作者不符：實際作者 {', '.join(rec['authors'][:3])}…")
    yr_note = ""
    if year and rec.get("year") and str(year) != rec["year"]:
        yr_note = f"年份：arXiv 首次上傳 {rec['year']}（你寫 {year}；若是正式發表年可忽略）"
    out = dict(res, status="mismatch" if problems else "verified", true_title=rec["title"],
               authors=rec.get("authors", []), true_year=rec.get("year", ""), arxiv=rec.get("arxiv") or arxiv,
               source=source, evidence=evidence, title_sim=round(sim, 3), author_ok=ok_a,
               problem="；".join(problems), year_note=yr_note)
    if record:
        k = _key(out["arxiv"], doi, url if not (out["arxiv"] or doi) else "", rec["title"])
        L["entries"][k] = {kk: out.get(kk) for kk in
                           ("true_title", "authors", "true_year", "arxiv", "doi", "url", "source", "evidence", "checked_at")}
        _save_ledger(L)
    return out


def manual(title, seen_title, evidence, authors="", year="", note=""):
    """人工登記：只用在 arXiv／本機論文庫都查不到的文獻。導師必須真的打開 evidence 頁面、抄下頁面上的標題。"""
    if not evidence or not URL_RE.match(evidence):
        raise SystemExit("❌ --evidence 必須是實際打開過的網址（http/https）")
    if not seen_title:
        raise SystemExit("❌ --seen-title 必須填頁面上實際看到的標題")
    sim = title_sim(title, seen_title)
    if sim < TITLE_OK:
        raise SystemExit(f"❌ 你要登記的標題和頁面上看到的標題不一致（相似度 {sim:.2f}）。\n"
                         f"   頁面標題：{seen_title}\n   請改用頁面上的正式標題。")
    a, d, _ = ids_from(evidence)
    if a:
        raise SystemExit("❌ 這是 arXiv 文獻，請用 check 讓程式直接查 arXiv，不要人工登記")
    L = _load_ledger()
    k = _key("", d, evidence if not d else "", seen_title)
    L["entries"][k] = {"true_title": seen_title, "authors": [x.strip() for x in re.split(r"[,;]", authors) if x.strip()],
                       "true_year": str(year or ""), "doi": d, "url": evidence, "source": "web-manual",
                       "evidence": evidence, "note": note, "checked_at": datetime.now().isoformat(timespec="seconds")}
    # 也用標題當 key，讓沒附網址的引用也查得到
    L["entries"][_key(title=seen_title)] = L["entries"][k]
    _save_ledger(L)
    print(f"✅ 已人工登記：{seen_title}\n   證據：{evidence}")


# ---------------- 【補強文獻】段 ----------------
def refs_section(text):
    m = re.search(r"【補強文獻】(.*?)(?=\n\s*【|\n\s*\[\d{1,2}/\d{1,2} 追記\]|\Z)", str(text or ""), re.S)
    return m.group(1).strip() if m else ""

def split_entries(sec):
    parts = re.split(r"[；;]|\n|(?<=\])\s*[、,，|｜]\s*", sec)
    return [p.strip(" 　-•*·") for p in parts if p and p.strip(" 　-•*·")]

def check_text(text, offline=False):
    """回傳 (ok, 報告行list)。沒有【補強文獻】段 → ok。"""
    sec = refs_section(text)
    if not sec:
        return True, ["（沒有【補強文獻】段，略過）"]
    ok, lines = True, []
    for i, ent in enumerate(split_entries(sec), 1):
        a, d, u = ids_from(ent)
        if not (a or d or u):
            ok = False
            lines.append(f"❌ 第{i}條缺識別碼（要 [arXiv:...] / [doi:...] / [url:...]）：{ent[:80]}")
            continue
        claimed = re.split(r"\[|（|\(|https?://|arxiv\s*[:：]|doi\s*[:：]", ent, flags=re.I)[0].strip(" ：:—-")
        r = verify(title="", url=u, arxiv=a, doi=d, offline=offline)
        if r["status"] != "verified":
            ok = False
            lines.append(f"❌ 第{i}條 {r['status']}：{r.get('problem', '')}｜{ent[:80]}")
            continue
        cov = coverage(claimed or ent, r["true_title"])
        if cov < 0.85:
            ok = False
            lines.append(f"❌ 第{i}條 識別碼存在，但寫的標題對不上（{cov:.0%}）。正式標題：「{r['true_title']}」｜{ent[:80]}")
        else:
            lines.append(f"✅ 第{i}條 {r['true_title']}（{r['source']}）")
    return ok, lines


# ---------------- 給 paperlog / mentor 呼叫的守門 ----------------
def gate_entry(title, url="", authors="", year="", question=""):
    """paper_xlsx 寫入前呼叫。不通過就 SystemExit（沒有略過開關，這是使用者要求的強制步驟）。"""
    msgs, ok = [], True
    r = verify(title=title, url=url, authors=authors, year=year)
    if r["status"] == "verified":
        msgs.append(f"✅ 主文獻已核實：{r['true_title']}（{r['source']}）" + (f"\n   ⚠ {r['year_note']}" if r.get("year_note") else ""))
    else:
        ok = False
        msgs.append(f"❌ 主文獻 {r['status']}：{r.get('problem', '')}")
    tok, lines = check_text(question)
    ok = ok and tok
    msgs += ["   " + x for x in lines]
    print("\n".join(["🔎 文獻核實（refcheck）"] + msgs))
    if not ok:
        raise SystemExit("⛔ 文獻核實未通過 → 不寫入。請修正標題／作者／補強文獻格式，或上網查到後用 "
                         "`python3 refcheck.py manual ...` 登記證據，再重跑。")
    return r

def is_verified(title="", url=""):
    """push_log 用：只看登記簿與 arXiv，回傳 (bool, 說明)。"""
    try:
        r = verify(title=title, url=url)
    except Exception as ex:
        return False, f"核實時出錯：{ex}"
    return r["status"] == "verified", (r.get("problem") or r.get("true_title", ""))


# ---------------- 稽核整份 xlsx ----------------
def audit_xlsx(rows=None, offline=False):
    import openpyxl
    ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True).worksheets[0]
    items = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if rows and not (rows[0] <= i <= rows[1]):
            continue
        row = list(row) + [None] * 13
        t, u, y, au = (row[1] or ""), (row[4] or ""), (row[5] or ""), (row[6] or "")
        if not (t or u):
            continue
        items.append((i, str(t).strip(), str(u).strip(), str(y).strip(), str(au).strip()))
    # 先批次查所有 arXiv 編號（省連線）
    ids = [ids_from(u)[0] for _, _, u, _, _ in items]
    if not offline:
        try:
            got = arxiv_by_ids([x for x in ids if x])
            L = _load_ledger()
            for k, rec in got.items():
                L["entries"]["arxiv:" + k] = {"true_title": rec["title"], "authors": rec["authors"],
                                             "true_year": rec["year"], "arxiv": rec["arxiv"], "source": "arxiv-api",
                                             "evidence": f"https://arxiv.org/abs/{rec['arxiv']}",
                                             "checked_at": datetime.now().isoformat(timespec="seconds")}
            _save_ledger(L)
        except RuntimeError as ex:
            print(f"⚠ {ex}")
    report = []
    for (i, t, u, y, au) in items:
        r = verify(title=t, url=u, authors=au, year=y, offline=offline)
        report.append((i, t, r))
        flag = {"verified": "✅", "mismatch": "⚠️", "not_found": "❌", "unverifiable": "❔"}[r["status"]]
        extra = r.get("problem") or r.get("year_note") or ""
        print(f"{flag} 第{i}列 {t[:60]}｜{r.get('source', '')}" + (f"\n      {extra}" if extra else ""))
    n = {s: sum(1 for _, _, r in report if r["status"] == s) for s in ("verified", "mismatch", "not_found", "unverifiable")}
    print(f"\n合計 {len(report)} 列：✅核實 {n['verified']}　⚠️不符 {n['mismatch']}　❌查無 {n['not_found']}　❔待人工 {n['unverifiable']}")
    return report


def _flags(args):
    out, i, pos = {}, 0, []
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            k = a[2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                out[k] = args[i + 1]; i += 2
            else:
                out[k] = True; i += 1
        else:
            pos.append(a); i += 1
    out["_pos"] = pos
    return out

def main(argv):
    if not argv:
        print(__doc__); return
    cmd, f = argv[0], _flags(argv[1:])
    g = lambda k: f.get(k) if isinstance(f.get(k), str) else ""
    if cmd == "check":
        r = verify(title=g("title"), url=g("url"), authors=g("authors"), year=g("year"))
        print(json.dumps(r, ensure_ascii=False, indent=1))
        sys.exit(0 if r["status"] == "verified" else 5)
    elif cmd == "text":
        with open(f["_pos"][0], encoding="utf-8") as fh:
            ok, lines = check_text(fh.read())
        print("\n".join(lines)); sys.exit(0 if ok else 5)
    elif cmd == "manual":
        manual(g("title") or g("seen-title"), g("seen-title"), g("evidence"), g("authors"), g("year"), g("note"))
    elif cmd == "audit_xlsx":
        rr = None
        if g("rows"):
            a, b = g("rows").split("-"); rr = (int(a), int(b))
        audit_xlsx(rr, offline=bool(f.get("offline")))
    elif cmd == "ledger":
        L = _load_ledger()["entries"]
        for k, v in L.items():
            print(f"{k}\t{v.get('source')}\t{(v.get('true_title') or '')[:70]}")
        print(f"共 {len(L)} 筆")
    else:
        print(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
