"""Stratified validation sample for an independent second LLM pass (step 6 of the method).

Usage: python3 -I validate_sample.py <neurips.json> <work_dir> [n_core n_adj n_out_cand n_out_rest]
Draws papers from the first-pass labels: core, adjacent, out-but-candidate, and out-and-never-candidate (from the
300 out-sample), writes them WITHOUT labels to work_dir/validate/batch_vXX.json (60 per batch) and the key to
work_dir/validate/key.json.
"""
import json, random, sys
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
n = [int(x) for x in sys.argv[3:7]] if len(sys.argv) >= 7 else [110, 90, 70, 30]
P = {p['id']: p for p in json.load(src.open())['papers']}
L = json.load((work / 'labels.json').open())
plan = json.load((work / 'batch_plan.json').open())
cand, outs = set(plan['candidates']), set(plan['out_sample'])
random.seed(99)
strata = {
    'core': [i for i, l in L.items() if l['tier'] == 'core'],
    'adjacent': [i for i, l in L.items() if l['tier'] == 'adjacent'],
    'out_candidate': [i for i, l in L.items() if l['tier'] == 'out' and i in cand],
    'out_rest': [i for i, l in L.items() if l['tier'] == 'out' and i in outs],
}
pick = []
for (k, ids), m in zip(strata.items(), n):
    s = random.sample(ids, min(m, len(ids))); pick += [(i, k) for i in s]
random.shuffle(pick)
vd = work / 'validate'; vd.mkdir(exist_ok=True)
for f in vd.glob('batch_v*.json'): f.unlink()
for b in range(0, len(pick), 60):
    chunk = pick[b:b + 60]
    json.dump([{'id': i, 'title': P[i]['title'], 'abstract': P[i]['abstract']} for i, _ in chunk], (vd / f'batch_v{b // 60:02d}.json').open('w'), ensure_ascii=False, indent=0)
json.dump({i: {'stratum': k, 'pass1': L[i]} for i, k in pick}, (vd / 'key.json').open('w'), indent=0)
print({k: len(v) for k, v in strata.items()}, '| sampled', len(pick), 'in', (len(pick) + 59) // 60, 'batches')
