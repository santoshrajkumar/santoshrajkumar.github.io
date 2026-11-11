"""Merge the arXiv and GitHub search caches into links.json for build.py.

A code repository is kept only if it looks like the paper's own code: not a paper-roundup or profile
repo, and its name shares a distinctive word with the paper title or its owner contains an author's surname.

Usage: python3 -I merge_links.py <lcss.json> <arxiv_cache.json> <github_cache.json> <out links.json>
"""
import json, re, sys, unicodedata

import os
def load(path):  # a cache that doesn't exist yet counts as empty
    return json.load(open(path)) if os.path.exists(path) and os.path.getsize(path) else {}
D = json.load(open(sys.argv[1])); ax = load(sys.argv[2]); gh = load(sys.argv[3])
P = {p['id']: p for p in D['papers']}
ROUNDUP = re.compile(r'awesome|daily|arxiv|weekly|digest|survey|paper[-_]?list|reading|enhansome|curated|collection', re.I)
GENERIC = set('''a an the of for and in on with via to by from under using toward towards is are at as into over
control controls controller learning data driven systems system model models based optimal robust nonlinear linear
analysis design approach method methods framework networks network dynamic dynamics problem problems time multi
agent agents new efficient stochastic distributed adaptive application applications code demo paper implementation
experiments repository repo official'''.split())

def ascii_(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()

def words(s):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)                    # CamelCase repo names
    return [w for w in re.split(r'[^a-z0-9]+', ascii_(s)) if len(w) >= 3 and w not in GENERIC]

def looks_like_paper_code(url, p, from_abstract=False):
    m = re.match(r'https?://[^/]+/([^/]+)/([^/#?]+)', url)
    if not m: return False
    owner, repo = m.group(1), re.sub(r'\.git$', '', m.group(2))
    if ROUNDUP.search(repo) or ROUNDUP.search(owner) or owner.lower() == repo.lower():
        return False
    if from_abstract:                                              # the authors linked it in their own abstract
        return True
    title = {w[:6] for w in words(p['title'])}
    if {w[:6] for w in words(repo)} & title:
        return True
    surnames = {ascii_(a['name'].split(',')[0]).replace(' ', '').replace('-', '') for a in p['authors']}
    return any(len(s) >= 4 and (s in ascii_(owner) or (len(s) >= 6 and s[:6] in ascii_(owner))) for s in surnames)

out, dropped = {}, []
for pid in set(ax) | set(gh):
    p = P.get(pid)
    if not p: continue
    a = ax.get(pid) or {}
    clean = lambda u: re.sub(r'\.git$', '', u.rstrip('/'))
    from_abs = [clean(u) for u in (a.get('code') or [])]
    cand = list(dict.fromkeys(from_abs + [clean(u) for u in ((gh.get(pid) or {}).get('repos') or [])]))
    code = [u for u in cand if looks_like_paper_code(u, p, from_abstract=u in from_abs)]
    dropped += [(p['id'], u) for u in cand if u not in code]
    if a.get('arxiv') or p['arxiv'] or code:
        out[pid] = {'arxiv': p['arxiv'] or a.get('arxiv') or '', 'code': code}
json.dump(out, open(sys.argv[4], 'w'), indent=1, sort_keys=True)
print('papers with arXiv', sum(1 for v in out.values() if v['arxiv']), '| with code', sum(1 for v in out.values() if v['code']),
      '| repos dropped', len(dropped))
if '-v' in sys.argv:
    for c, u in sorted(dropped): print('  dropped', c, u)
