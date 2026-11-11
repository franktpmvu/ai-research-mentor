# -*- coding: utf-8 -*-
"""paper-rag-mcp 資料更新流程（可重複執行；只處理有變動的部分）

用法：
  1. 新資料丟進 input_raw/inbox/（PDF、zip、資料夾都可以）
  2. python update.py            → 跑完整流程
     python update.py --dry-run  → 只顯示會做什麼，不動任何檔案
     python update.py --rebuild  → 解析與索引全部重做
     python update.py --minutes 2 → 解析最多跑 2 分鐘就先停（沒做完的下次接著做）
     python update.py --workers 2 → 同時解析 2 份（每份約需 0.7 GB 記憶體）
     python update.py --doc-timeout 90 → 單份超過 90 秒就跳過（預設 300），記成 TIMEOUT
     python update.py --retry-failed   → 重試先前失敗（ERR）或逾時（TIMEOUT）的文件

流程：
  ① 收件  inbox/ → batches/YYMMDD_名稱/（zip 原檔保留在 _original/，旁邊解壓）
  ② 盤點  掃 batches/ 與 corpus/*_refs/pdf/ → 算 hash，寫進 registry.csv（沒變的檔案不重算）
  ③ 去重  同檔案（hash）、同 arXiv、同 DOI 歸成一組，每組選一份 canonical 來索引
  ④ 補洞  corpus 裡缺 PDF 的參考文獻，若在新資料中找到 → 複製過去並更新筆記
  ⑤ 解析  只解析「新的」或「解析器版本不同」的 canonical 文件
  ⑥ 索引  新解析的文件寫進 SQLite FTS5 全文索引；已移除的文件從索引刪掉
  ⑦ 發布  寫 index_version.json（MCP server 看到版本變了就重新載入）＋ update_log.md

原則：原始資料只搬不改（inbox → batches 是移動，不刪不改內容）；所有衍生資料在 data/derived/，可整個刪掉重建。
需要：Python 3.11+、pymupdf4llm（requirements.txt）；有 poppler 會優先用來盤點，沒有也可以
"""
import os, re, csv, sys, json, shutil, zipfile, hashlib, subprocess, difflib, datetime, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, 'input_raw')
INBOX = os.path.join(RAW, 'inbox')
BATCHES = os.path.join(RAW, 'batches')
CORPUS = os.path.join(ROOT, 'corpus')
DER = os.path.join(ROOT, 'data', 'derived')
REG = os.path.join(DER, 'registry.csv')

# 管線版本：改了任何一個，對應的步驟就會對所有文件重做
sys.path.insert(0, os.path.join(ROOT, 'src'))
from paper_kb.ingest.pdf import PARSER_VERSION       # noqa: E402
from paper_kb.index import INDEX_VERSION             # noqa: E402
VERSIONS = {
    'parser': PARSER_VERSION,   # 改了 → 全部重新解析（也會重新索引）
    'index': INDEX_VERSION,     # 改了 → 全部重新索引（不用重新解析）
}
PARSED = os.path.join(DER, 'parsed')

DRY = '--dry-run' in sys.argv
REBUILD = '--rebuild' in sys.argv
MINUTES = float(sys.argv[sys.argv.index('--minutes') + 1]) if '--minutes' in sys.argv else None
WORKERS = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 1
DOC_TIMEOUT = float(sys.argv[sys.argv.index('--doc-timeout') + 1]) if '--doc-timeout' in sys.argv else 300
RETRY = '--retry-failed' in sys.argv
TODAY = datetime.date.today().strftime('%y%m%d')
log = []

def say(msg):
    print(msg); log.append(msg)

def pdf_meta(p):
    """(頁數, metadata 標題, 前 2 頁文字)。有 poppler 就用 poppler（結果和第一次盤點一致），沒有就用 pymupdf。"""
    if shutil.which('pdfinfo') and shutil.which('pdftotext'):
        info = sh('pdfinfo', p)
        pages = (re.search(r'Pages:\s+(\d+)', info) or [0, ''])[1]
        mt = (re.search(r'Title:[ \t]+(.*)', info) or [0, ''])[1].strip()
        return pages, mt, sh('pdftotext', '-l', '2', p, '-')
    try:
        import pymupdf
        with pymupdf.open(p) as d:
            return str(d.page_count), (d.metadata or {}).get('title') or '', \
                '\n'.join(d[i].get_text() for i in range(min(2, d.page_count)))
    except Exception:
        return '', '', ''

def sh(*a):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''

def norm(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())

# ---------------- ⓪ 下載佇列 ----------------
QUEUE = os.path.join(RAW, 'url_queue.txt')

def _pdf_url(u):
    """arXiv 的 abs/html 連結轉成 pdf 連結；其他網址原樣（需本身就是 PDF）"""
    m = re.search(r'arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})(v\d+)?', u)
    if m:
        return f'https://arxiv.org/pdf/{m.group(1)}{m.group(2) or ""}', m.group(1)
    return u, re.sub(r'[^A-Za-z0-9._-]', '_', u.rstrip('/').split('/')[-1])[:60] or 'download'

def fetch_queue():
    """input_raw/url_queue.txt 每行一個網址（導師系統讀完論文時自動加入）。
    下載成功 → 放進 inbox/、從佇列移除；失敗 → 留在佇列，下次再試。沒有佇列檔就跳過。"""
    if not os.path.exists(QUEUE):
        return
    lines = [l.strip() for l in open(QUEUE, encoding='utf-8') if l.strip() and not l.startswith('#')]
    if not lines:
        return
    import urllib.request
    os.makedirs(INBOX, exist_ok=True)
    keep = []
    for line in lines:
        url = line.split()[0]
        pdf, name = _pdf_url(url)
        dst = os.path.join(INBOX, name if name.lower().endswith('.pdf') else name + '.pdf')
        if DRY:
            say(f'⓪ 下載佇列：會下載 {pdf}'); keep.append(line); continue
        try:
            req = urllib.request.Request(pdf, headers={'User-Agent': 'paper-kb/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if not data.startswith(b'%PDF'):
                raise ValueError('下載到的不是 PDF')
            with open(dst, 'wb') as f:
                f.write(data)
            say(f'⓪ 下載佇列：{pdf} → inbox/{os.path.basename(dst)}')
        except Exception as e:
            say(f'⓪ 下載佇列：{pdf} 失敗（{e}），留在佇列下次再試')
            keep.append(line)
    if not DRY:
        with open(QUEUE, 'w', encoding='utf-8') as f:
            f.write(''.join(l + '\n' for l in keep))

# ---------------- ① 收件 ----------------
def intake():
    os.makedirs(INBOX, exist_ok=True); os.makedirs(BATCHES, exist_ok=True)
    items = [x for x in sorted(os.listdir(INBOX)) if not x.startswith('.')]
    if not items:
        say('① 收件：inbox 是空的'); return
    for x in items:
        src = os.path.join(INBOX, x)
        stem = re.sub(r'\.(zip|pdf)$', '', x, flags=re.I)
        dst = os.path.join(BATCHES, f'{TODAY}_{stem}')
        i = 2
        while os.path.exists(dst):
            dst = os.path.join(BATCHES, f'{TODAY}_{stem}_{i}'); i += 1
        say(f'① 收件：{x} → batches/{os.path.basename(dst)}/')
        if DRY: continue
        os.makedirs(dst)
        if x.lower().endswith('.zip'):
            os.makedirs(os.path.join(dst, '_original'))
            shutil.move(src, os.path.join(dst, '_original', x))
            with zipfile.ZipFile(os.path.join(dst, '_original', x)) as z:
                z.extractall(dst)
        else:
            shutil.move(src, os.path.join(dst, x))

# ---------------- ② 盤點 ----------------
FIELDS = ['doc_id', 'path', 'source', 'mine', 'sha256', 'size', 'mtime', 'pages', 'title_guess', 'arxiv', 'doi',
          'head', 'group', 'canonical', 'role', 'parsed_ver', 'indexed_ver', 'added', 'status']

def load_registry():
    if not os.path.exists(REG):
        return {}
    return {r['path']: r for r in csv.DictReader(open(REG, encoding='utf-8-sig'))}

def scan(old):
    found = {}
    roots = [('collection', BATCHES)] + [('corpus', os.path.join(CORPUS, d, 'pdf'))
                                         for d in (sorted(os.listdir(CORPUS)) if os.path.isdir(CORPUS) else [])]
    for src, base in roots:
        if not os.path.isdir(base): continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d != '_original' and not d.startswith('__MACOSX')]
            for f in fn:
                if not f.lower().endswith('.pdf'): continue
                p = os.path.join(dp, f); rel = os.path.relpath(p, ROOT).replace('\\', '/')
                st = os.stat(p)
                o = old.get(rel)
                if o and o['size'] == str(st.st_size) and o['mtime'] == str(int(st.st_mtime)):
                    found[rel] = dict(o); found[rel]['status'] = 'unchanged'; continue
                h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
                pages, mt, txt = pdf_meta(p)
                head = ' '.join(l.strip() for l in txt.splitlines() if l.strip())[:600]
                ax = re.search(r'(\d{4}\.\d{4,5})', f) or re.search(r'arXiv:(\d{4}\.\d{4,5})', txt)
                doi = re.search(r'(10\.\d{4,9}/[^\s"<>]+)', txt)
                found[rel] = dict(doc_id=h[:12], path=rel, source=src, mine=str('/_mine/' in rel),
                                  sha256=h, size=str(st.st_size), mtime=str(int(st.st_mtime)), pages=pages,
                                  title_guess=mt if len(mt) > 15 and not mt.lower().endswith(('.pdf', '.dvi', '.doc')) else '',
                                  arxiv=ax.group(1) if ax else '', doi=doi.group(1).rstrip('.,;') if doi else '',
                                  head=head, group='', canonical='', role='', parsed_ver=(o or {}).get('parsed_ver', ''),
                                  indexed_ver=(o or {}).get('indexed_ver', ''),
                                  added=(o or {}).get('added', TODAY), status='changed' if o else 'new')
    removed = [p for p in old if p not in found]
    return found, removed

# ---------------- ③ 去重 ----------------
def group(reg):
    parent = {}
    def f(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def u(a, b): parent[f(a)] = f(b)
    keys = collections.defaultdict(list)
    for p, r in reg.items():
        f(p)
        keys['h:' + r['sha256']].append(p)
        if r['arxiv']: keys['a:' + r['arxiv']].append(p)
        if r['doi']: keys['d:' + r['doi'].lower()].append(p)
    for ps in keys.values():
        for q in ps[1:]: u(ps[0], q)
    groups = collections.defaultdict(list)
    for p in reg: groups[f(p)].append(p)
    for g, ps in groups.items():
        gid = reg[sorted(ps)[0]]['doc_id']
        # canonical：優先你自己的論文（_mine），其次 corpus 裡的（已有筆記），再其次頁數多的
        best = sorted(ps, key=lambda p: ('/_mine/' not in p, reg[p]['source'] != 'corpus',
                                         -int(reg[p]['pages'] or 0), len(p)))[0]
        mine = any('/_mine/' in p for p in ps)   # 同一篇只要有一份在 _mine，整組都算你的論文
        for p in ps:
            reg[p]['group'] = gid; reg[p]['canonical'] = str(p == best); reg[p]['mine'] = str(mine)
    return groups

# ---------------- ④ 補洞 ----------------
def fill_corpus(reg):
    if not os.path.isdir(CORPUS): return 0
    cands = [r for r in reg.values() if r['source'] == 'collection' and r['canonical'] == 'True' and r['mine'] == 'False']
    n = 0
    for d in sorted(os.listdir(CORPUS)):
        folder = os.path.join(CORPUS, d)
        if not d.endswith('_refs') or not os.path.isdir(folder): continue
        for md in sorted(os.listdir(folder)):
            if not md.endswith('.md') or md == 'README.md': continue
            mp = os.path.join(folder, md); s = open(mp, encoding='utf-8').read()
            m = re.search(r'\| PDF \| (.*?) \|', s)
            if not m or '已下載' in m.group(1) or '來自你的收藏' in m.group(1) or '你自己的論文' in m.group(1): continue
            title = s.splitlines()[0][2:]; title = title.split('：', 1)[1] if '：' in title else title
            nt = norm(title)
            if len(nt) < 15: continue
            hit = None
            for r in cands:
                hay = norm(r['title_guess'] + ' ' + r['head'][:400])
                k = hay.find(nt[:60])
                if k < 0: continue
                # 防誤配：標題後面緊接的若還是長串標題文字（例如 ...via SIFT），且 metadata 標題明顯更長，就跳過
                if r['title_guess'] and len(norm(r['title_guess'])) > len(nt) + 12: continue
                hit = r; break
            if not hit: continue
            name = md[:-3] + '.pdf'; dst = os.path.join(folder, 'pdf', name)
            say(f'④ 補洞：{d}/{md} ← {hit["path"]}')
            n += 1
            if DRY: continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst): shutil.copy2(os.path.join(ROOT, hit['path']), dst)
            s = re.sub(r'\| PDF \| .*? \|', f'| PDF | pdf/{name}（✅ 來自你的收藏 {hit["path"]}） |', s, count=1)
            open(mp, 'w', encoding='utf-8').write(s)
            hit['role'] = (hit['role'] + ';' if hit['role'] else '') + f'fills:{d}/{md}'
    return n

# ---------------- ⑤⑥ 解析與索引 ----------------
def _parse_one(path, doc_id, outdir, q):
    """在子行程裡跑；結果放進 q：('ok', (頁數, 段數, 標題)) 或 ('err', 訊息)"""
    try:
        sys.path.insert(0, os.path.join(ROOT, 'src'))
        from paper_kb.ingest.pdf import parse_pdf
        d = parse_pdf(path, doc_id)
        tmp = os.path.join(outdir, doc_id + '.json.tmp')
        with open(tmp, 'w', encoding='utf-8') as fo:
            json.dump(d, fo, ensure_ascii=False)
        os.replace(tmp, os.path.join(outdir, doc_id + '.json'))
        q.put(('ok', (d['pages'], d['stats']['n_blocks'], d.get('title', ''))))
    except Exception as e:
        q.put(('err', f'{type(e).__name__}: {e}'))


def parse_and_index(reg, removed):
    import time
    from paper_kb import index
    t0 = time.time()
    canon = [r for r in reg.values() if r['canonical'] == 'True']
    def parsed_ok(r):
        # 解析結果檔開頭記有解析器版本：上次中途被中止、清單沒寫到也認得，不用重做
        f = os.path.join(PARSED, r['doc_id'] + '.json')
        if not os.path.exists(f):
            return False
        if r['parsed_ver'] == VERSIONS['parser']:
            return True
        with open(f, encoding='utf-8') as fh:
            m = re.search(r'"parser":\s*"([^"]*)"', fh.read(300))
        if m and m.group(1) == VERSIONS['parser']:
            r['parsed_ver'] = VERSIONS['parser']; r['indexed_ver'] = ''
            return True
        return False
    need_parse = [r for r in canon if REBUILD or not parsed_ok(r)]
    say(f'⑤ 解析：待解析 {len(need_parse)} 份（共 {len(canon)} 份 canonical）')
    if DRY:
        return False
    os.makedirs(PARSED, exist_ok=True)
    done = err = 0
    # 每份文件一個子行程；超過 DOC_TIMEOUT 秒就中止並記成 TIMEOUT（之後加 --retry-failed 才會再試）
    import multiprocessing as mp
    ctx = mp.get_context('spawn')
    todo = [r for r in need_parse if RETRY or r['parsed_ver'] not in ('ERR', 'TIMEOUT')]
    skipped = len(need_parse) - len(todo)
    if skipped:
        say(f'   跳過先前失敗或逾時的 {skipped} 份（要重試加 --retry-failed）')
    running = []   # (process, queue, row, start)
    while todo or running:
        while todo and len(running) < WORKERS and not (MINUTES and time.time() - t0 > MINUTES * 60):
            r = todo.pop(0)
            q = ctx.Queue()
            pr = ctx.Process(target=_parse_one, args=(os.path.join(ROOT, r['path']), r['doc_id'], PARSED, q), daemon=True)
            pr.start(); running.append((pr, q, r, time.time()))
        if not running:
            break
        time.sleep(0.2)
        for item in list(running):
            pr, q, r, st = item
            if pr.is_alive() and time.time() - st < DOC_TIMEOUT:
                continue
            if pr.is_alive():
                pr.kill(); pr.join()
                r['parsed_ver'] = 'TIMEOUT'; err += 1
                say(f'   逾時（>{DOC_TIMEOUT}s）跳過：{r["path"]}')
            else:
                res = q.get() if not q.empty() else ('err', f'exit code {pr.exitcode}')
                if res[0] == 'ok':
                    pages, nb, title = res[1]
                    r['parsed_ver'] = VERSIONS['parser']; r['indexed_ver'] = ''   # 重新解析 → 也要重新索引
                    if not r['title_guess'] and len(title) > 15:
                        r['title_guess'] = title[:200]
                    done += 1
                    print(f'   [{done}/{len(need_parse)}] {r["doc_id"]} {pages}p {nb} 段 {time.time() - st:.0f}s  {r["path"][-55:]}', flush=True)
                else:
                    r['parsed_ver'] = 'ERR'; err += 1
                    say(f'   解析失敗：{r["path"]}（{res[1][:120]}）')
            running.remove(item)
    if todo:
        say(f'   時間到，先停；剩 {len(todo)} 份下次再解析')
    say(f'   解析完成 {done} 份、失敗 {err} 份')

    # ⑥ 索引：已解析但索引版本不符的 → 寫進 FTS5；不是 canonical 或已移除的 → 從索引刪掉
    db = index.connect(os.path.join(DER, 'index', 'papers.db'))
    keep = {r['doc_id'] for r in canon}
    stale = [x for x in index.doc_ids(db) if x not in keep]
    for x in stale:
        index.delete(db, x)
    n = 0
    for r in canon:
        if r['parsed_ver'] != VERSIONS['parser']:
            continue
        if REBUILD or r['indexed_ver'] != VERSIONS['index'] or r['doc_id'] not in index.doc_ids(db, cached=True):
            d = json.load(open(os.path.join(PARSED, r['doc_id'] + '.json'), encoding='utf-8'))
            ft = ''
            if index.bad_title(r['title_guess']) and index.bad_title(d.get('title')):
                ft = index.font_title(os.path.join(ROOT, r['path']))
            index.upsert(db, r, d, ft); r['indexed_ver'] = VERSIONS['index']; n += 1
    from paper_kb import citations
    nc = citations.build(db, CORPUS, reg)
    for did, (ag, wn, use) in getattr(citations.build, 'report', {}).items():
        if not use:
            say(f'   引用句：{did} 全文編號和筆記只吻合 {ag}/{wn}（PDF 可能是另一個版本）→ 保留筆記句子')
    db.commit()
    say(f'⑥ 索引：寫入 {n} 份、刪除 {len(stale)} 份；索引內共 {len(index.doc_ids(db))} 份；引用關係 {nc} 筆')
    db.close()
    return bool(done or n or stale)

# ---------------- ⑦ 發布 ----------------
def publish(reg, removed, filled, changed_index):
    os.makedirs(DER, exist_ok=True)
    rows = sorted(reg.values(), key=lambda r: r['path'])
    new = sum(1 for r in rows if r['status'] in ('new', 'changed'))
    canon = sum(1 for r in rows if r['canonical'] == 'True')
    say(f'② 盤點：共 {len(rows)} 個 PDF（新增或變動 {new}、移除 {len(removed)}）')
    say(f'③ 去重：{canon} 份 canonical（重複的 {len(rows) - canon} 份不索引）')
    say(f'④ 補洞：corpus 補上 {filled} 篇')
    if DRY:
        say('（dry-run：沒有寫入任何檔案）'); return
    with open(REG, 'w', newline='', encoding='utf-8-sig') as fo:
        w = csv.DictWriter(fo, fieldnames=FIELDS); w.writeheader()
        for r in rows: w.writerow({k: r.get(k, '') for k in FIELDS})
    vfile = os.path.join(DER, 'index_version.json')
    v = json.load(open(vfile)) if os.path.exists(vfile) else {'version': 0}
    if new or removed or filled or changed_index:
        v.update(version=v['version'] + 1, updated_at=datetime.datetime.now().isoformat(timespec='seconds'),
                 n_pdf=len(rows), n_canonical=canon, pipeline=VERSIONS)
        json.dump(v, open(vfile, 'w'), indent=1)
    with open(os.path.join(DER, 'update_log.md'), 'a', encoding='utf-8') as fo:
        fo.write(f"\n## {datetime.datetime.now():%Y-%m-%d %H:%M}（index_version {v['version']}）\n" + '\n'.join('- ' + l for l in log) + '\n')

if __name__ == '__main__':
    old = load_registry()
    fetch_queue()
    intake()
    reg, removed = scan(old)
    group(reg)
    filled = fill_corpus(reg)
    changed = parse_and_index(reg, removed)
    publish(reg, removed, filled, changed)
