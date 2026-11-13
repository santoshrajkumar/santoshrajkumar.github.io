"""Merge the arXiv and GitHub search caches into links.json for build.py.

A repository is kept only if it looks like the paper's own code: not a paper-roundup or profile repo, and either
linked from the authors' own arXiv abstract/comments, or its name shares a distinctive word with the title, or its
owner contains an author's surname.

Usage: python3 -I merge_links.py <neurips.json> <arxiv_cache.json> <github_cache.json> <out links.json>
"""
import json, re, sys, unicodedata
P = {p['id']: p for p in json.load(open(sys.argv[1]))['papers']}
ax = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
try: gh = json.load(open(sys.argv[3]))
except FileNotFoundError: gh = {}
ROUNDUP = re.compile(r'awesome|daily|arxiv|weekly|digest|survey|paper[-_]?list|reading|curated|collection|neurips|iclr|icml', re.I)
GENERIC = set('''a an the of for and in on with via to by from under using toward towards is are at as into over
control controls controller learning data driven systems system model models based optimal robust nonlinear linear
analysis design approach method methods framework networks network dynamic dynamics problem problems time multi
agent agents new efficient stochastic distributed adaptive application applications code demo paper implementation
experiments repository repo official neural deep'''.split())

def ascii_(s):
    s = unicodedata.normalize('NFKD', s); return ''.join(c for c in s if not unicodedata.combining(c)).lower()
def words(s):
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return [w for w in re.split(r'[^a-z0-9]+', ascii_(s)) if len(w) >= 3 and w not in GENERIC]
def looks_like_paper_code(url, p, from_abstract=False):
    m = re.match(r'https?://[^/]+/([^/]+)/([^/#?]+)', url)
    if not m: return False
    owner, repo = m.group(1), re.sub(r'\.git$', '', m.group(2))
    if ROUNDUP.search(repo) or ROUNDUP.search(owner) or owner.lower() == repo.lower(): return False
    if from_abstract: return True
    if {w[:6] for w in words(repo)} & {w[:6] for w in words(p['title'])}: return True
    surnames = {ascii_(a[0]).split(' ')[-1].replace('-', '') for a in p['authors'] if a[0]}
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
    dropped += [(pid, u) for u in cand if u not in code]
    if a.get('arxiv') or code: out[pid] = {'arxiv': a.get('arxiv') or '', 'code': code}
# hand-entered links (work/manual_links.json next to the output) override automatic ones
import os
man = os.path.join(os.path.dirname(os.path.abspath(sys.argv[4])), 'manual_links.json')
if os.path.exists(man):
    for pid, v in json.load(open(man)).items():
        cur = out.get(pid, {'arxiv': '', 'code': []})
        out[pid] = {'arxiv': v.get('arxiv') or cur['arxiv'], 'code': list(dict.fromkeys((v.get('code') or []) + cur['code']))}
json.dump(out, open(sys.argv[4], 'w'), indent=1, sort_keys=True)
print('papers with arXiv', sum(1 for v in out.values() if v['arxiv']), '| with code', sum(1 for v in out.values() if v['code']), '| repos dropped', len(dropped))
