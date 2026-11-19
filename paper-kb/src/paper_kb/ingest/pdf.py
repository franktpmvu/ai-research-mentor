# -*- coding: utf-8 -*-
"""解析層：PDF → 帶頁碼、章節、段落編號的區塊

輸出格式（data/derived/parsed/<doc_id>.json）：
{
  "doc_id": "...", "parser": PARSER_VERSION, "title": "...", "pages": 12, "toc": [...],
  "blocks": [
    {"para_id": "<doc_id>:p3:2", "page": 3, "section": "3.1 Method", "kind": "text",
     "bbox": [x0, y0, x1, y1], "text": "..."}
  ]
}
kind：title / heading / text / caption / table / formula / footnote / reference
- 頁首頁尾、圖片區塊不輸出。
- 「References」標題之後的區塊標成 reference（搜尋時預設排除），遇到下一個標題就結束；
  之後若又出現長得像參考文獻條目的段落（排版順序錯亂時），也標成 reference。

目前實作：PyMuPDF4LLM（版面模型隨 pip 安裝，免 GPU、免下載）。授權：AGPL-3.0（個人或開源使用沒問題）。
要換成 Docling 等其他解析器：另寫一個同樣輸出格式的 parse_pdf，並在 update.py 改 VERSIONS['parser']。
"""
import re

PARSER_VERSION = 'pymupdf4llm-2.1/v2'

KIND = {
    'title': 'title', 'section-header': 'heading',
    'text': 'text', 'list-item': 'text',
    'caption': 'caption', 'table': 'table', 'formula': 'formula', 'footnote': 'footnote',
    'page-header': None, 'page-footer': None, 'picture': None,
}
REF_HEAD = re.compile(r'^\s*(\d+\.?\s*)?(references|bibliography|literature cited|reference list)\s*$', re.I)
# 參考文獻條目長相：[12] …／12. Author …／Author, A. …（且含年份）
REF_ENTRY = re.compile(r'^\s*(\[\d+\]|\d{1,3}\.\s+[A-Z]|[A-Z][A-Za-z\'\-]+,\s+[A-Z]\.)')
YEAR = re.compile(r'\b(19|20)\d\d\b')


def _looks_like_ref(text):
    return bool(REF_ENTRY.match(text)) and bool(YEAR.search(text))


SHY = '\u00ad'


def _fix_hyphens(blocks):
    """行尾斷字：同一篇其他地方有「cross-validation」這種寫法就保留連字號，否則接起來（tra-cking → tracking）。"""
    alltext = ' '.join(b['text'] for b in blocks)
    hyph = set(re.findall(r'\b\w+-\w+\b', alltext.lower()))

    def rep(m):
        a, b = m.group(1), m.group(2)
        return f'{a}-{b}' if f'{a}-{b}'.lower() in hyph else a + b
    for b in blocks:
        if SHY in b['text']:
            b['text'] = re.sub(r'(\w+)' + SHY + r'(\w+)', rep, b['text']).replace(SHY, '')


def _box_text(box):
    """把 textlines 組回文字；處理行尾連字號斷字。"""
    lines = []
    for ln in box.get('textlines') or []:
        # LaTeX 產生的 PDF 常沒有空白字元，單字是分開的 span：依水平間距補空格
        t, prev = '', None
        for s in ln.get('spans', []):
            txt = s.get('text', '')
            if not txt:
                continue
            bb = s.get('bbox') or [0, 0, 0, 0]
            size = s.get('size') or 10
            if prev is not None and t and not t.endswith(' ') and not txt.startswith(' '):
                gap = bb[0] - prev[2]
                if gap > 0.12 * size:
                    t += ' '
            t += txt
            prev = bb
        t = re.sub(r'\s+', ' ', t).strip()
        if t:
            lines.append(t)
    out = ''
    for t in lines:
        if not out:
            out = t
        elif out.endswith('-') and t[:1].islower():
            out = out[:-1] + SHY + t    # 行尾斷字先標記，整篇解析完再決定（見 _fix_hyphens）
        else:
            out += ' ' + t
    return out.strip()


def parse_pdf(path, doc_id):
    import json
    import pymupdf4llm

    raw = pymupdf4llm.to_json(path, use_ocr=False, show_progress=False)
    d = json.loads(raw) if isinstance(raw, str) else raw
    blocks, section, in_refs, refs_seen = [], '', False, False
    title = ''
    for pg in d.get('pages', []):
        page = int(pg.get('page_number', 0)) or (len(blocks) and blocks[-1]['page'] + 1) or 1
        n = 0
        for b in pg.get('boxes', []):
            kind = KIND.get(b.get('boxclass'), 'text')
            if kind is None:
                continue
            if kind == 'table':
                tb = b.get('table') or {}
                text = (tb.get('markdown') or '').strip() or _box_text(b)
            else:
                text = _box_text(b)
            if not text:
                continue
            if kind == 'title' and not title:
                title = text
            if kind == 'heading':
                # References 標題開始參考文獻區；之後任何其他標題（Appendix、Methods、或排版順序錯亂的 Conclusions）就結束
                in_refs = bool(REF_HEAD.match(text))
                refs_seen = refs_seen or in_refs
                section = text[:120]
            elif kind in ('text', 'footnote') and (in_refs or (refs_seen and _looks_like_ref(text))):
                kind = 'reference'
            n += 1
            blocks.append(dict(
                para_id=f'{doc_id}:p{page}:{n}', page=page, section=section, kind=kind,
                bbox=[round(float(b.get(k, 0)), 1) for k in ('x0', 'y0', 'x1', 'y1')], text=text))
    _fix_hyphens(blocks)
    toc = d.get('toc') or []
    if not title and toc:
        title = toc[0][1]
    if not title:
        title = (d.get('metadata') or {}).get('title', '')
        if title.startswith('<') or title.lower().startswith('microsoft word'):   # metadata 亂碼
            title = ''
    if len(title) < 15:   # 沒有 title 區塊、metadata 也沒有 → 用第一頁第一個夠長的標題
        title = next((b['text'] for b in blocks if b['page'] == 1 and b['kind'] == 'heading'
                      and len(b['text']) > 15), title)
    return dict(doc_id=doc_id, parser=PARSER_VERSION, title=title, pages=d.get('page_count', 0),
                toc=toc, blocks=blocks,
                stats=dict(n_blocks=len(blocks), n_chars=sum(len(x['text']) for x in blocks),
                           n_reference=sum(x['kind'] == 'reference' for x in blocks)))


if __name__ == '__main__':
    import sys, json, time
    t = time.time()
    r = parse_pdf(sys.argv[1], 'test')
    print(json.dumps(r['stats'], ensure_ascii=False), 'title=', r['title'][:80], f'{time.time() - t:.1f}s')
    for x in r['blocks'][:int(sys.argv[2]) if len(sys.argv) > 2 else 15]:
        print(x['para_id'], x['kind'], '|', x['section'][:30], '|', x['text'][:110])
