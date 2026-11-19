# -*- coding: utf-8 -*-
"""搜尋索引：SQLite FTS5（BM25），一個檔案 data/derived/index/papers.db

表格：
  docs   每份文件一列：doc_id, title, path, source, mine, arxiv, doi, pages
  paras  每段一列（FTS5）：text、section、alt 可搜尋；para_id, doc_id, page, kind 只存不搜
         alt：換行斷字的接合寫法（原文 "Cycle- GAN" → alt 放 "CycleGAN"），只用來搜尋，不顯示
  meta   索引版本；版本不同時 connect() 會整個重建表格
改了表格結構或斷詞方式 → 改 INDEX_VERSION，update.py 會自動重建全部索引。
"""
import re
import sqlite3

INDEX_VERSION = 'fts5-porter/v5'

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(
  doc_id TEXT PRIMARY KEY, title TEXT, path TEXT, source TEXT, mine TEXT,
  arxiv TEXT, doi TEXT, pages INTEGER, n_paras INTEGER);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS paras USING fts5(
  text, section, alt, para_id UNINDEXED, doc_id UNINDEXED, page UNINDEXED, kind UNINDEXED, seq UNINDEXED,
  tokenize = 'porter unicode61 remove_diacritics 2');
"""
_ids = None


def connect(path, readonly=False):
    import os
    if readonly:
        from pathlib import Path
        return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, check_same_thread=False)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    # 掛載的磁碟（例如 VM 共用的 Windows 資料夾）不支援 SQLite 檔案鎖 → 改用獨占鎖＋日誌放記憶體。
    # 代價：寫到一半當掉索引可能壞掉；索引可重建（python update.py --rebuild）。
    db.execute('PRAGMA locking_mode=EXCLUSIVE')
    db.execute('PRAGMA journal_mode=MEMORY')
    try:
        v = db.execute("SELECT value FROM meta WHERE key = 'index_version'").fetchone()
    except sqlite3.OperationalError:
        v = None
    if not v or v[0] != INDEX_VERSION:     # 表格結構可能改了 → 整個重建（update.py 會重新寫入全部文件）
        db.executescript('DROP TABLE IF EXISTS paras; DROP TABLE IF EXISTS docs; DROP TABLE IF EXISTS meta;')
    db.executescript(SCHEMA)
    db.execute("INSERT OR REPLACE INTO meta VALUES ('index_version', ?)", (INDEX_VERSION,))
    return db


def doc_ids(db, cached=False):
    global _ids
    if not cached or _ids is None:
        _ids = {r[0] for r in db.execute('SELECT doc_id FROM docs')}
    return _ids


def delete(db, doc_id):
    db.execute('DELETE FROM paras WHERE doc_id = ?', (doc_id,))
    db.execute('DELETE FROM docs WHERE doc_id = ?', (doc_id,))
    doc_ids(db, cached=True).discard(doc_id)


BAD_TITLE = re.compile(
    r'^<|\.pdf$|\.docx?$|^(microsoft word|powerpoint|overleaf|untitled|official|arxiv)|\.\.\d|'
    r'^([\dIVX]+\s*\.?\s*)*(introduction|abstract|contents|preface)$|^[\d\. ]+$|(大學|university).{0,12}(碩士|博士|thesis)', re.I)


def bad_title(t):
    t = (t or '').strip()
    return len(t) < 12 or bool(BAD_TITLE.search(t))


def font_title(pdf_path):
    """第一頁字體最大的那幾行（多數論文的標題）"""
    try:
        import pymupdf
        with pymupdf.open(pdf_path) as doc:
            spans = [(round(s['size'], 1), s['text'].strip(), s['bbox'][1])
                     for b in doc[0].get_text('dict')['blocks'] for l in b.get('lines', [])
                     if abs(l.get('dir', (1, 0))[1]) < 0.1            # 略過直排（arXiv 側邊標記）
                     for s in l['spans'] if s['text'].strip() and 'arxiv' not in s['text'].lower()]
        if not spans:
            return ''
        top = max(x[0] for x in spans if len(x[1]) > 2) if any(len(x[1]) > 2 for x in spans) else 0
        return re.sub(r'\s+', ' ', ' '.join(x[1] for x in spans if x[0] >= top - 0.5)).strip()[:250]
    except Exception:
        return ''


_SPLIT = re.compile(r'(\w+)-\s+(\w+)')


def _alt(text):
    """換行斷字沒接回去的（"Cycle- GAN"、"tra- cking"）→ 接合寫法，放進只供搜尋的 alt 欄"""
    return ' '.join(a + b for a, b in _SPLIT.findall(text))


def upsert(db, meta, parsed, font_title=''):
    """meta：registry 的一列；parsed：解析層輸出的 dict；font_title：第一頁最大字（標題都不可靠時用）"""
    did = meta['doc_id']
    delete(db, did)
    title = next((t for t in (meta.get('title_guess'), parsed.get('title'), font_title) if not bad_title(t)),
                 meta['path'].rsplit('/', 1)[-1])
    rows = [(b['text'], b['section'], _alt(b['text']), b['para_id'], did, b['page'], b['kind'], i)
            for i, b in enumerate(parsed['blocks'])]
    db.executemany('INSERT INTO paras(text, section, alt, para_id, doc_id, page, kind, seq) VALUES (?,?,?,?,?,?,?,?)', rows)
    db.execute('INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?)',
               (did, title, meta['path'], meta['source'], meta['mine'], meta['arxiv'], meta['doi'],
                int(parsed.get('pages') or 0), len(rows)))
    doc_ids(db, cached=True).add(did)


# ---------------- 查詢（MCP server 用） ----------------
_OPS = re.compile(r'"|\b(AND|OR|NOT|NEAR)\b|\*')


def _fts_query(q, mode):
    """一般文字 → FTS5 查詢。使用者若已寫 FTS5 語法（引號、AND/OR/NEAR、*）就原樣使用。"""
    if _OPS.search(q):
        return q
    terms = [t for t in re.findall(r'[\w\-]+', q) if len(t) > 1 or t.isdigit()]
    terms = ['"' + t.replace('"', '') + '"' for t in terms]
    return (' AND ' if mode == 'and' else ' OR ').join(terms)


def search(db, query, k=10, include_references=False, kinds=None, doc_ids_filter=None, source=None):
    """回傳依 BM25 排序的段落。先要求所有關鍵字都出現（AND），不夠 k 筆再放寬成 OR。
    全大寫的縮寫（MGS、EAO、AUC）要大小寫完全相符：避免 MGS 被字根處理成 mg 而命中藥物劑量。"""
    acr = [t for t in re.findall(r'\b[A-Z][A-Z0-9]{1,7}\b', query) if t not in ('AND', 'OR', 'NOT', 'NEAR')
           and sum(c.isalpha() for c in t) >= 2]
    acr_re = [re.compile(r'(?<![A-Za-z0-9])' + re.escape(t) + r's?(?![A-Za-z0-9])') for t in acr]
    where, args = [], []
    if not include_references:
        where.append("p.kind != 'reference'")
    if kinds:
        where.append('p.kind IN (%s)' % ','.join('?' * len(kinds))); args += list(kinds)
    if doc_ids_filter:
        where.append('p.doc_id IN (%s)' % ','.join('?' * len(doc_ids_filter))); args += list(doc_ids_filter)
    if source:
        where.append('d.source = ?'); args.append(source)
    extra = (' AND ' + ' AND '.join(where)) if where else ''
    sql = (f"SELECT p.para_id, p.doc_id, d.title, p.page, p.section, p.kind, "
           f"snippet(paras, 0, '**', '**', ' … ', 40), bm25(paras, 1.0, 0.5, 1.0) AS s, p.text, p.alt "
           f"FROM paras p JOIN docs d ON d.doc_id = p.doc_id "
           f"WHERE paras MATCH ?{extra} ORDER BY s LIMIT ?")
    out, seen = [], set()
    for mode in ('and', 'or'):
        fq = _fts_query(query, mode)
        if not fq:
            break
        try:
            rows = db.execute(sql, [fq] + args + [3000 if acr_re else k]).fetchall()
        except sqlite3.OperationalError as e:
            raise ValueError(f'查詢語法錯誤：{e}（查詢：{fq}）')
        for r in rows:
            if r[0] in seen or not all(x.search(r[8]) or x.search(r[9] or '') for x in acr_re):
                continue
            seen.add(r[0])
            out.append(dict(para_id=r[0], doc_id=r[1], title=r[2], page=r[3], section=r[4], kind=r[5],
                            snippet=r[6], score=round(-r[7], 2), match='all-terms' if mode == 'and' else 'any-term'))
        if len(out) >= k or _OPS.search(query):
            break
    return out[:k]


def get_paragraphs(db, para_ids, window=0):
    """依 para_id 取段落；window=N 連前後各 N 段一起回傳（同一份文件內）"""
    out, seen = [], set()
    for pid in para_ids:
        r = db.execute('SELECT doc_id, CAST(seq AS INTEGER) FROM paras WHERE para_id = ?', (pid,)).fetchone()
        if not r:
            out.append(dict(para_id=pid, missing=True)); continue
        rows = db.execute('SELECT para_id, page, section, kind, text FROM paras WHERE doc_id = ? '
                          'AND CAST(seq AS INTEGER) BETWEEN ? AND ? ORDER BY CAST(seq AS INTEGER)',
                          (r[0], r[1] - window, r[1] + window)).fetchall()
        for x in rows:
            if x[0] not in seen:
                seen.add(x[0])
                out.append(dict(para_id=x[0], doc_id=r[0], page=x[1], section=x[2], kind=x[3], text=x[4],
                                target=(x[0] == pid)))
    return out


def get_paras(db, doc_id, pages=None, section=None, kinds=None):
    where, args = ['doc_id = ?'], [doc_id]
    if pages:
        where.append('page IN (%s)' % ','.join('?' * len(pages))); args += [int(p) for p in pages]
    if section:
        where.append('section LIKE ?'); args.append(f'%{section}%')
    if kinds:
        where.append('kind IN (%s)' % ','.join('?' * len(kinds))); args += list(kinds)
    rows = db.execute(f"SELECT para_id, page, section, kind, text FROM paras WHERE {' AND '.join(where)} "
                      f"ORDER BY CAST(seq AS INTEGER)", args).fetchall()
    return [dict(para_id=r[0], page=r[1], section=r[2], kind=r[3], text=r[4]) for r in rows]


def get_doc(db, doc_id):
    r = db.execute('SELECT * FROM docs WHERE doc_id = ?', (doc_id,)).fetchone()
    if not r:
        return None
    cols = [c[0] for c in db.execute('SELECT * FROM docs LIMIT 0').description]
    return dict(zip(cols, r))
