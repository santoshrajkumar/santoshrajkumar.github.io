"""Compare OpenAlex per-author affiliations with hand-read arXiv bylines (work/oa_audit). Usage: python3 -I audit_openalex.py"""
import json, sys
from collections import Counter
sys.argv = ['x', 'corl2026_papers.json', 'raw', 'work/emb.npy', '.']
g = {'__file__': 'scripts/build.py', '__name__': 'b'}
exec(open('scripts/build.py').read().split('# OpenReview author ids')[0], g)
R = lambda xs: set(g['res_list'](xs))
P = {p['id']: p for p in json.load(open('corl2026_papers.json'))['papers']}
L = json.load(open('work/oa_audit/labels_00.json'))
c = Counter(); bad_papers = Counter(); ex = []
for r in L:
    oa = {a['name']: a for a in P[r['id']]['author_affiliations'] if a.get('source') == 'openalex'}
    for a in r['authors']:
        if a['name'] not in oa or a['basis'] not in ('explicit', 'single', 'group') or not a['institutions']: continue
        o, b = R(oa[a['name']]['institutions']), R(a['institutions'])
        c['compared'] += 1
        if o == b: c['identical'] += 1
        elif o & b: c['overlap'] += 1
        else:
            c['disjoint'] += 1; bad_papers[r['id']] += 1
            ex.append((r['id'], a['name'], sorted(o), sorted(b)))
        if o - b: c['openalex has an institution the byline does not'] += 1
        if b - o: c['byline has an institution openalex misses'] += 1
n = c['compared']
for k, v in c.items(): print(f'{k:50} {v:4}  ({100 * v / n:.1f}%)')
print('papers with >=1 disjoint author:', len(bad_papers), 'of', len(L), '| disjoint per bad paper:', sorted(bad_papers.values(), reverse=True))
for e in ex[:25]: print('  ', e[0], e[1], '| OA', e[2][:3], '| byline', e[3][:3])
json.dump(ex, open('work/oa_audit/disjoint.json', 'w'), indent=1, ensure_ascii=False)
