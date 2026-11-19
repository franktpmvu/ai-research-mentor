# -*- coding: utf-8 -*-
"""用地端 LLM（Ollama）預先標註候選池（R07 步驟 3）：每個（題目, 段落）標 0／1／2。

  python eval/llm_label.py --sample 50          先隨機抽 50 筆試標（固定亂數種子，可重現）
  python eval/llm_label.py                      標完候選池全部（已標過的會跳過，可以中途停、下次接著標）
  python eval/llm_label.py --model qwen3:8b     指定模型（預設 qwen3:8b）
  python eval/llm_label.py --sample 50 --out eval/qrels_trial_v2.jsonl
                                                寫到另一個檔（試新提示詞用；同樣的亂數種子會抽到和第一次相同的 50 筆）

給 1、2 分時要附上段落原文的一句話（evidence），程式會檢查這句真的在段落裡，不在就降為 0 分，
用來擋掉「問題裡有的詞、就以為段落裡也有」這種錯誤。

輸出寫進 eval/qrels.jsonl，一行一筆：{"id", "para_id", "rel", "by": "llm:<模型>", "reason"}。
使用者或 Claude 抽查修正時，改寫同一筆並把 by 改成 "user" 或 "claude"。
"""
import os
import sys
import json
import time
import random
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from paper_kb.encoders.vector import ollama_url, ollama_ok   # noqa: E402

PROMPT = """你是資訊檢索評估的標註員。判斷「段落」對「問題」的相關程度。

問題（中文）：{q_zh}
問題（英文）：{q_en}
使用者當時的原句：{q_raw}

段落出處：{title}｜{section}｜第 {page} 頁
段落：
\"\"\"{text}\"\"\"

評分標準：
2 = 段落直接回答問題的核心，或清楚解釋了問題問的機制或原因。
1 = 部分相關：講的是同一個主題或方法，提供了背景或部分答案，但沒有回答核心。
0 = 不相關：只是用詞相近、只是順帶提到、或是在講別的東西。
只根據段落本身判斷，不要用你自己的知識補上段落沒寫的內容。問題裡出現的詞，段落裡不一定有。
給 1 或 2 分時，evidence 必須是從段落原文一字不改複製的一句話（英文就照抄英文），用來證明段落真的講到了；
找不到這樣的句子，就給 0 分，evidence 留空字串。

只輸出 JSON：{{"rel": 0 或 1 或 2, "evidence": "段落原文的一句話", "reason": "一句話說明"}}"""

SCHEMA = {'type': 'object', 'properties': {'rel': {'type': 'integer', 'enum': [0, 1, 2]},
                                           'evidence': {'type': 'string'}, 'reason': {'type': 'string'}},
          'required': ['rel', 'evidence', 'reason']}


def _norm(s):
    return ' '.join((s or '').split()).lower()


def check_evidence(r, text):
    """rel>0 時，evidence 必須真的出現在段落裡（至少 12 個字元）；否則降為 0 分。回傳 (rel, 是否被降分)"""
    rel = int(r['rel'])
    ev = _norm(r.get('evidence', '')).strip(' ."“”')
    if rel > 0 and (len(ev) < 12 or ev not in _norm(text)):
        return 0, True
    return rel, False


def ask(model, prompt):
    body = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'stream': False,
                       'think': False, 'format': SCHEMA,
                       'options': {'temperature': 0, 'num_ctx': 4096}}).encode('utf-8')
    req = urllib.request.Request(ollama_url() + '/api/chat', data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(json.loads(r.read())['message']['content'])


def main(argv):
    model = argv[argv.index('--model') + 1] if '--model' in argv else 'qwen3:8b'
    ok, msg = ollama_ok(model)
    if not ok:
        sys.exit('❌ ' + msg)
    qs = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(ROOT, 'eval', 'questions.jsonl'), encoding='utf-8')}
    pool_f = os.path.join(ROOT, 'eval', 'pool.jsonl')
    if not os.path.exists(pool_f):
        sys.exit('❌ 還沒有 eval/pool.jsonl：先跑 python eval/build_pool.py')
    pool = [json.loads(l) for l in open(pool_f, encoding='utf-8') if l.strip()]
    out_f = (os.path.abspath(argv[argv.index('--out') + 1]) if '--out' in argv
             else os.path.join(ROOT, 'eval', 'qrels.jsonl'))
    n_demoted = 0
    done = set()
    if os.path.exists(out_f):
        done = {(r['id'], r['para_id']) for r in map(json.loads, filter(str.strip, open(out_f, encoding='utf-8')))}
    todo = [p for p in pool if (p['id'], p['para_id']) not in done and p.get('text')]
    if '--sample' in argv:
        n = int(argv[argv.index('--sample') + 1])
        todo = random.Random(42).sample(todo, min(n, len(todo)))
    print(f'模型 {model}｜候選池 {len(pool)}｜已標 {len(done)}｜這次要標 {len(todo)}')
    t0 = time.time()
    with open(out_f, 'a', encoding='utf-8') as f:
        for i, p in enumerate(todo, 1):
            q = qs[p['id']]
            prompt = PROMPT.format(q_zh=q['query_sem'], q_en=q['query_sem_en'], q_raw=q['query'],
                                   title=p.get('title') or '', section=p.get('section') or '', page=p.get('page'),
                                   text=(p['text'] or '')[:3000])
            try:
                r = ask(model, prompt)
            except Exception as e:
                print(f'\n⚠️ {p["id"]} {p["para_id"]} 失敗：{e}（下次再標）'); continue
            rel, demoted = check_evidence(r, p['text'])
            n_demoted += demoted
            f.write(json.dumps({'id': p['id'], 'para_id': p['para_id'], 'rel': rel, 'by': f'llm:{model}',
                                'llm_rel': int(r['rel']), 'evidence': r.get('evidence', ''),
                                'reason': ('[證據不在段落裡→0] ' if demoted else '') + r.get('reason', '')},
                               ensure_ascii=False) + '\n')
            f.flush()
            el = time.time() - t0
            print(f'\r{i}/{len(todo)}  平均 {el / i:.1f} 秒/筆  預估剩 {el / i * (len(todo) - i) / 60:.0f} 分', end='', flush=True)
    print(f'\n→ {os.path.relpath(out_f, ROOT)}（證據不在段落裡而降為 0 分：{n_demoted} 筆）')


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
