"""Merge the LLM batch outputs into labels.json and print agreement with the recall stage.

Usage: python3 -I aggregate.py <neurips.json> <work_dir>
Reads work_dir/labels/batch_XX.json (lists of {id, tier, sub, reason}); writes work_dir/labels.json.
"""
import json, sys
from collections import Counter
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
P = {p['id']: p for p in json.load(src.open())['papers']}
R = json.load((work / 'recall.json').open())['rows']
plan = json.load((work / 'batch_plan.json').open())
VALID = {'core': {'OC', 'ID', 'SF', 'ES', 'LC', 'RC'}, 'adjacent': {'MB', 'NO', 'TD', 'TS', 'SD'}, 'out': {None, ''}}
labels, bad = {}, []
for f in sorted((work / 'labels').glob('batch_*.json')):
    for x in json.load(f.open()):
        pid = str(x.get('id')); tier = (x.get('tier') or '').lower(); sub = x.get('sub') or None
        if pid not in P or tier not in VALID or (tier != 'out' and sub not in VALID[tier]):
            bad.append((f.name, x)); continue
        labels[pid] = {'tier': tier, 'sub': sub if tier != 'out' else None, 'reason': x.get('reason', '')}
expected = set(plan['candidates']) | set(plan['out_sample'])
missing = expected - set(labels)
print('labelled', len(labels), '| invalid', len(bad), '| missing', len(missing))
for b in bad[:10]: print('  bad', b)
json.dump(labels, (work / 'labels.json').open('w'), ensure_ascii=False, indent=0)
c = Counter(l['tier'] for pid, l in labels.items() if pid in set(plan['candidates']))
s = Counter(l['tier'] for pid, l in labels.items() if pid in set(plan['out_sample']))
print('candidates:', dict(c)); print('out-sample (recall check):', dict(s))
print('subcategories:', Counter(l['sub'] for l in labels.values() if l['sub']))
