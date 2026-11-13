"""Produce work_dir/final_labels.json from the first pass, adjudicated disagreements, manual overrides and the
author prior (rescue of borderline 'out' papers only).

Usage: python3 -I finalize_labels.py <neurips.json> <work_dir>
Inputs (all in work_dir): labels.json (pass 1), validate/adjudicated.json (optional: {id: {tier, sub, reason}}),
overrides.json (optional: same shape, hand decisions), author_prior.json (optional), recall.json.
A paper labelled out in pass 1 is *flagged* for re-reading (work_dir/rescue_queue.json) when its lexicon score is
strong and its authors' OpenAlex control share is high; nothing is relabelled automatically by the prior.
"""
import json, sys
from collections import Counter
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
P = {p['id']: p for p in json.load(src.open())['papers']}
L = json.load((work / 'labels.json').open())
R = json.load((work / 'recall.json').open())['rows']
adj = json.load((work / 'validate' / 'adjudicated.json').open()) if (work / 'validate' / 'adjudicated.json').exists() else {}
ovr = json.load((work / 'overrides.json').open()) if (work / 'overrides.json').exists() else {}
prior = json.load((work / 'author_prior.json').open()) if (work / 'author_prior.json').exists() else {}
final = {}
for i, l in L.items(): final[i] = dict(l, source='pass1')
for i, l in adj.items(): final[i] = dict(l, source='adjudicated')
for i, l in ovr.items(): final[i] = dict(l, source='override')
queue = [{'id': i, 'title': P[i]['title'], 'lex': R[i]['lex'], 'prior': prior[i], 'label': final[i]}
         for i in final if final[i]['tier'] == 'out' and i in prior and R[i]['lex'] >= 4 and prior[i]['mean'] >= 0.25 and i not in ovr and i not in adj]
json.dump(queue, (work / 'rescue_queue.json').open('w'), ensure_ascii=False, indent=0)
json.dump(final, (work / 'final_labels.json').open('w'), ensure_ascii=False, indent=0)
c = Counter(l['tier'] for l in final.values())
print('final labels', len(final), dict(c), '| sources', dict(Counter(l['source'] for l in final.values())))
print('core by sub', dict(Counter(l['sub'] for l in final.values() if l['tier'] == 'core')))
print('adjacent by sub', dict(Counter(l['sub'] for l in final.values() if l['tier'] == 'adjacent')))
print('rescue queue (out, strong lexicon, control-heavy authors):', len(queue))
