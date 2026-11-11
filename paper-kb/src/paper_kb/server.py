# -*- coding: utf-8 -*-
"""paper-kb MCP server：你的論文庫（全文＋引用關係）的查詢與閱讀工具

啟動（stdio）：python -m paper_kb.server         （在 src/ 底下，或設定 PYTHONPATH=src）
資料位置：預設是本專案的 data/derived/；可用環境變數 PAPER_KB_ROOT 指到別的專案根目錄。

設計：server 只回傳原文與定位（doc_id、頁碼、para_id），不做摘要或判斷；判斷交給呼叫它的 AI。
跑完 update.py 不用重啟：每次呼叫都會檢查 index_version.json，版本變了就重新開啟資料庫。
"""
import os
import json
import sqlite3

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from paper_kb import index

ROOT = os.environ.get('PAPER_KB_ROOT') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DER = os.path.join(ROOT, 'data', 'derived')
DB_PATH = os.path.join(DER, 'index', 'papers.db')
VFILE = os.path.join(DER, 'index_version.json')

_state = {'db': None, 'version': None}


def db():
    v = None
    if os.path.exists(VFILE):
        try:
            v = json.load(open(VFILE)).get('version')
        except Exception:
            pass
    if _state['db'] is None or v != _state['version']:
        if _state['db'] is not None:
            _state['db'].close()
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f'找不到索引 {DB_PATH}；請先執行 python update.py')
        _state['db'] = index.connect(DB_PATH, readonly=True)
        _state['version'] = v
    return _state['db']


def _resolve(doc_id):
    """接受 doc_id、arXiv 編號、DOI 或筆記編號（如 nt02_siamfc）"""
    c = db()
    if c.execute('SELECT 1 FROM docs WHERE doc_id = ?', (doc_id,)).fetchone():
        return doc_id
    r = c.execute('SELECT doc_id FROM docs WHERE arxiv = ? OR doi = ?', (doc_id, doc_id)).fetchone()
    if r:
        return r[0]
    r = c.execute("SELECT cited_doc FROM cites WHERE paper_id = ? AND cited_doc != ''", (doc_id,)).fetchone()
    if r:
        return r[0]
    raise ToolError(f'找不到文件 {doc_id}；可以先用 list_documents（title=關鍵字）或 search 找 doc_id')


mcp = MCPServer(
    'paper-kb',
    instructions=(
        '使用者自己的論文庫：他讀過、收藏的論文全文，以及他已發表論文的參考文獻與引用原句。'
        '工具只回傳原文與定位資訊，不做判斷。回答時請引用 para_id（格式 <doc_id>:p<頁>:<段>）與頁碼；'
        '原文沒寫的事不要說成原文寫的。一般流程：search 找候選 → get_document 讀相關頁面或章節（或 get_paragraphs 讀指定段落）→ 根據原文回答。'
        '核實某篇論文是否支持某個說法時，直接用 get_document 讀那篇，不要只看 search 的片段。'
    ),
)


@mcp.tool()
def search(query: str, k: int = 10, include_references: bool = False,
           source: str | None = None, doc_ids: list[str] | None = None) -> str:
    """全文關鍵字搜尋（SQLite FTS5，BM25 排序）。回傳命中段落與所屬文件、頁碼，依文件分組。

    - query：英文關鍵字效果最好（論文都是英文）。會先找「所有字都出現」的段落，不足 k 筆再放寬成「任一字出現」。
      也可直接用 FTS5 語法：片語加引號 "expected average overlap"、AND / OR / NOT、NEAR(a b, 10)、前綴 track*。
    - include_references：是否包含參考文獻區（預設不含，避免只是被引用的論文名稱命中）。
    - source："collection"（使用者的論文收藏）或 "corpus"（他已發表論文的參考文獻）；不填 = 全部。
    - doc_ids：只在這幾份文件裡搜。
    片段只是線索；要確認內容請用 get_document 讀原文。
    """
    try:
        hits = index.search(db(), query, k=max(1, min(k, 50)), include_references=include_references,
                            doc_ids_filter=doc_ids, source=source)
    except ValueError as e:
        raise ToolError(str(e))
    if not hits:
        return f'沒有結果：{query}。可以換同義詞、用較少的關鍵字，或用前綴（例如 track*）。'
    groups = {}
    for h in hits:
        groups.setdefault(h['doc_id'], []).append(h)
    out = [f'{len(hits)} 段，來自 {len(groups)} 份文件（** ** 標出命中字）']
    for did, hs in groups.items():
        out.append(f"\n## {hs[0]['title']}  [doc_id={did}]")
        for h in hs:
            tag = '' if h['match'] == 'all-terms' else '（部分關鍵字）'
            out.append(f"- {h['para_id']}  p.{h['page']}  §{h['section'][:60]}  [{h['kind']}]{tag}\n  {h['snippet']}")
    return '\n'.join(out)


@mcp.tool()
def get_document(doc_id: str, pages: list[int] | None = None, section: str | None = None,
                 outline_only: bool = False, include_references: bool = False, max_chars: int = 60000) -> str:
    """讀一份文件的原文，每段前面標 [para_id] 與頁碼。

    - doc_id：也接受 arXiv 編號（如 2203.11991）、DOI、或筆記編號（如 nt02_siamfc）。
    - pages：只讀這些頁（例如 [3, 4]）。section：只讀標題含這個字串的章節（例如 "Method"）。
    - outline_only：只回傳章節標題與頁碼（先看結構再決定讀哪裡）。
    - include_references：是否包含參考文獻列表（預設不含）。
    - 超過 max_chars 會截斷並告訴你下一段從哪一頁開始。
    """
    did = _resolve(doc_id)
    meta = index.get_doc(db(), did)
    head = (f"# {meta['title']}\ndoc_id={did}  pages={meta['pages']}  source={meta['source']}"
            f"{'  （使用者自己的論文）' if meta['mine'] == 'True' else ''}"
            f"{'  arXiv=' + meta['arxiv'] if meta['arxiv'] else ''}{'  DOI=' + meta['doi'] if meta['doi'] else ''}\n")
    if outline_only:
        hs = index.get_paras(db(), did, kinds=['title', 'heading'])
        return head + '\n'.join(f"p.{h['page']}  {h['text'][:120]}" for h in hs)
    kinds = None if include_references else ['title', 'heading', 'text', 'caption', 'table', 'formula', 'footnote']
    ps = index.get_paras(db(), did, pages=pages, section=section, kinds=kinds)
    if not ps:
        return head + '（沒有符合條件的段落；可先用 outline_only=True 看章節與頁碼）'
    out, n, last_page = [head], len(head), None
    for p in ps:
        line = f"[{p['para_id']}] " + (f"## {p['text']}" if p['kind'] in ('heading', 'title') else
                                       f"({p['kind']}) {p['text']}" if p['kind'] not in ('text',) else p['text'])
        if p['page'] != last_page:
            line = f"\n--- p.{p['page']} ---\n" + line
        if n + len(line) > max_chars:
            out.append(f"\n…（已截斷：達到 max_chars={max_chars}。下一段是 {p['para_id']}：用 get_paragraphs 從它開始讀"
                       f"（window 可帶後文），或用 pages=[{p['page']}, …] 並調大 max_chars）")
            break
        out.append(line); n += len(line); last_page = p['page']
    return '\n'.join(out)


@mcp.tool()
def get_paragraphs(para_ids: list[str], window: int = 0) -> str:
    """依 para_id 讀指定段落（例如 search 結果裡的 "b0b8069bedbb:p8:1"），核實引用時最省事。

    - para_ids：一個或多個 para_id。
    - window：連前後各 N 段一起回傳（同一份文件），看上下文用；目標段落標 ★。
    """
    ps = index.get_paragraphs(db(), para_ids, window=max(0, min(window, 10)))
    out, last = [], None
    for p in ps:
        if p.get('missing'):
            out.append(f"[{p['para_id']}] （找不到這個 para_id）"); continue
        if p['doc_id'] != last:
            meta = index.get_doc(db(), p['doc_id'])
            out.append(f"\n# {meta['title']}  [doc_id={p['doc_id']}]"); last = p['doc_id']
        out.append(f"{'★' if p['target'] else ' '}[{p['para_id']}] p.{p['page']} §{p['section'][:60]} ({p['kind']})\n  {p['text']}")
    return '\n'.join(out).strip()


@mcp.tool()
def get_citations(doc_id: str | None = None, query: str | None = None) -> str:
    """引用關係（來自使用者已發表論文的參考文獻筆記）。

    - doc_id 是使用者自己的論文 → 列出它引用的所有文獻（編號、年份、引用原句、有沒有全文）。
    - doc_id 是其他論文 → 列出使用者哪篇論文引用了它、引用原句、使用者的筆記。
    - doc_id 和 query 一起給：只看這份文件相關的引用，再用關鍵字縮小。
    - query：關鍵字，會比對被引論文標題、筆記編號、引用原句、出處、使用者論文名稱（例如 "CycleGAN"、"SiamFC"、
      "LD-YOLOv7"）。多個字要全部出現。
    引用原句是使用者論文裡的原文；note 是使用者自己寫的筆記（沒寫就不顯示）。
    不帶參數：列出有引用資料的使用者論文。
    """
    c = db()
    cols = 'citing, ref_no, paper_id, cited_doc, title, year, venue, role, contexts, note, citing_doc, ctx_paras, ctx_source'
    if query:
        terms = [t for t in query.split() if t] or [query]
        hay = "(title || ' ' || paper_id || ' ' || contexts || ' ' || venue || ' ' || citing || ' ' || note)"
        cond = ' AND '.join(f'{hay} LIKE ?' for _ in terms)
        qargs = [f'%{t}%' for t in terms]
        if doc_id:   # 兩個都給：只在這份文件相關的引用裡找
            try:
                did = _resolve(doc_id)
            except ToolError:
                did = doc_id
            cond += ' AND (citing_doc = ? OR cited_doc = ? OR paper_id = ?)'
            qargs += [did, did, doc_id]
        rows = c.execute(f'SELECT {cols} FROM cites WHERE {cond} ORDER BY citing, CAST(ref_no AS INTEGER)',
                         qargs).fetchall()
    elif doc_id:
        try:
            did = _resolve(doc_id)
        except ToolError:
            did = doc_id
        rows = c.execute(f'SELECT {cols} FROM cites WHERE citing_doc = ? ORDER BY CAST(ref_no AS INTEGER)', (did,)).fetchall()
        if not rows:
            rows = c.execute(f'SELECT {cols} FROM cites WHERE cited_doc = ? OR paper_id = ?', (did, doc_id)).fetchall()
    else:
        rows = c.execute('SELECT citing, citing_doc, COUNT(*), SUM(cited_doc != \'\') FROM cites GROUP BY citing').fetchall()
        return '使用者已發表論文與參考文獻數：\n' + '\n'.join(
            f'- {r[0]}  [doc_id={r[1] or "（無全文）"}]  參考文獻 {r[2]} 篇，其中 {r[3]} 篇有全文' for r in rows)
    if not rows:
        have = ', '.join(r[0] for r in c.execute('SELECT DISTINCT citing FROM cites'))
        return ('沒有符合的引用紀錄。引用資料只涵蓋這幾篇使用者論文的參考文獻：' + have +
                '。其他論文（包括使用者其他版本或未收錄的論文）沒有引用資料，不代表它們沒有參考文獻；'
                '可用 get_document(doc_id, include_references=True) 讀原文的參考文獻列表。')
    out = []
    for r in rows:
        out.append(f"- [{r[1]}] {r[4]}（{r[5] or '年份未知'}{'，' + r[6] if r[6] else ''}）"
                   f"  paper_id={r[2]}  全文：{('doc_id=' + r[3]) if r[3] else '無'}\n"
                   f"  被 {r[0]}{' [doc_id=' + r[10] + ']' if r[10] else ''} 引用"
                   + (f"；角色：{r[7]}" if r[7] else '')
                   + _ctx_lines(r[8], r[11], r[12])
                   + (f'\n  note：{r[9]}' if r[9] else ''))
    return '\n'.join(out)


def _ctx_lines(contexts, paras, source):
    sents = [x for x in (contexts or '').split('\n') if x]
    pids = (paras or '').split('\n') if paras else []
    if source == 'fulltext':
        label = '\n  引用原句（從使用者論文全文自動抓取，附 para_id 可用 get_paragraphs 核對）：'
    elif source == 'note:version-mismatch':
        label = '\n  引用原句（來自筆記；論文庫裡這篇論文的 PDF 是另一個版本，參考文獻編號不同，所以沒有用全文）：'
    else:
        label = '\n  引用原句（來自筆記）：' if sents else ''
    return label + ''.join(f'\n  > {x}' + (f'  [{pids[i]}]' if i < len(pids) and pids[i] else '')
                           for i, x in enumerate(sents))


@mcp.tool()
def list_documents(title: str | None = None, source: str | None = None, mine: bool | None = None,
                   limit: int = 50, offset: int = 0) -> str:
    """列出索引裡的文件（標題、doc_id、頁數、來源、arXiv）。

    - title：標題包含的字（不分大小寫）。source："collection" 或 "corpus"。mine=True 只列使用者自己的論文。
    """
    where, args = [], []
    if title:
        where.append('title LIKE ?'); args.append(f'%{title}%')
    if source:
        where.append('source = ?'); args.append(source)
    if mine is not None:
        where.append('mine = ?'); args.append(str(bool(mine)))
    w = ('WHERE ' + ' AND '.join(where)) if where else ''
    c = db()
    total = c.execute(f'SELECT COUNT(*) FROM docs {w}', args).fetchone()[0]
    rows = c.execute(f'SELECT doc_id, title, pages, source, mine, arxiv FROM docs {w} ORDER BY title LIMIT ? OFFSET ?',
                     args + [limit, offset]).fetchall()
    out = [f'共 {total} 份（顯示 {offset + 1}–{offset + len(rows)}）']
    out += [f"- {r[1][:110]}  [doc_id={r[0]}] {r[2]}p {r[3]}{' ★mine' if r[4] == 'True' else ''}"
            f"{' arXiv:' + r[5] if r[5] else ''}" for r in rows]
    return '\n'.join(out)


def main():
    mcp.run('stdio')


if __name__ == '__main__':
    main()
