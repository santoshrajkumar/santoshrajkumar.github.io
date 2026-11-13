"""Batches for the papers not covered by the recall stage, so that every main-track paper gets an LLM label.

Usage: python3 -I make_rest_batches.py <neurips.json> <work_dir> [batch_size]
Appends batch files after the existing ones and records them in work_dir/batch_plan.json under "rest".
"""
import json, random, sys
from pathlib import Path
src, work = Path(sys.argv[1]), Path(sys.argv[2]); bs = int(sys.argv[3]) if len(sys.argv) > 3 else 80
P = json.load(src.open())['papers']
plan = json.load((work / 'batch_plan.json').open())
done = set(plan['candidates']) | set(plan['out_sample'])
rest = [p for p in P if p['id'] not in done]
random.seed(7); random.shuffle(rest)
bdir = work / 'batches'; start = len(list(bdir.glob('batch_*.json')))
names = []
for k, i in enumerate(range(0, len(rest), bs)):
    name = f'batch_{start + k:02d}.json'
    json.dump([{'id': p['id'], 'title': p['title'], 'abstract': p['abstract']} for p in rest[i:i + bs]], (bdir / name).open('w'), ensure_ascii=False, indent=0)
    names.append(name)
plan['rest'] = [p['id'] for p in rest]; plan['rest_batches'] = names
json.dump(plan, (work / 'batch_plan.json').open('w'))
print('rest papers', len(rest), '| batches', names[0], '..', names[-1])
