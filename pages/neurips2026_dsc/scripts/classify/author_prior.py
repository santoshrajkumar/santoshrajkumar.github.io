"""Author prior (tie-breaker only): share of each author's OpenAlex works in control-related topics.

Usage: python3 -I author_prior.py <neurips.json> <work_dir> <ids.txt> [max_requests]
For the papers listed in ids.txt (one id per line; the borderline set), looks up each author on OpenAlex by name,
disambiguates by institution overlap, and records the share of their topic counts whose subfield is
"Control and Systems Engineering" (or robotics / mechanical engineering). Cached in work_dir/openalex_cache.json;
the free OpenAlex budget is about 1,000 records per day per IP, so the script stops at max_requests.
Caveat: name matching, not profile-ID matching; used only to rescue borderline papers, never to exclude.
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path

src, work, ids_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
max_req = int(sys.argv[4]) if len(sys.argv) > 4 else 400
P = {p['id']: p for p in json.load(src.open())['papers']}
ids = [l.strip() for l in ids_path.read_text().splitlines() if l.strip()]
cache_path = work / 'openalex_cache.json'
cache = json.load(cache_path.open()) if cache_path.exists() else {}
CONTROL_SUB = {'Control and Systems Engineering', 'Mechanical Engineering', 'Aerospace Engineering', 'Automotive Engineering'}
UA = {'User-Agent': 'neurips2026-dsc-explorer/1.0'}

def ascii_(s):
    s = unicodedata.normalize('NFKD', s); return ''.join(c for c in s if not unicodedata.combining(c)).lower()
def toks(s): return set(re.findall(r'[a-z]{3,}', ascii_(s))) - {'university', 'institute', 'technology', 'the', 'and', 'college', 'school', 'department', 'research', 'national', 'laboratory', 'lab', 'inc'}

def lookup(name, inst):
    key = f'{name}|{inst}'
    if key in cache: return cache[key]
    url = 'https://api.openalex.org/authors?' + urllib.parse.urlencode({'filter': f'display_name.search:{name}', 'per-page': 4, 'select': 'id,display_name,works_count,last_known_institutions,affiliations,topics'})
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        remaining = int(r.headers.get('x-ratelimit-remaining', '0') or 0)
        res = json.loads(r.read()).get('results', [])
    except Exception as e:
        print('openalex error', e, flush=True); return None
    want = toks(inst)
    best, best_s = None, -1
    for a in res:
        affs = [i.get('display_name', '') for i in (a.get('last_known_institutions') or [])] + [x.get('institution', {}).get('display_name', '') for x in (a.get('affiliations') or [])]
        ov = len(want & set().union(*(toks(x) for x in affs))) if affs else 0
        s = ov * 10 + min(a.get('works_count', 0), 50) / 100
        if (ov > 0 or not want) and s > best_s: best, best_s = a, s
    if best is None and len(res) == 1: best = res[0]
    out = None
    if best:
        tot = sum(t['count'] for t in best.get('topics') or []) or 1
        ctrl = sum(t['count'] for t in best.get('topics') or [] if (t.get('subfield') or {}).get('display_name') in CONTROL_SUB)
        out = {'id': best['id'], 'name': best['display_name'], 'works': best.get('works_count', 0), 'control_share': round(ctrl / tot, 3), 'matched_inst': best_s >= 10}
    cache[key] = out
    return out, remaining

n_req = 0
for pid in ids:
    p = P[pid]
    for name, inst, _ in p['authors']:
        if f'{name}|{inst}' in cache: continue
        if n_req >= max_req: break
        res = lookup(name, inst); n_req += 1
        if res is None: time.sleep(5); continue
        _, remaining = res
        if remaining and remaining < 30: print('OpenAlex daily budget nearly exhausted; stopping', flush=True); n_req = max_req; break
        time.sleep(0.3)
    if n_req % 20 == 0: json.dump(cache, cache_path.open('w'))
json.dump(cache, cache_path.open('w'))
# per-paper prior: mean control share over matched authors, and max
prior = {}
for pid in ids:
    vals = [cache.get(f'{a[0]}|{a[1]}') for a in P[pid]['authors']]
    vals = [v for v in vals if v]
    if vals:
        prior[pid] = {'mean': round(sum(v['control_share'] for v in vals) / len(vals), 3), 'max': max(v['control_share'] for v in vals), 'n_matched': len(vals), 'n_authors': len(P[pid]['authors'])}
json.dump(prior, (work / 'author_prior.json').open('w'), indent=0)
print('requests', n_req, '| cached authors', len(cache), '| papers with prior', len(prior))
