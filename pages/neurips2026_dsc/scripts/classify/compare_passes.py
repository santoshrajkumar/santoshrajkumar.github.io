"""Compare the independent second pass with the first pass on the validation sample; write the disagreement queue.

Usage: python3 -I compare_passes.py <neurips.json> <work_dir>
Reads work_dir/validate/key.json and work_dir/validate/labels_v*.json; writes work_dir/validate/disagreements.json
(each with both labels, for a third adjudicating read) and prints agreement, Cohen's kappa and per-stratum results.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
P = {p['id']: p for p in json.load(src.open())['papers']}
vd = work / 'validate'
key = json.load((vd / 'key.json').open())
p2 = {}
for f in sorted(vd.glob('labels_v*.json')):
    for x in json.load(f.open()): p2[str(x['id'])] = x
both = [i for i in key if i in p2]
print('validation papers', len(key), 'with second-pass label', len(both))
tiers = ['core', 'adjacent', 'out']
M = Counter((key[i]['pass1']['tier'], p2[i]['tier']) for i in both)
print('rows = pass 1, cols = pass 2'); print('            ' + ''.join(f'{t:>10}' for t in tiers))
for a in tiers: print(f'{a:>10}  ' + ''.join(f'{M[(a, b)]:>10}' for b in tiers))
n = len(both); agree = sum(M[(t, t)] for t in tiers)
pe = sum((sum(M[(t, b)] for b in tiers) / n) * (sum(M[(a, t)] for a in tiers) / n) for t in tiers)
po = agree / n
print(f'tier agreement {po:.3f}  kappa {(po - pe) / (1 - pe):.3f}')
inout = lambda t: 'in' if t != 'out' else 'out'
io = Counter((inout(key[i]['pass1']['tier']), inout(p2[i]['tier'])) for i in both)
print('in/out agreement', round((io[('in', 'in')] + io[('out', 'out')]) / n, 3), dict(io))
sub_agree = [i for i in both if key[i]['pass1']['tier'] != 'out' and p2[i]['tier'] != 'out']
print('subcategory agreement among papers both passes kept:', round(sum(key[i]['pass1']['sub'] == p2[i]['sub'] for i in sub_agree) / max(1, len(sub_agree)), 3), 'of', len(sub_agree))
per = defaultdict(Counter)
for i in both: per[key[i]['stratum']][(key[i]['pass1']['tier'], p2[i]['tier'])] += 1
for s, c in per.items(): print(f'  stratum {s}:', dict(c))
dis = [{'id': i, 'title': P[i]['title'], 'abstract': P[i]['abstract'], 'stratum': key[i]['stratum'], 'pass1': key[i]['pass1'], 'pass2': {'tier': p2[i]['tier'], 'sub': p2[i].get('sub'), 'reason': p2[i].get('reason', '')}}
       for i in both if key[i]['pass1']['tier'] != p2[i]['tier']]
json.dump(dis, (vd / 'disagreements.json').open('w'), ensure_ascii=False, indent=0)
print('disagreements written:', len(dis))
