"""Semantic Scholar fallback for the author prior (used when the OpenAlex daily budget is exhausted).

Usage: python3 -I author_prior_s2.py <neurips.json> <work_dir> <ids.txt> [max_authors]
For each author of the listed papers not already in work_dir/author_prior.json's cache, searches Semantic Scholar by
name, picks the candidate whose affiliations overlap the NeurIPS institution string (or the only candidate), and
computes the share of their papers in control venues (CDC, ACC, L4DC, TAC, Automatica, CSL, IFAC, ECC, RA-L, ICRA, IROS).
Unauthenticated: ~1 request/s with exponential back-off on 429. Merges into work_dir/author_prior.json.
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error
from pathlib import Path

src, work, ids_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
max_authors = int(sys.argv[4]) if len(sys.argv) > 4 else 400
P = {p['id']: p for p in json.load(src.open())['papers']}
ids = [l.strip() for l in ids_path.read_text().splitlines() if l.strip()]
cache_path = work / 's2_cache.json'
cache = json.load(cache_path.open()) if cache_path.exists() else {}
oa = json.load((work / 'openalex_cache.json').open()) if (work / 'openalex_cache.json').exists() else {}
VEN = re.compile(r'conference on decision and control|\bcdc\b|american control conference|\bacc\b|learning for dynamics|l4dc|transactions on automatic control|automatica|control systems letters|ifac|european control conference|robotics and automation letters|ra-l|\bicra\b|\biros\b|control', re.I)
UA = {'User-Agent': 'neurips2026-dsc-explorer/1.0'}

def ascii_(s): s = unicodedata.normalize('NFKD', s); return ''.join(c for c in s if not unicodedata.combining(c)).lower()
def toks(s): return set(re.findall(r'[a-z]{3,}', ascii_(s))) - {'university', 'institute', 'technology', 'the', 'and', 'college', 'school', 'department', 'research', 'national', 'laboratory', 'lab', 'inc'}

def get(url):
    for attempt in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40); time.sleep(1.1)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(min(120, 5 * 2 ** attempt)); continue
            if e.code == 404: return None
            time.sleep(5)
        except Exception: time.sleep(5)
    return None

n = 0
for pid in ids:
    for name, inst, _ in P[pid]['authors']:
        key = f'{name}|{inst}'
        if key in cache or oa.get(key): continue
        if n >= max_authors: break
        n += 1
        j = get('https://api.semanticscholar.org/graph/v1/author/search?' + urllib.parse.urlencode({'query': name, 'fields': 'name,affiliations,paperCount', 'limit': 5}))
        res = (j or {}).get('data') or []
        want = toks(inst); best = None
        for a in res:
            ov = len(want & set().union(*(toks(x) for x in a.get('affiliations') or [])) ) if a.get('affiliations') else 0
            if ov > 0 and (best is None or ov > best[0]): best = (ov, a)
        if best is None and len(res) == 1: best = (0, res[0])
        if best is None: cache[key] = None; continue
        a = best[1]
        pj = get(f"https://api.semanticscholar.org/graph/v1/author/{a['authorId']}/papers?fields=venue,year&limit=200")
        papers = (pj or {}).get('data') or []
        ctrl = sum(1 for x in papers if VEN.search(x.get('venue') or ''))
        cache[key] = {'id': a['authorId'], 'name': a['name'], 'works': a.get('paperCount', 0), 'control_share': round(ctrl / max(1, len(papers)), 3), 'matched_inst': best[0] > 0, 'source': 's2'}
        if n % 10 == 0: json.dump(cache, cache_path.open('w')); print(n, 'authors', flush=True)
json.dump(cache, cache_path.open('w'))
prior = json.load((work / 'author_prior.json').open()) if (work / 'author_prior.json').exists() else {}
for pid in ids:
    vals = [oa.get(f'{a[0]}|{a[1]}') or cache.get(f'{a[0]}|{a[1]}') for a in P[pid]['authors']]
    vals = [v for v in vals if v]
    if vals: prior[pid] = {'mean': round(sum(v['control_share'] for v in vals) / len(vals), 3), 'max': max(v['control_share'] for v in vals), 'n_matched': len(vals), 'n_authors': len(P[pid]['authors'])}
json.dump(prior, (work / 'author_prior.json').open('w'), indent=0)
print('s2 authors looked up', n, '| papers with prior', len(prior))
