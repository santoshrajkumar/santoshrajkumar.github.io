"""Offline test of the site's topic search on many control topics.

Mirrors index.html: query = bge prefix + text when <= 24 words, CLS pooling, normalized; score = int8 row . q * scale
over papers.bin. Also replays the keyword fallback (title idf) used when the model cannot load, and compares the int8
index against full-precision embeddings (work/emb.npy) to check quantization.

Usage: <venv>/bin/python -I eval_search.py <site_dir> <topics.txt> <out_dir>
"""
import csv, json, math, re, sys
from collections import Counter
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

site, topics_f, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
s = (site / 'papers.js').read_text(); PP = json.loads(s[s.index('=') + 1:].strip().rstrip(';'))
s = (site / 'data.js').read_text(); D = json.loads(s[s.index('=') + 1:].strip().rstrip(';'))
CODES = [a['code'] for a in D['meta']['areas']]
rows, n, dim = PP['rows'], PP['n'], PP['dim']
b = (site / 'papers.bin').read_bytes()
S = np.frombuffer(b[:4 * n], '<f4'); V = np.frombuffer(b[4 * n:], np.int8).reshape(n, dim).astype(np.float32)
ALL = json.loads((site / 'neurips.json').read_text())['papers']
AB = {p['id']: p['abstract'] for p in ALL}
FULL = np.load(site / 'work' / 'emb.npy'); IDX = {p['id']: i for i, p in enumerate(ALL)}
F = FULL[[IDX[r[3]] for r in rows]]

T = []
for line in topics_f.read_text().splitlines():
    if not line.strip() or line.startswith('#'): continue
    parts = line.split('|')
    T.append((parts[0].split(','), '|'.join(parts[1:-1]), parts[-1].strip()))
print(len(T), 'topics')

model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
qtext = [('Represent this sentence for searching relevant passages: ' + t if len(t.split()) <= 24 else t) for _, _, t in T]
Q = model.encode(qtext, normalize_embeddings=True, batch_size=64)
SIM = (Q @ V.T) * S[None, :]                       # what the browser computes
SIMF = Q @ F.T                                      # full precision

# keyword fallback (title idf, as lexicalScores in index.html)
norm = lambda x: re.sub(r'[^a-z0-9]+', ' ', x.lower().replace('&', ' and ')).strip()
df = Counter(w for r in rows for w in set(norm(r[0]).split()))
idf = {w: math.log(n / c) for w, c in df.items()}
def lex(t):
    qw = {w for w in norm(t).split() if len(w) > 2}
    return np.array([sum(idf.get(w, 0) for w in qw if w in set(norm(r[0]).split())) for r in rows])

K = 10
hub = Counter()
res = []
for qi, (exp, rx, t) in enumerate(T):
    sims = SIM[qi]; top = np.argsort(-sims)[:K]
    topf = set(np.argsort(-SIMF[qi])[:K])
    rgx = re.compile(rx, re.I)
    txt = [rows[i][0] + ' ' + AB.get(rows[i][3], '') for i in top]
    rel = [bool(rgx.search(x)) for x in txt]
    area_hit = [CODES[rows[i][2]] in exp for i in top]
    corpus_hits = sum(1 for r in rows if rgx.search(r[0] + ' ' + AB.get(r[3], '')))
    lx = lex(t)
    for i in top: hub[i] += 1
    res.append({
        'topic': t, 'expected': ','.join(exp), 'top1_sim': round(float(sims[top[0]]), 3), 'sim10': round(float(sims[top[-1]]), 3),
        'term_hit@1': int(rel[0]), 'term_hits@5': sum(rel[:5]), 'term_hits@10': sum(rel),
        'area_hits@10': sum(area_hit), 'corpus_matches': corpus_hits,
        'int8_vs_fp32_overlap@10': len(set(top) & topf), 'fallback_results': int((lx > 0).sum()),
        'top3': ' || '.join(rows[i][0][:80] for i in top[:3]),
    })

with open(out / 'results.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(res[0])); w.writeheader(); w.writerows(res)

N = len(res)
answerable = [r for r in res if r['corpus_matches'] >= 3]   # the index has >= 3 papers mentioning the topic's key terms
summ = {
    'topics': N,
    'answerable (>=3 papers in index mention the key terms)': len(answerable),
    'answerable with key term in top-1': sum(r['term_hit@1'] for r in answerable),
    'answerable with key term in >=1 of top-5': sum(1 for r in answerable if r['term_hits@5'] >= 1),
    'answerable with key term in >=3 of top-5': sum(1 for r in answerable if r['term_hits@5'] >= 3),
    'mean precision@10 on key term (answerable)': round(sum(r['term_hits@10'] for r in answerable) / (10 * max(1, len(answerable))), 3),
    'expected area in top-10 (>=1)': sum(1 for r in res if r['area_hits@10'] >= 1),
    'mean expected-area share @10': round(sum(r['area_hits@10'] for r in res) / (10 * N), 3),
    'int8 vs fp32 top-10 overlap (mean of 10)': round(sum(r['int8_vs_fp32_overlap@10'] for r in res) / N, 2),
    'int8 vs fp32 identical top-10 sets': sum(1 for r in res if r['int8_vs_fp32_overlap@10'] == 10),
    'keyword fallback returns nothing': sum(1 for r in res if r['fallback_results'] == 0),
    'top1 similarity min/median/max': [round(float(x), 3) for x in np.percentile([r['top1_sim'] for r in res], [0, 50, 100])],
    'hub papers (in top-10 of >= 8% of topics)': [(rows[i][0][:70], c) for i, c in hub.most_common(15) if c >= 0.08 * N],
    'distinct papers ever in a top-10': len(hub), 'index size': n,
}
(out / 'summary.json').write_text(json.dumps(summ, indent=1, ensure_ascii=False))
print(json.dumps(summ, indent=1, ensure_ascii=False))
weak = sorted(answerable, key=lambda r: (r['term_hits@5'], r['top1_sim']))[:25]
print('\nWEAKEST answerable topics:')
for r in weak: print(f"  {r['term_hits@5']}/5 sim {r['top1_sim']} matches {r['corpus_matches']:>3} | {r['topic']} -> {r['top3'][:160]}")
print('\nUNANSWERABLE (key terms in <3 papers of the index):')
print('  ' + '; '.join(r['topic'] for r in res if r['corpus_matches'] < 3))
