#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""營養學獨立實用軌 — 輕量 CLI（不套用 mentor.py 的 KG/深度守門機制）
設計：獨立藍圖(nutrition_roadmap.json) + 每日推播紀錄(nutrition_log.json)。
理論實作各半、每天一則。省 token：LLM 一律透過本 CLI 讀狀態，勿直接 Read 大 JSON。"""
import json, os, sys, argparse, datetime, re

BASE = os.path.dirname(os.path.abspath(__file__))
RM = os.path.join(BASE, "nutrition_roadmap.json")
LOG = os.path.join(BASE, "nutrition_log.json")

def _load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def _save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _today():
    return datetime.date.today().isoformat()

def _cur_week(rm):
    sd = rm.get("meta", {}).get("start_date")
    if not sd:
        return 1
    d0 = datetime.date.fromisoformat(sd)
    return (datetime.date.today() - d0).days // 7 + 1

def _norm(s):
    return re.sub(r"[^0-9a-z一-鿿]+", "", (s or "").lower())

def cmd_brief(a):
    rm = _load(RM, {})
    log = _load(LOG, {"pushes": []})
    wk = _cur_week(rm)
    weeks = rm.get("weeks", {})
    wobj = weeks.get(str(wk))
    meta = rm.get("meta", {})
    print("🥗 營養學獨立軌 · 每日簡報")
    print("=" * 54)
    print(f"  {_today()}  Nutrition Week {wk}")
    print(f"  🎯 一年目標：{meta.get('goal','(未設定)')}")
    # quarter
    q = meta.get("quarters", {})
    for k, v in q.items():
        rng = re.findall(r"W(\d+)-(\d+)", k)
        if rng:
            lo, hi = int(rng[0][0]), int(rng[0][1])
            if lo <= wk <= hi:
                print(f"  📦 本季：{k} — {v}")
    if wobj:
        print(f"  ▸ 本週主題：{wobj.get('theme','')}")
        print(f"     理論：{wobj.get('theory','')}")
        print(f"     實作：{wobj.get('practice','')}")
    else:
        print(f"  ⚠ 第 {wk} 週尚無藍圖 → 請 LLM 依上週結果生成後 roadmap_set --week {wk} 寫回")
    # recent pushes (dedup guard)
    pushes = log.get("pushes", [])
    recent = pushes[-14:]
    if recent:
        print(f"  🚫 近 {len(recent)} 則已推主題（勿重複）：")
        for p in recent:
            print(f"     - {p.get('date','')} [{p.get('kind','')}] {p.get('topic','')}")
    else:
        print("  （尚無推播紀錄，今天是第一則）")
    days = sorted({p.get("date") for p in pushes if p.get("date")})
    print(f"  ✅ 累計推播天數：{len(days)}")
    print("=" * 54)
    print("  流程：①讀本週主題 ②選今日角度(理論+實作各半) ③check_dup 驗重複")
    print("        ④呈現 ⑤log 記錄。頻率：每天一則。")

def cmd_check_dup(a):
    log = _load(LOG, {"pushes": []})
    t = _norm(a.title)
    best = 0.0
    hit = None
    for p in log.get("pushes", []):
        o = _norm(p.get("topic", ""))
        if not o or not t:
            continue
        # 子字串完全包含 → HIT
        if t in o or o in t:
            print(f"🔴 HIT  主題高度重疊\n   撞：{p.get('date','')} {p.get('topic','')}")
            return
        A, B = set(t), set(o)
        j = len(A & B) / len(A | B) if (A | B) else 0
        if j > best:
            best, hit = j, p.get("topic", "")
    if best >= 0.6:
        print(f"🟡 疑似（相似 {best:.2f}）：{hit} — 請人工確認")
    else:
        print(f"🟢 CLEAR  最高相似 {best:.2f} < 0.6，可推")

def cmd_log(a):
    log = _load(LOG, {"pushes": []})
    entry = {"date": a.date or _today(), "topic": a.topic,
             "kind": a.kind, "note": a.note or "", "url": a.url or ""}
    log.setdefault("pushes", []).append(entry)
    _save(LOG, log)
    print(f"✅ 已記錄：{entry['date']} [{entry['kind']}] {entry['topic']}")

def cmd_roadmap_set(a):
    rm = _load(RM, {"meta": {}, "weeks": {}})
    rm.setdefault("weeks", {})[str(a.week)] = {
        "theme": a.theme, "theory": a.theory, "practice": a.practice}
    _save(RM, rm)
    print(f"✅ roadmap_set week {a.week}：{a.theme}")

def cmd_show(a):
    rm = _load(RM, {})
    meta = rm.get("meta", {})
    print(f"🎯 目標：{meta.get('goal','')}")
    for k, v in meta.get("quarters", {}).items():
        print(f"  {k}: {v}")
    print("── 已排週次 ──")
    for w in sorted(rm.get("weeks", {}), key=lambda x: int(x)):
        wo = rm["weeks"][w]
        print(f"  W{w}: {wo.get('theme','')}")

def cmd_streak(a):
    log = _load(LOG, {"pushes": []})
    days = sorted({p.get("date") for p in log.get("pushes", []) if p.get("date")})
    if not days:
        print("尚無紀錄。開始第一天吧，習慣 > 完美 ✓")
        return
    # 目前連續天數
    dset = set(days)
    cur = 0
    d = datetime.date.today()
    while d.isoformat() in dset:
        cur += 1
        d -= datetime.timedelta(days=1)
    print(f"營養學軌：總推播 {len(days)} 天；目前連續 {cur} 天；最近一次 {days[-1]}")

def main():
    p = argparse.ArgumentParser(prog="nutrition.py")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("brief").set_defaults(fn=cmd_brief)
    c = sub.add_parser("check_dup"); c.add_argument("--title", required=True); c.set_defaults(fn=cmd_check_dup)
    c = sub.add_parser("log")
    c.add_argument("--topic", required=True); c.add_argument("--kind", default="both", choices=["theory","practice","both"])
    c.add_argument("--note", default=""); c.add_argument("--url", default=""); c.add_argument("--date", default="")
    c.set_defaults(fn=cmd_log)
    c = sub.add_parser("roadmap_set")
    for k in ("week","theme","theory","practice"):
        c.add_argument("--"+k, required=True)
    c.set_defaults(fn=cmd_roadmap_set)
    sub.add_parser("show").set_defaults(fn=cmd_show)
    sub.add_parser("streak").set_defaults(fn=cmd_streak)
    a = p.parse_args()
    if not getattr(a, "fn", None):
        p.print_help(); return
    a.fn(a)

if __name__ == "__main__":
    main()
# EOF-SENTINEL: nutrition.py 完整結尾
