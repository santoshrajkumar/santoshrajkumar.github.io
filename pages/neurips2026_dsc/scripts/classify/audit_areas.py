"""Step 7: cross-tabulate tiers against the unofficial research-area clusters (the only area label public for 2026).

Usage: python3 -I audit_areas.py <neurips.json> <work_dir>
Prints the tier x area table, the inclusion rate per area, and writes work_dir/audit_queue.json with
(a) core/adjacent papers filed under areas unrelated to control (possible false friends) and
(b) a sample of 'out' papers filed under RL / Robotics / Time series (possible misses), for a re-read.
"""
import json, random, sys
from collections import Counter, defaultdict
from pathlib import Path

src, work = Path(sys.argv[1]), Path(sys.argv[2])
P = {p['id']: p for p in json.load(src.open())['papers']}
L = json.load((work / 'final_labels.json').open()) if (work / 'final_labels.json').exists() else json.load((work / 'labels.json').open())
plan = json.load((work / 'batch_plan.json').open())
areas = sorted({p['jarea'] for p in P.values()})
tab = defaultdict(Counter)
for i, l in L.items(): tab[P[i]['jarea']][l['tier']] += 1
tot = Counter(p['jarea'] for p in P.values())
print(f"{'area':<48}{'core':>6}{'adj':>6}{'out':>6}{'unlab':>7}{'in-rate':>9}")
for a in sorted(areas, key=lambda a: -(tab[a]['core'] + tab[a]['adjacent'])):
    c, d, o = tab[a]['core'], tab[a]['adjacent'], tab[a]['out']
    print(f"{a:<48}{c:>6}{d:>6}{o:>6}{tot[a] - c - d - o:>7}{(c + d) / tot[a]:>9.1%}")
UNRELATED = {'3D, Image & Video', 'Vision-Language & Multimodal', 'LLM Agents', 'LLM fine-tuning & post-training', 'LLM reasoning & test-time scaling',
             'Efficient LLM inference', 'Long context & sparse attention', 'LLM behavior, bias & evaluation', 'Diffusion & non-autoregressive LMs', 'Graph Learning'}
RELEVANT = {'Reinforcement Learning', 'Robotics & Embodied AI', 'Time Series, Causality & Tabular', 'Theory & Optimization', 'AI for Science & Neuro'}
fp = [{'id': i, 'title': P[i]['title'], 'area': P[i]['jarea'], 'label': l, 'check': 'possible false positive'} for i, l in L.items() if l['tier'] != 'out' and P[i]['jarea'] in UNRELATED]
random.seed(11)
miss_pool = [i for i, l in L.items() if l['tier'] == 'out' and P[i]['jarea'] in RELEVANT and i in set(plan['candidates'])]
fn = [{'id': i, 'title': P[i]['title'], 'abstract': P[i]['abstract'], 'area': P[i]['jarea'], 'label': L[i], 'check': 'possible miss'} for i in random.sample(miss_pool, min(60, len(miss_pool)))]
for x in fp: x['abstract'] = P[x['id']]['abstract']
json.dump(fp + fn, (work / 'audit_queue.json').open('w'), ensure_ascii=False, indent=0)
print(f'\npossible false positives (in, but unrelated area): {len(fp)} | sampled possible misses (out, relevant area): {len(fn)} of {len(miss_pool)} -> audit_queue.json')
