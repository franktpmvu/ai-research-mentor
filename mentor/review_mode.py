#!/usr/bin/env python3
"""
複習模式 review_mode — 以「概念」為單位複習與了解學習者（KYC）。

知識本身要有語意：複習考的是概念（例如「一對一匹配為何免 NMS」），
論文只是概念的證據來源。狀態存兩個小檔：
  concepts.json  概念節點：語意名稱、來源論文、先修概念、作答歷史
  kyc.json       學習者畫像觀察：思考模式、興趣訊號（含「三篇都不喜歡」）

指令（經 mentor.py 分派：python3 mentor.py review_mode <子指令> ...）：
  pick [--n 5]                         選題候選（只給導師看）
  concept_add --name ".." --sources "pid||pid" [--domain D] [--prereqs "cid||cid"] [--id cid]
  concept_link --id cid --prereqs "cid||cid"
  concept_log --id cid --result pass|fail --depth 0-4 --how asked|followup|mentioned [--note ..] [--blindspots "a||b"] [--no_recall]
                                       記一次概念作答；同時對主要來源論文跑 recall（沿用間隔與技能地圖）
  concepts [--domain D]                概念清單
  kyc_add --kind pattern|interest --text ".." [--evidence ".."] [--sign +|-]
  kyc_show                             畫像觀察；同一模式證據 ≥3 → 標「可寫入 profile.md」
"""
import json, os, re, sys
from datetime import date, datetime

import mentor as M

BASE = M.BASE
CONCEPTS_FILE = os.path.join(BASE, "concepts.json")
KYC_FILE = os.path.join(BASE, "kyc.json")
PROMOTE_AT = 3

def _load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _today():
    return str(date.today())

def _concepts():
    return _load(CONCEPTS_FILE, {"meta": {"created": _today(), "schema": "concept-nodes"}, "concepts": {}})

def _kyc():
    return _load(KYC_FILE, {"meta": {"created": _today(), "schema": "learner-kyc"}, "observations": []})

def _slug(name):
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name.lower()).strip("_")
    return ("c_" + s[:40]) if s else "c_" + datetime.now().strftime("%H%M%S")

# ── 選題 ────────────────────────────────────
def _today_push_pids():
    try:
        log = _load(os.path.join(BASE, "push_log.json"), [])
        return [p["pid"] for e in log if e.get("date") == _today() for p in e.get("papers", [])]
    except Exception:
        return []

def _kg_ancestors(pids, max_d=3):
    nodes = M._load_kg().get("nodes", {})
    anc = {}
    for root in pids:
        frontier = [(root, 0)]
        while frontier:
            cur, d = frontier.pop(0)
            if d >= max_d:
                continue
            for p in nodes.get(cur, {}).get("prereqs", []) or []:
                if p not in anc or anc[p][1] > d + 1:
                    anc[p] = (root, d + 1)
                frontier.append((p, d + 1))
    return anc

def _recent_domains(cs, days=14):
    cnt = {}
    for c in cs["concepts"].values():
        for h in c.get("history", []):
            try:
                if (date.today() - datetime.strptime(h["date"], "%Y-%m-%d").date()).days <= days:
                    cnt[c.get("domain", "?")] = cnt.get(c.get("domain", "?"), 0) + 1
            except Exception:
                pass
    return cnt

GAP_WORDS = ("缺口", "盲區", "未觸及", "未複述", "待補", "誤", "待 recall", "待recall", "未探討")

def pick(flags):
    n = int(flags.get("n", 5)) if flags.get("n") not in (None, True) else 5
    rows = M._recall_due_list(include_future=True)
    cs = _concepts()
    by_src = {}
    for cid, c in cs["concepts"].items():
        for s in c.get("sources", []):
            by_src.setdefault(s, []).append(cid)
    today_pids = _today_push_pids()
    anc = _kg_ancestors(today_pids)
    dom_cnt = _recent_domains(cs)
    by = M._pid_records(M._all_episodes())
    scored = []
    for r in rows:
        pid = r["pid"]
        recs = by.get(pid, {}).get("recs", [])
        if any(q.get("date") == _today() for q in recs):
            continue                               # 今天已討論過，不再考
        never = not any(q.get("judge") == "recall" for q in recs)
        overdue = max(0, r["overdue"])
        s, why = 0.0, []
        if r["overdue"] >= 0:
            s += 3 + min(overdue, 120) / 30; why.append(f"逾期{overdue}天")
        if never and overdue >= 30:
            s += 3; why.append("通過後從沒複習過（測長期記憶）")
        note = r.get("last_note", "")
        blind = next((q.get("blindspots") for q in reversed(recs) if q.get("blindspots")), [])
        if blind or any(w in note for w in GAP_WORDS):
            s += 2; why.append("上次留有缺口")
        if pid in anc:
            s += 2; why.append(f"是今日推播 {anc[pid][0]} 的先修(距{anc[pid][1]})")
        d = r.get("domain") or "?"
        s += max(0, 2 - dom_cnt.get(d, 0)); 
        scored.append((s, r, why, blind))
    scored.sort(key=lambda x: -x[0])
    # 領域分散：前 n 名中同領域最多 2 個
    out, per = [], {}
    for item in scored:
        d = item[1].get("domain") or "?"
        if per.get(d, 0) >= 2:
            continue
        per[d] = per.get(d, 0) + 1; out.append(item)
        if len(out) >= n:
            break
    print("\n🧠 複習選題候選（只給導師看；考的是概念，不是論文名）")
    print("─" * 60)
    if not out:
        print("  沒有可複習的已通過概念。"); print("─" * 60); return []
    for s, r, why, blind in out:
        pid = r["pid"]
        dom, title, rub, _qs, _src = M._lookup_paper(pid)
        print(f"  ▸ [{r.get('domain')}] {pid}  score {s:.1f}  — {'、'.join(why) or '到期'}")
        print(f"    來源：{(title or pid)[:66]}")
        if by_src.get(pid):
            for cid in by_src[pid]:
                c = cs["concepts"][cid]
                last = c.get("history", [{}])[-1] if c.get("history") else {}
                print(f"    已有概念 {cid}：{c['name'][:60]}" + (f"（上次 {last.get('date')} {last.get('result')} d{last.get('depth')}）" if last else ""))
        if rub:
            for i, x in enumerate(rub[:3], 1):
                print(f"    rubric{i}：{str(x)[:80]}")
        if blind:
            print(f"    舊盲區：{blind[:3]}")
        if r.get("last_note"):
            print(f"    上次評語（別洩漏）：{r['last_note'][:80]}")
    print("─" * 60)
    print("  做法：從 rubric 抽出一個『概念』（語意句，不是論文名）→ 沒有就 concept_add →")
    print("  換情境/反事實/比較/找破綻出 1 題 → 追問 → concept_log 記錄 → 觀察到思考模式就 kyc_add。")
    return out

# ── 概念節點 ────────────────────────────────
def concept_add(flags):
    name = flags.get("name")
    if not isinstance(name, str) or not name.strip():
        print('用法: concept_add --name "語意描述" --sources "pid||pid" [--domain D] [--prereqs "cid||cid"] [--id cid]'); return
    cs = _concepts()
    cid = flags.get("id") if isinstance(flags.get("id"), str) else _slug(name)
    if cid in cs["concepts"]:
        print(f"  ⚠ {cid} 已存在：{cs['concepts'][cid]['name']}"); return
    sources = M._split_multi(flags.get("sources", "")) if isinstance(flags.get("sources"), str) else []
    domain = flags.get("domain") if isinstance(flags.get("domain"), str) else None
    if not domain and sources:
        domain = M._lookup_paper(sources[0])[0]
    prereqs = M._split_multi(flags.get("prereqs", "")) if isinstance(flags.get("prereqs"), str) else []
    missing = [p for p in prereqs if p not in cs["concepts"]]
    if missing:
        print(f"  ⚠ 先修概念不存在（仍會記下，之後補建）：{missing}")
    cs["concepts"][cid] = {"name": name.strip(), "domain": domain or "cross", "sources": sources,
                           "prereqs": prereqs, "added": _today(), "history": []}
    _save(CONCEPTS_FILE, cs)
    print(f"  ✅ 新增概念 {cid}：{name.strip()}  來源 {sources}")

def concept_link(flags):
    cid = flags.get("id"); cs = _concepts()
    if cid not in cs["concepts"]:
        print(f"  ⚠ 找不到概念 {cid}"); return
    pr = M._split_multi(flags.get("prereqs", "")) if isinstance(flags.get("prereqs"), str) else []
    c = cs["concepts"][cid]
    c["prereqs"] = list(dict.fromkeys(c.get("prereqs", []) + pr))
    _save(CONCEPTS_FILE, cs)
    print(f"  🔗 {cid} 先修 → {c['prereqs']}")

def concept_log(flags):
    cid = flags.get("id"); result = flags.get("result")
    cs = _concepts()
    if cid not in cs["concepts"] or result not in ("pass", "fail"):
        print('用法: concept_log --id cid --result pass|fail --depth N --how asked|followup|mentioned [--note ..] [--blindspots "a||b"]'); return
    c = cs["concepts"][cid]
    depth = int(flags.get("depth", 2 if result == "pass" else 1))
    how = flags.get("how") if flags.get("how") in ("mentioned", "asked", "followup") else "asked"
    note = flags.get("note", "") if isinstance(flags.get("note"), str) else ""
    blind = M._split_multi(flags.get("blindspots", "")) if isinstance(flags.get("blindspots"), str) else []
    c.setdefault("history", []).append({"date": _today(), "result": "passed" if result == "pass" and depth >= 2 else "failed",
                                        "depth": depth, "how": how, "note": note[:300], "blindspots": blind})
    _save(CONCEPTS_FILE, cs)
    print(f"  📝 概念作答已記：{c['name'][:50]} → {result} d{depth}（{how}）")
    if flags.get("no_recall"):
        return                                    # 已另外用 recall 記過這次作答時，避免重複計分
    if c.get("sources"):
        f2 = {"paper": c["sources"][0], "result": result, "depth": str(depth), "how": how,
              "note": f"[概念 {cid}] {note}"[:300]}
        if blind:
            f2["blindspots"] = "||".join(blind)
        M.recall(f2)

def concepts(flags):
    cs = _concepts(); dom = flags.get("domain")
    print("\n🧩 概念節點")
    print("─" * 60)
    for cid, c in sorted(cs["concepts"].items(), key=lambda kv: kv[1].get("domain", "")):
        if isinstance(dom, str) and c.get("domain") != dom:
            continue
        h = c.get("history", [])
        last = f"{h[-1]['date']} {h[-1]['result']} d{h[-1]['depth']}" if h else "未考"
        print(f"  [{c.get('domain')}] {cid}：{c['name'][:56]}")
        print(f"     來源 {c.get('sources')}  先修 {c.get('prereqs') or '—'}  最近 {last}  共{len(h)}次")
    print("─" * 60)

# ── KYC ─────────────────────────────────────
def kyc_add(flags):
    kind = flags.get("kind"); text = flags.get("text")
    if kind not in ("pattern", "interest") or not isinstance(text, str):
        print('用法: kyc_add --kind pattern|interest --text ".." [--evidence ".."] [--sign +|-]'); return
    k = _kyc()
    k["observations"].append({"date": _today(), "kind": kind, "text": text.strip(),
                              "evidence": flags.get("evidence", "") if isinstance(flags.get("evidence"), str) else "",
                              "sign": flags.get("sign") if flags.get("sign") in ("+", "-") else ""})
    _save(KYC_FILE, k)
    print(f"  👁 KYC 觀察已記（{kind}）：{text.strip()[:60]}")

def kyc_show(flags):
    k = _kyc()
    groups = {}
    for o in k["observations"]:
        groups.setdefault((o["kind"], o["text"]), []).append(o)
    print("\n👁 學習者畫像觀察（KYC）")
    print("─" * 60)
    if not groups:
        print("  尚無觀察。")
    for (kind, text), obs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        tag = "  ⬆ 可寫入 profile.md" if kind == "pattern" and len(obs) >= PROMOTE_AT else ""
        print(f"  [{kind}] ×{len(obs)}  {text[:60]}{tag}")
        print(f"     證據：{'；'.join((o['date'] + ' ' + o['evidence'])[:40] for o in obs[-3:])}")
    print("─" * 60)
    print(f"  同一 pattern 用同一句 text 累積；×{PROMOTE_AT} 以上才升級寫進 profile.md 的『常見模式』。")

CMDS = {"pick": pick, "concept_add": concept_add, "concept_link": concept_link, "concept_log": concept_log,
        "concepts": concepts, "kyc_add": kyc_add, "kyc_show": kyc_show}

def main(argv):
    if not argv or argv[0] not in CMDS:
        print(__doc__); return
    CMDS[argv[0]](M._parse_flags(argv[1:]))

if __name__ == "__main__":
    main(sys.argv[1:])
