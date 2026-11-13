"""Build LLM-classification batches from the recall stage.

Usage: python3 -I make_batches.py <neurips.json> <work_dir> [batch_size] [n_out_sample]
Takes every recall candidate plus a random sample of non-candidates (to estimate recall of the lexicon/embedding
stage) and writes work_dir/batches/batch_XX.json for the LLM pass. Deterministic (seeded).
"""
import json, random, sys
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
bs = int(sys.argv[3]) if len(sys.argv) > 3 else 80
n_out = int(sys.argv[4]) if len(sys.argv) > 4 else 300
P = json.load(src.open())['papers']
R = json.load((work / 'recall.json').open())['rows']
cand = [p for p in P if R[p['id']]['candidate']]
rest = [p for p in P if not R[p['id']]['candidate']]
random.seed(2026)
sample = random.sample(rest, min(n_out, len(rest)))
todo = cand + sample
random.shuffle(todo)
bdir = work / 'batches'; bdir.mkdir(parents=True, exist_ok=True)
for f in bdir.glob('batch_*.json'): f.unlink()
for i in range(0, len(todo), bs):
    chunk = todo[i:i + bs]
    json.dump([{'id': p['id'], 'title': p['title'], 'abstract': p['abstract']} for p in chunk],
              (bdir / f'batch_{i // bs:02d}.json').open('w'), ensure_ascii=False, indent=0)
json.dump({'candidates': [p['id'] for p in cand], 'out_sample': [p['id'] for p in sample]}, (work / 'batch_plan.json').open('w'))
print('candidates', len(cand), '| out-sample', len(sample), '| batches', (len(todo) + bs - 1) // bs, 'of', bs)
