"""Validate work/affil_labels/batch_NN.json against work/affil_batches/batch_NN.json.
Usage: python3 -I check_labels.py <batch_NN.json> <labels_NN.json>"""
import json, sys
B = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2]))
BASES = {'explicit', 'group', 'single', 'ambiguous', 'none'}
lab = {r['id']: r for r in L}
err = []
for it in B:
    r = lab.get(it['id'])
    if not r: err.append(f"missing paper {it['id']}"); continue
    names = [a.get('name') for a in r.get('authors', [])]
    if names != it['missing_authors']: err.append(f"{it['id']}: author names/order differ from missing_authors")
    for a in r.get('authors', []):
        if a.get('basis') not in BASES: err.append(f"{it['id']} {a.get('name')}: bad basis {a.get('basis')}")
        if not isinstance(a.get('institutions'), list): err.append(f"{it['id']} {a.get('name')}: institutions not a list")
        if a.get('basis') in ('explicit', 'group', 'single') and not a.get('institutions'): err.append(f"{it['id']} {a.get('name')}: basis {a.get('basis')} with no institutions")
extra = set(lab) - {it['id'] for it in B}
if extra: err.append(f"extra papers {sorted(extra)}")
print('OK' if not err else '\n'.join(err[:50]))
from collections import Counter
print(Counter(a['basis'] for r in L for a in r.get('authors', [])))
