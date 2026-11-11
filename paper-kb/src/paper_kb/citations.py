# -*- coding: utf-8 -*-
"""引用關係：從 corpus/*_refs/*.md 筆記抽出「你的論文 → 參考文獻」與引用原句

寫進 papers.db 的 cites 表（每次 update.py 都整張重建，很快）：
  citing_doc   你的論文的 doc_id（找不到 PDF 時為空）
  citing       你的論文名稱（筆記「來源」欄）
  ref_no       參考文獻編號
  paper_id     筆記編號，例如 nt02_siamfc
  cited_doc    被引論文的 doc_id（沒有 PDF 時為空）
  title, year, venue, url, role
  contexts     引用原句（多句以換行分隔）。優先從你論文的全文自動抓：句子裡出現 [n]、[5,6,29]、[3-5] 就算引用第 n 篇；
               全文抓不到（沒有全文、或編號對不上）才用筆記裡人工整理的句子
  ctx_paras    每句引用原句所在的 para_id（和 contexts 同順序；用筆記句子時為空）
  ctx_source   fulltext 或 note
  note         你在筆記「note（我的回覆）」寫的內容（空的就是空）
「question（導師提問）」不收錄。
"""
import os
import re

# 參考文獻資料夾 → 你的論文 PDF 檔名（registry 的 path 包含這些字串即可）
# 個人設定放在專案根目錄的 config.json（不上傳 GitHub）；沒有這個檔就是空的，系統照常運作。
def _load_mine():
    import json
    root = os.environ.get('PAPER_KB_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, 'config.json')
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get('mine', {}) or {}
    except FileNotFoundError:
        return {}


MINE = _load_mine()

SCHEMA = """
DROP TABLE IF EXISTS cites;
CREATE TABLE cites(citing_doc TEXT, citing TEXT, ref_no TEXT, paper_id TEXT, cited_doc TEXT,
  title TEXT, year TEXT, venue TEXT, url TEXT, role TEXT, contexts TEXT, note TEXT, refs_dir TEXT,
  ctx_paras TEXT DEFAULT '', ctx_source TEXT DEFAULT 'note');
"""


def _sections(md):
    out, cur = {}, None
    for ln in md.splitlines():
        if ln.startswith('## '):
            cur = ln[3:].strip(); out[cur] = []
        elif cur:
            out[cur].append(ln)
    return out


def _fields(md):
    f = {}
    for m in re.finditer(r'^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$', md, re.M):
        f[m.group(1)] = m.group(2).strip('` ')
    return f


def parse_note(path):
    md = open(path, encoding='utf-8').read()
    f, sec = _fields(md), _sections(md)
    title = md.splitlines()[0].lstrip('# ').strip() if md else ''
    ctx = []
    for k, v in sec.items():
        if '怎麼被引用' in k:
            ctx = [ln.lstrip('> ').strip() for ln in v if ln.startswith('>') and ln.lstrip('> ').strip()]
    note = []
    for k, v in sec.items():
        if k.startswith('note'):
            note = [ln for ln in v if ln.strip() and not ln.strip().startswith('<!--')]
    src = f.get('來源', '')
    m = re.search(r'\[(\d+)\]', src)
    pdf = re.match(r'(pdf/[^\s（(]+\.pdf)', f.get('PDF', ''))
    return dict(paper_id=f.get('paper_id', os.path.basename(path)[:-3]), title=title,
                citing=re.sub(r'\s*參考文獻.*$', '', src).strip(), ref_no=m.group(1) if m else '',
                year=f.get('year', ''), venue=f.get('出處', ''), url=f.get('URL', ''),
                role=f.get('在你論文中的角色', ''), contexts='\n'.join(ctx), note='\n'.join(note).strip(),
                pdf=pdf.group(1) if pdf else '')


def build(db, corpus_dir, registry):
    """registry：{path: row}。回傳寫入筆數。"""
    db.executescript(SCHEMA)
    by_path = {p: r for p, r in registry.items()}

    def doc_of(path):
        r = by_path.get(path)
        if not r:
            return ''
        if r['canonical'] == 'True':
            return r['doc_id']
        # 重複檔 → 換成同組的 canonical
        for x in registry.values():
            if x['group'] == r['group'] and x['canonical'] == 'True':
                return x['doc_id']
        return ''

    def mine_doc(keys):
        for k in keys:
            for p, r in registry.items():
                if '/_mine/' in p and k in p:
                    d = doc_of(p)
                    if d:
                        return d
        return ''

    n = 0
    for d in (sorted(os.listdir(corpus_dir)) if os.path.isdir(corpus_dir) else []):   # 沒有 corpus（全新安裝）→ 引用表為空
        full = os.path.join(corpus_dir, d)
        if not (d.endswith('_refs') and os.path.isdir(full)):
            continue
        keys = MINE.get(d, [])
        for f in sorted(os.listdir(full)):
            if not f.endswith('.md') or f.upper().startswith('README'):
                continue
            x = parse_note(os.path.join(full, f))
            # 「來源」欄若點名某個版本（例如 arXiv 2211.06663），就對到那個版本的 PDF
            named = [k for k in keys if k in x['citing']]
            citing_doc = mine_doc(named + [k for k in keys if k not in named])
            cited = doc_of(f'corpus/{d}/{x["pdf"]}') if x['pdf'] else ''
            db.execute('INSERT INTO cites(citing_doc, citing, ref_no, paper_id, cited_doc, title, year, venue, url, role, '
                       'contexts, note, refs_dir) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (citing_doc, x['citing'], x['ref_no'], x['paper_id'], cited, x['title'], x['year'],
                        x['venue'], x['url'], x['role'], x['contexts'], x['note'], d))
            n += 1
    build.report = attach_fulltext(db)
    return n


# ---------------- 從全文抓引用句 ----------------
_MARK = re.compile(r'\[(\d+(?:\s*[,\-–]\s*\d+)*)\]')
_SENT_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z(\[])')
_ABBR = re.compile(r'\b(et al|Fig|Figs|Eq|Eqs|Sec|Tab|e\.g|i\.e|vs|cf|No|Ref|Refs)\.$', re.I)


def _refs_in(marker):
    out = set()
    for part in marker.split(','):
        nums = [int(x) for x in re.findall(r'\d+', part)]
        if len(nums) == 2 and re.search(r'[\-–]', part) and 0 < nums[1] - nums[0] < 30:
            out.update(range(nums[0], nums[1] + 1))
        else:
            out.update(nums)
    return out


def sentences_with_refs(db, doc_id):
    """你論文的內文（不含參考文獻區、表格）→ {參考文獻編號: [(句子, para_id), ...]}"""
    rows = db.execute("SELECT para_id, kind, text FROM paras WHERE doc_id = ? AND kind IN ('text', 'caption', 'footnote') "
                      "ORDER BY CAST(seq AS INTEGER)", (doc_id,)).fetchall()
    # 段落接成一條文字流（跨欄、跨頁被切開的句子能接回來），記住每個字元屬於哪個 para_id
    stream, owner = '', []
    for pid, kind, text in rows:
        sep = ' ' if stream and not stream.endswith(('.', '!', '?', ':')) and kind == 'text' else '\n'
        stream += sep; owner.append((len(stream), pid)); stream += text
    def pid_at(i):
        last = owner[0][1] if owner else ''
        for start, pid in owner:
            if start > i:
                break
            last = pid
        return last
    # 切句（略過 et al. / Fig. 這類縮寫）
    sents, start = [], 0
    for m in list(_SENT_END.finditer(stream)) + [None]:
        end = m.start() if m else len(stream)
        if m and _ABBR.search(stream[start:end]):
            continue
        sents.append((start, end)); start = m.end() if m else end
    out = {}
    for a, b in sents:
        for line_start, piece in _split_lines(stream, a, b):
            for mk in _MARK.finditer(piece):
                for n in _refs_in(mk.group(1)):
                    lst = out.setdefault(n, [])
                    item = (re.sub(r'\s+', ' ', piece).strip(), pid_at(line_start + mk.start()))
                    if item not in lst:
                        lst.append(item)
    return out


def _split_lines(stream, a, b):
    """句子內若有段落換行（不同段落），分開成各自的片段"""
    pos = a
    for piece in stream[a:b].split('\n'):
        if piece.strip():
            yield pos, piece
        pos += len(piece) + 1


def _words(s):
    return set(re.findall(r'[a-z]{4,}', s.lower()))


def attach_fulltext(db, min_agree=0.8):
    """每篇你的論文：用全文抓的引用句取代筆記句子。
    安全檢查：筆記句子和全文句子（同一個編號）要有 min_agree 以上吻合，才代表全文和筆記是同一個版本、編號一致；
    吻合率太低（例如論文庫裡的 PDF 是另一個版本）就整篇保留筆記句子，ctx_source 標 note:version-mismatch。
    回傳 {citing_doc: (吻合數, 有筆記句子的數量, 是否採用全文)}"""
    report = {}
    for (did,) in db.execute("SELECT DISTINCT citing_doc FROM cites WHERE citing_doc != ''").fetchall():
        refs = sentences_with_refs(db, did)
        rows = db.execute('SELECT rowid, ref_no, contexts FROM cites WHERE citing_doc = ?', (did,)).fetchall()
        agree = with_note = 0
        for _, ref_no, ctx in rows:
            notes = [c for c in (ctx or '').split('\n') if c.strip()]
            if not notes:
                continue
            with_note += 1
            hit = refs.get(int(ref_no)) if ref_no.isdigit() else None
            if hit and any(len(_words(n) & _words(h[0])) / max(1, len(_words(n))) > 0.6 for n in notes for h in hit):
                agree += 1
        use = bool(refs) and (with_note == 0 or agree / with_note >= min_agree)
        report[did] = (agree, with_note, use)
        if not use:
            if refs:
                db.execute("UPDATE cites SET ctx_source = 'note:version-mismatch' WHERE citing_doc = ?", (did,))
            continue
        for rowid, ref_no, _ in rows:
            hit = refs.get(int(ref_no)) if ref_no.isdigit() else None
            if hit:
                db.execute("UPDATE cites SET contexts = ?, ctx_paras = ?, ctx_source = 'fulltext' WHERE rowid = ?",
                           ('\n'.join(x[0] for x in hit), '\n'.join(x[1] for x in hit), rowid))
    return report
