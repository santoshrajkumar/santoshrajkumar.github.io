"""Validate a DSC label file against its batch. Usage: python3 -I check_dsc.py <batch.json> <labels.json>"""
import json, sys
from collections import Counter
B = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2]))
CORE, ADJ = {'OC', 'ID', 'SF', 'ES', 'LC', 'RC'}, {'MB', 'NO', 'TD', 'TS', 'SD'}
err, ids = [], [b['id'] for b in B]
if [l.get('id') for l in L] != ids: err.append('ids missing, extra or out of order')
for l in L:
    t, s, r = l.get('tier'), l.get('sub'), l.get('reason')
    if t == 'core' and s not in CORE: err.append(f"{l.get('id')}: core needs one of {sorted(CORE)}, got {s}")
    elif t == 'adjacent' and s not in ADJ: err.append(f"{l.get('id')}: adjacent needs one of {sorted(ADJ)}, got {s}")
    elif t == 'out' and s is not None: err.append(f"{l.get('id')}: out needs sub null")
    elif t not in ('core', 'adjacent', 'out'): err.append(f"{l.get('id')}: bad tier {t}")
    if not r or len(r.split()) > 25: err.append(f"{l.get('id')}: reason missing or > 25 words")
print('OK' if not err else '\n'.join(err[:40]))
print(Counter(l.get('tier') for l in L), Counter(l.get('sub') for l in L if l.get('sub')))
