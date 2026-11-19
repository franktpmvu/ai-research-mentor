# -*- coding: utf-8 -*-
"""建候選池（R07 步驟 2）：每題 × 每種問句版本 × 每個 encoder 各取前 N 段，聯集起來給人或 LLM 標註。

一個（題目, 段落）的相關程度只標一次，任務 A 和 B 共用：
- 任務 A（跨文件）：raw、query_sem、query_sem_en，在全部文件裡搜。
- 任務 B（文件內）：同樣三種問句，但只在 context_doc_id 那篇裡搜。

  python eval/build_pool.py                 每組取前 5 段（預設）
  python eval/build_pool.py --depth 10      每組取前 10 段
  python eval/build_pool.py --no-vector     只用全文（不需要 Ollama；候選池會偏向全文，不公平，只供測試）

輸出 eval/pool.jsonl：一行一個（題目, 段落），附全文與「被誰找到、排第幾」。
已經標過的（eval/qrels.jsonl 裡有的）不會重複列出，所以加了新 encoder 後重跑，只會多出要補標的段落。
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from paper_kb import index                      # noqa: E402

FIELDS = [('raw', 'query'), ('sem_zh', 'query_sem'), ('sem_en', 'query_sem_en')]


def main(argv):
    depth = int(argv[argv.index('--depth') + 1]) if '--depth' in argv else 5
    db = index.connect(os.path.join(ROOT, 'data', 'derived', 'index', 'papers.db'), readonly=True)
    qs = [json.loads(l) for l in open(os.path.join(ROOT, 'eval', 'questions.jsonl'), encoding='utf-8')]
    qrels = os.path.join(ROOT, 'eval', 'qrels.jsonl')
    done = set()
    if os.path.exists(qrels):
        for l in open(qrels, encoding='utf-8'):
            if l.strip():
                r = json.loads(l); done.add((r['id'], r['para_id']))

    encs = [('fulltext', None)]
    if '--no-vector' not in argv:
        from paper_kb.encoders import vector
        for m in vector.models_from_config():
            ok, msg = vector.ollama_ok(m)
            if not ok:
                sys.exit(f'❌ {msg}（候選池要用到所有 encoder，否則對沒參加的 encoder 不公平；只想測試可加 --no-vector）')
            encs += [('vector', m), ('hybrid', m)]

    def run(enc, model, text, scope):
        if enc == 'fulltext':
            try:
                return index.search(db, text, k=depth, doc_ids_filter=scope)
            except ValueError:
                return []
        from paper_kb.encoders import vector
        f = vector.search if enc == 'vector' else vector.hybrid
        return f(db, text, model, k=depth, doc_ids_filter=scope)

    pool = {}
    for n, q in enumerate(qs, 1):
        tasks = [('A', None)] + ([('B', [q['context_doc_id']])] if q.get('context_doc_id') else [])
        for task, scope in tasks:
            for fname, key in FIELDS:
                for enc, model in encs:
                    tag = f"{task}/{fname}/{enc}{':' + model.split(':')[-1] if model else ''}"
                    for rank, h in enumerate(run(enc, model, q[key], scope), 1):
                        k = (q['id'], h['para_id'])
                        if k in done:
                            continue
                        pool.setdefault(k, {'id': q['id'], 'para_id': h['para_id'], 'doc_id': h['doc_id'],
                                            'found_by': []})['found_by'].append(f'{tag}@{rank}')
        print(f'\r{n}/{len(qs)} 題，候選池 {len(pool)} 段', end='', flush=True)
    print()

    out = os.path.join(ROOT, 'eval', 'pool.jsonl')
    with open(out, 'w', encoding='utf-8') as f:
        for (qid, pid), r in sorted(pool.items()):
            p = index.get_paragraphs(db, [pid])[0]
            title = db.execute('SELECT title FROM docs WHERE doc_id = ?', (r['doc_id'],)).fetchone()[0]
            r.update(title=title, page=p.get('page'), section=p.get('section'), text=p.get('text'))
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    per_q = {}
    for qid, _ in pool:
        per_q[qid] = per_q.get(qid, 0) + 1
    print(f'→ eval/pool.jsonl：{len(pool)} 段要標（{len(per_q)} 題，平均每題 {len(pool) / max(1, len(per_q)):.0f} 段）；'
          f'已標過而略過 {len(done)} 筆')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
