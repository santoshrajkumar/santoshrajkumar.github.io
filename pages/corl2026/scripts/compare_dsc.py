"""Agreement between the first DSC pass (work/dsc/labels) and the blind second pass (work/dsc/validate/labels)."""
import json, glob
from collections import Counter
A, B = {}, {}
for f in sorted(glob.glob('work/dsc/labels/batch_*.json')):
    for l in json.load(open(f)): A[l['id']] = l
for f in sorted(glob.glob('work/dsc/validate/labels/batch_*.json')):
    for l in json.load(open(f)): B[l['id']] = l
ids = list(B); n = len(ids)
T = ['core', 'adjacent', 'out']
agree = sum(A[i]['tier'] == B[i]['tier'] for i in ids)
po = agree / n
pa = Counter(A[i]['tier'] for i in ids); pb = Counter(B[i]['tier'] for i in ids)
pe = sum(pa[t] * pb[t] for t in T) / n / n
inout = sum((A[i]['tier'] != 'out') == (B[i]['tier'] != 'out') for i in ids)
both_in = [i for i in ids if A[i]['tier'] != 'out' and B[i]['tier'] != 'out']
sub = sum(A[i]['sub'] == B[i]['sub'] for i in both_in)
print(f"sample {n}: tier agreement {po:.1%}, Cohen kappa {(po - pe) / (1 - pe):.2f}, in/out agreement {inout / n:.1%}, subcategory agreement (both in) {sub / len(both_in):.1%}")
print('confusion (first pass rows -> second pass cols):')
for t in T: print(f"  {t:9}", [sum(1 for i in ids if A[i]['tier'] == t and B[i]['tier'] == u) for u in T])
json.dump([{'id': i, 'first': A[i], 'second': B[i]} for i in ids if A[i]['tier'] != B[i]['tier']], open('work/dsc/validate/disagreements.json', 'w'), indent=1, ensure_ascii=False)
print('disagreements', sum(A[i]['tier'] != B[i]['tier'] for i in ids))
