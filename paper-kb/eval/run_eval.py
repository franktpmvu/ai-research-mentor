# -*- coding: utf-8 -*-
"""評估（R07）：比較 encoder（fulltext／vector／hybrid）在各問句版本上的表現。

目前是「代理指標」：還沒有候選池標註（qrels）時，以「當時討論的那篇論文（context_doc_id）」當作正確文件，
只算任務 A（跨文件找論文）的文件層級：Hit@5、Hit@10、MRR@10。其他相關論文也算對的情況要等標註後才算得到，
所以這裡是下限。

  python eval/run_eval.py                                  全文＋config.json 裡所有 embed_models
  python eval/run_eval.py --models qwen3-embedding:0.6b    只跑指定模型（逗號分隔）
  python eval/run_eval.py --no-vector                      只跑全文（不需要 Ollama）

結果寫到 eval/results/YYMMDD_proxy_taskA.md（同一天重跑會覆蓋）。
"""
import os
import sys
import json
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from paper_kb import index                      # noqa: E402

FIELDS = [('raw', 'query'), ('sem_zh', 'query_sem'), ('sem_en', 'query_sem_en')]
K = 10


def doc_rank(hits, gold):
    seen = []
    for h in hits:
        if h['doc_id'] not in seen:
            seen.append(h['doc_id'])
    return seen.index(gold) + 1 if gold in seen else None


def main(argv):
    db = index.connect(os.path.join(ROOT, 'data', 'derived', 'index', 'papers.db'), readonly=True)
    qs = [json.loads(l) for l in open(os.path.join(ROOT, 'eval', 'questions.jsonl'), encoding='utf-8')]
    qs = [q for q in qs if q.get('context_doc_id')]
    encoders = [('fulltext', None)]
    if '--no-vector' not in argv:
        from paper_kb.encoders import vector
        models = (argv[argv.index('--models') + 1].split(',') if '--models' in argv
                  else vector.models_from_config())
        for m in models:
            ok, msg = vector.ollama_ok(m)
            if not ok:
                print('略過', m, '：', msg); continue
            encoders += [('vector', m), ('hybrid', m)]

    def run(enc, model, text):
        if enc == 'fulltext':
            try:
                return index.search(db, text, k=40)   # 取多一點段落，才湊得到 10 份文件
            except ValueError:
                return []
        from paper_kb.encoders import vector
        f = vector.search if enc == 'vector' else vector.hybrid
        return f(db, text, model, k=40)

    rows, worst = [], {}
    for enc, model in encoders:
        name = enc if not model else f'{enc}（{model}）'
        for fname, key in FIELDS:
            ranks = []
            for q in qs:
                r = doc_rank(run(enc, model, q[key]), q['context_doc_id'])
                ranks.append(r)
                if r is None or r > 5:
                    worst.setdefault((name, fname), []).append(q['id'])
            n = len(ranks)
            h5 = sum(1 for r in ranks if r and r <= 5)
            h10 = sum(1 for r in ranks if r and r <= K)
            mrr = sum(1 / r for r in ranks if r and r <= K) / n
            rows.append((name, fname, h5, h10, mrr, n))
            print(f'{name:34s} {fname:7s} Hit@5 {h5:2d}/{n}  Hit@10 {h10:2d}/{n}  MRR@10 {mrr:.3f}')

    v = json.load(open(os.path.join(ROOT, 'data', 'derived', 'index_version.json')))
    out = os.path.join(ROOT, 'eval', 'results', f'{datetime.date.today():%y%m%d}_proxy_taskA.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        from paper_kb.encoders.vector import EMBED_VERSION
    except Exception:
        EMBED_VERSION = '-'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f'# 任務 A 代理評估（{datetime.datetime.now():%Y-%m-%d %H:%M}）\n\n'
                f'- index_version {v["version"]}｜pipeline {v.get("pipeline")}｜embed {EMBED_VERSION}\n'
                f'- 題目：eval/questions.jsonl 中有 context_doc_id 的 {len(qs)} 題\n'
                f'- 代理指標：以當時討論的論文為唯一正確文件（其他相關論文不算），所以是下限；'
                f'問句版本 raw＝原句、sem_zh／sem_en＝不含論文或方法名稱的語意問句\n\n'
                '| encoder | 問句 | Hit@5 | Hit@10 | MRR@10 |\n|---|---|---|---|---|\n')
        for name, fname, h5, h10, mrr, n in rows:
            f.write(f'| {name} | {fname} | {h5}/{n} | {h10}/{n} | {mrr:.3f} |\n')
        f.write('\n## 沒進前 5 的題目\n')
        for (name, fname), ids in worst.items():
            f.write(f'- {name}／{fname}：{" ".join(ids)}\n')
    print('→', os.path.relpath(out, ROOT))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
