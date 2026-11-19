# -*- coding: utf-8 -*-
"""向量 encoder（RAG）：用 Ollama 的 embedding 模型把段落轉成向量，查詢時找最接近的段落。

規格見 guide/rules/R05_encoder-vector-hybrid.md：
- 輸入：FTS5 索引裡的段落（para_id 為單位，跳過參考文獻區）。
- 輸出：[{para_id, doc_id, page, section, kind, title, snippet, score}]，和全文搜尋相同格式。
- 每個模型一個資料夾 data/derived/vectors/<模型>/，每份文件一組檔案（<doc_id>.npy＋<doc_id>.json），
  記錄模型與 EMBED_VERSION；版本不同就重算。整個資料夾可以刪掉重建。

Ollama 位址：環境變數 OLLAMA_HOST（預設 http://localhost:11434）。
用哪些模型：config.json 的 "embed_models"（預設 ["qwen3-embedding:0.6b"]）。
"""
import os
import re
import json
import time
import urllib.request

import numpy as np

# 送進 embedding 的文字格式（標題＋章節＋段落）。改了格式就把版本 +1，所有向量會重算。
EMBED_VERSION = 'title-section-text/v1'
MAX_CHARS = 2000          # 單段最多送多少字（段落通常遠小於此）
BATCH = 32
NUM_CTX = 2048            # Ollama context 長度；段落很短，開小可以省顯示卡記憶體

ROOT = os.environ.get('PAPER_KB_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
VEC_DIR = os.path.join(ROOT, 'data', 'derived', 'vectors')


def ollama_url():
    h = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
    return h if h.startswith('http') else 'http://' + h


def models_from_config():
    cfg = os.path.join(ROOT, 'config.json')
    try:
        m = json.load(open(cfg, encoding='utf-8')).get('embed_models')
    except Exception:
        m = None
    return m or ['qwen3-embedding:0.6b']


def slug(model):
    return re.sub(r'[^A-Za-z0-9._-]', '_', model)


# ---------- 各模型的查詢／文件前綴（依模型官方建議） ----------
def query_text(model, q):
    if 'qwen3-embedding' in model:
        return ('Instruct: Given a question, retrieve passages from research papers that answer it\n'
                f'Query: {q}')
    if 'embeddinggemma' in model:
        return f'task: search result | query: {q}'
    return q


def doc_text(model, title, section, text):
    title, section, text = (title or '').strip(), (section or '').strip(), (text or '').strip()
    if 'embeddinggemma' in model:
        return f'title: {title or "none"} | text: {section + chr(10) if section else ""}{text}'[:MAX_CHARS]
    return '\n'.join(x for x in (title, section, text) if x)[:MAX_CHARS]


# ---------- Ollama ----------
def embed(model, texts, timeout=300):
    """回傳 L2 正規化後的 float32 陣列（len(texts) × dim）"""
    body = json.dumps({'model': model, 'input': texts, 'truncate': True,
                       'options': {'num_ctx': NUM_CTX}}).encode('utf-8')
    req = urllib.request.Request(ollama_url() + '/api/embed', data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        v = np.asarray(json.loads(r.read())['embeddings'], dtype=np.float32)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.where(n == 0, 1, n)


def ollama_ok(model):
    """Ollama 有沒有開、模型有沒有 pull。回傳 (ok, 訊息)"""
    try:
        with urllib.request.urlopen(ollama_url() + '/api/tags', timeout=5) as r:
            names = {m['name'] for m in json.loads(r.read()).get('models', [])}
    except Exception as e:
        return False, f'連不到 Ollama（{ollama_url()}）：{e}'
    if model not in names and model + ':latest' not in names:
        return False, f'Ollama 裡沒有 {model}，請先執行 ollama pull {model}'
    return True, ''


# ---------- 建立／更新向量 ----------
def _paths(model, doc_id):
    d = os.path.join(VEC_DIR, slug(model))
    return d, os.path.join(d, doc_id + '.npy'), os.path.join(d, doc_id + '.json')


def _done(model, doc_id, n_paras, title):
    d, npy, js = _paths(model, doc_id)
    if not (os.path.exists(npy) and os.path.exists(js)):
        return False
    try:
        m = json.load(open(js, encoding='utf-8'))
    except Exception:
        return False
    # 標題會送進模型，標題改了（例如 config.json 的 title_overrides）也要重算；舊檔沒記標題的視為相同
    return (m.get('model') == model and m.get('version') == EMBED_VERSION and m.get('n_paras') == n_paras
            and m.get('title', title) == title)


def update(db, model, say=print, deadline=None, dry=False):
    """幫索引裡每份文件算向量（只算缺的或版本不同的），刪掉索引裡已不存在的文件。
    回傳 (算了幾份, 剩幾份)。deadline：time.time() 的截止時間，到了就先停。"""
    d = os.path.join(VEC_DIR, slug(model))
    docs = db.execute("SELECT d.doc_id, d.title, COUNT(p.para_id) FROM docs d JOIN paras p ON p.doc_id = d.doc_id "
                      "WHERE p.kind != 'reference' GROUP BY d.doc_id").fetchall()
    alive = {r[0] for r in docs}
    todo = [r for r in docs if not _done(model, r[0], r[2], r[1])]
    stale = [f for f in (os.listdir(d) if os.path.isdir(d) else []) if f.endswith('.json')
             and f[:-5] not in alive]
    say(f'⑥b 向量（{model}）：待算 {len(todo)} 份（共 {len(docs)} 份）、移除 {len(stale)} 份')
    if dry or (not todo and not stale):
        return 0, len(todo)
    ok, msg = ollama_ok(model)
    if not ok:
        say(f'   ⚠️ {msg} → 先略過向量，下次再算')
        return 0, len(todo)
    os.makedirs(d, exist_ok=True)
    for f in stale:
        for ext in ('.json', '.npy'):
            p = os.path.join(d, f[:-5] + ext)
            if os.path.exists(p):
                os.remove(p)
    done = 0
    t0 = time.time()
    for i, (doc_id, title, n) in enumerate(todo):
        if deadline and time.time() > deadline:
            break
        rows = db.execute("SELECT para_id, section, text FROM paras WHERE doc_id = ? AND kind != 'reference' "
                          "ORDER BY CAST(seq AS INTEGER)", (doc_id,)).fetchall()
        texts = [doc_text(model, title, r[1], r[2]) for r in rows]
        vecs = [embed(model, texts[j:j + BATCH]) for j in range(0, len(texts), BATCH)]
        v = np.concatenate(vecs) if vecs else np.zeros((0, 1), np.float32)
        _, npy, js = _paths(model, doc_id)
        np.save(npy + '.tmp.npy', v.astype(np.float16))
        os.replace(npy + '.tmp.npy', npy)
        json.dump({'model': model, 'version': EMBED_VERSION, 'n_paras': n, 'title': title,
                   'para_ids': [r[0] for r in rows]},
                  open(js, 'w', encoding='utf-8'))
        done += 1
        say(f'   [{i + 1}/{len(todo)}] {doc_id} {len(rows)} 段 {time.time() - t0:.0f}s')
    left = len(todo) - done
    say(f'   向量完成 {done} 份' + (f'；剩 {left} 份下次再算' if left else ''))
    return done, left


# ---------- 查詢 ----------
_cache = {}


def _load(model):
    """把某模型的所有向量讀進記憶體（依資料夾內檔案的修改時間判斷要不要重讀）"""
    d = os.path.join(VEC_DIR, slug(model))
    if not os.path.isdir(d):
        raise RuntimeError(f'還沒有 {model} 的向量；請先跑 update.py（需要 Ollama）')
    files = sorted(f for f in os.listdir(d) if f.endswith('.json'))
    sig = (len(files), max((os.path.getmtime(os.path.join(d, f)) for f in files), default=0))
    c = _cache.get(model)
    if c and c['sig'] == sig:
        return c
    mats, ids = [], []
    for f in files:
        m = json.load(open(os.path.join(d, f), encoding='utf-8'))
        if m.get('version') != EMBED_VERSION:
            continue
        v = np.load(os.path.join(d, f[:-5] + '.npy'))
        if len(v) != len(m['para_ids']):
            continue
        mats.append(v); ids += m['para_ids']
    mat = np.concatenate(mats).astype(np.float32) if mats else np.zeros((0, 1), np.float32)
    doc_of = np.array([p.split(':')[0] for p in ids])
    c = _cache[model] = {'sig': sig, 'mat': mat, 'ids': ids, 'doc_of': doc_of}
    return c


def _rowids(db):
    """para_id → FTS5 rowid（para_id 欄位沒有索引，逐筆查會掃整張表；一次讀進來，索引版本變了就重讀）"""
    n = db.execute('SELECT COUNT(*) FROM paras').fetchone()[0]
    c = _cache.get('_rowid')
    if not c or c['n'] != n or c['db'] is not db:
        c = _cache['_rowid'] = {'n': n, 'db': db,
                                'map': dict((r[1], r[0]) for r in db.execute('SELECT rowid, para_id FROM paras'))}
    return c['map']


_qcache = {}


def query_vec(model, query):
    """問句向量（快取：同一問句在 vector 和 hybrid 都會用到，不重算）"""
    key = (model, query)
    if key not in _qcache:
        if len(_qcache) > 2000:
            _qcache.clear()
        _qcache[key] = embed(model, [query_text(model, query)])[0]
    return _qcache[key]


def search(db, query, model, k=10, doc_ids_filter=None, source=None):
    c = _load(model)
    rowid = _rowids(db)
    if not c['ids']:
        return []
    q = query_vec(model, query)
    s = c['mat'] @ q
    mask = np.ones(len(s), bool)
    if doc_ids_filter:
        mask &= np.isin(c['doc_of'], list(doc_ids_filter))
    if source:
        ok = {r[0] for r in db.execute('SELECT doc_id FROM docs WHERE source = ?', (source,))}
        mask &= np.isin(c['doc_of'], list(ok))
    s = np.where(mask, s, -np.inf)
    top = np.argsort(-s)[:k]
    out = []
    for i in top:
        if not np.isfinite(s[i]):
            break
        pid = c['ids'][i]
        if pid not in rowid:
            continue
        r = db.execute('SELECT p.doc_id, d.title, p.page, p.section, p.kind, p.text FROM paras p '
                       'JOIN docs d ON d.doc_id = p.doc_id WHERE p.rowid = ?', (rowid[pid],)).fetchone()
        if not r:
            continue
        txt = r[5].replace('\n', ' ')
        out.append(dict(para_id=pid, doc_id=r[0], title=r[1], page=r[2], section=r[3], kind=r[4],
                        snippet=txt[:300] + (' …' if len(txt) > 300 else ''), score=round(float(s[i]), 4),
                        match='vector'))
    return out


def hybrid(db, query, model, k=10, doc_ids_filter=None, source=None, pool=50, rrf_k=60):
    """全文（BM25）和向量各取前 pool 段，用 RRF（Reciprocal Rank Fusion）合併；每筆標示來自哪個 encoder"""
    from paper_kb import index
    try:
        ft = index.search(db, query, k=pool, doc_ids_filter=doc_ids_filter, source=source)
    except ValueError:
        ft = []
    vec = search(db, query, model, k=pool, doc_ids_filter=doc_ids_filter, source=source)
    score, item, src = {}, {}, {}
    for name, lst in (('fulltext', ft), ('vector', vec)):
        for rank, h in enumerate(lst):
            score[h['para_id']] = score.get(h['para_id'], 0) + 1 / (rrf_k + rank + 1)
            item.setdefault(h['para_id'], h)
            src.setdefault(h['para_id'], []).append(name)
    out = []
    for pid in sorted(score, key=lambda p: -score[p])[:k]:
        h = dict(item[pid]); h['score'] = round(score[pid], 4); h['match'] = '+'.join(src[pid])
        out.append(h)
    return out
