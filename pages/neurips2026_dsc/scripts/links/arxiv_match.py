"""Find NeurIPS 2026 DSC papers on arXiv (official API, 5 s between requests) and pull GitHub/GitLab links from
the arXiv abstract and comments. Cached and resumable.

Usage: python3 -I arxiv_match.py <neurips.json> <cache.json> <ids.txt> [limit]
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

src, cache_path, ids_path = sys.argv[1], sys.argv[2], sys.argv[3]
limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
P = {p['id']: p for p in json.load(open(src))['papers']}
ids = [l.strip() for l in open(ids_path) if l.strip()]
try: cache = json.load(open(cache_path))
except FileNotFoundError: cache = {}
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
STOP = set('a an the of for and in on with via to by from under using towards toward is are at as its into over'.split())

def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
def surname(name): return norm(name).split(' ')[-1] if name else ''

def query(title):
    words = [w for w in norm(title).split() if w not in STOP and len(w) > 1][:12]
    q = ' AND '.join(f'ti:{w}' for w in words)
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode({'search_query': q, 'max_results': 8})
    req = urllib.request.Request(url, headers={'User-Agent': 'neurips2026-dsc-explorer-link-check/1.0'})
    for attempt in range(9):
        try: return urllib.request.urlopen(req, timeout=40).read()
        except Exception as e:
            wait = min(900, 60 * 2 ** attempt); print(f'arXiv said {e}; waiting {wait} s', flush=True); time.sleep(wait)
    raise RuntimeError('arXiv API unreachable after long back-off')

CODE = re.compile(r'https?://(?:www\.)?(?:github\.com|gitlab\.com|gitlab\.[a-z0-9.-]+)/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+', re.I)
done = 0
for key in ids:
    p = P.get(key)
    if not p or key in cache or len(norm(p['title'])) < 15: continue
    if limit is not None and done >= limit: break
    xml = query(p['title']); time.sleep(5); done += 1
    root = ET.fromstring(xml); best = None
    ours = {surname(a[0]) for a in p['authors']}
    for e in root.findall('a:entry', NS):
        t = ' '.join(e.find('a:title', NS).text.split())
        sim = SequenceMatcher(None, norm(p['title']), norm(t)).ratio()
        theirs = {norm(a.find('a:name', NS).text).split(' ')[-1] for a in e.findall('a:author', NS)}
        shared = len(ours & theirs)
        if sim >= 0.9 and shared >= 1 and (best is None or sim > best['sim']):
            aid = e.find('a:id', NS).text.rsplit('/abs/', 1)[-1]
            com = e.find('x:comment', NS)
            text = ' '.join(filter(None, [e.find('a:summary', NS).text, com.text if com is not None else '']))
            best = {'arxiv': re.sub(r'v\d+$', '', aid), 'title': t, 'sim': round(sim, 3), 'shared_authors': shared,
                    'code': sorted({u.rstrip('.,);') for u in CODE.findall(text)})}
    cache[key] = best or {}
    if done % 20 == 0:
        json.dump(cache, open(cache_path, 'w')); print(done, 'queried,', sum(1 for v in cache.values() if v), 'found', flush=True)
json.dump(cache, open(cache_path, 'w'))
found = [v for v in cache.values() if v]
print('total checked', len(cache), 'arXiv found', len(found), 'with code', sum(1 for v in found if v['code']))
