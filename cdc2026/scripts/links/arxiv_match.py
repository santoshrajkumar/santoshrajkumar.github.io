"""Find each CDC 2026 paper on arXiv (official API, 3 s between requests) and pull GitHub/GitLab links
from the arXiv abstract and comments. Results are cached so the run can resume.

Usage: python3 -I arxiv_match.py <cdc.json> <cache.json> [limit]
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

src, cache_path = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
D = json.load(open(src))
try:
    cache = json.load(open(cache_path))
except FileNotFoundError:
    cache = {}
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
STOP = set('a an the of for and in on with via to by from under using towards toward is are at as its into over'.split())

def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'\(I\)\s*$', '', s)           # CDC marks invited papers with (I)
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

def surname(name):                            # program names are "Last, First"
    return norm(name.split(',')[0]).split(' ')[-1] if name else ''

def query(title):
    words = [w for w in norm(title).split() if w not in STOP and len(w) > 1][:12]
    q = ' AND '.join(f'ti:{w}' for w in words)
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode({'search_query': q, 'max_results': 8})
    req = urllib.request.Request(url, headers={'User-Agent': 'cdc2026-explorer-link-check/1.0'})
    for attempt in range(9):
        try:
            return urllib.request.urlopen(req, timeout=40).read()
        except Exception as e:                 # 429/503: arXiv asks us to slow down; back off 1 to 15 min
            wait = min(900, 60 * 2 ** attempt)
            print(f'arXiv said {e}; waiting {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('arXiv API unreachable after long back-off')

CODE = re.compile(r'https?://(?:www\.)?(?:github\.com|gitlab\.com|gitlab\.[a-z0-9.-]+)/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+', re.I)

done = 0
for p in D['papers']:
    if not p['abstract'] or len(norm(p['title'])) < 15:
        continue                                # plenaries/workshops without abstracts
    key = p['id']
    if key in cache:
        continue
    if limit is not None and done >= limit:
        break
    xml = query(p['title']); time.sleep(5); done += 1
    root = ET.fromstring(xml)
    best = None
    our_names = {surname(a[0]) for a in p['authors']}
    for e in root.findall('a:entry', NS):
        t = ' '.join(e.find('a:title', NS).text.split())
        sim = SequenceMatcher(None, norm(p['title']), norm(t)).ratio()
        names = [a.find('a:name', NS).text for a in e.findall('a:author', NS)]
        theirs = {norm(n).split(' ')[-1] for n in names}
        shared = len(our_names & theirs)
        if sim >= 0.9 and shared >= 1 and (best is None or sim > best['sim']):
            aid = e.find('a:id', NS).text.rsplit('/abs/', 1)[-1]
            text = ' '.join(filter(None, [e.find('a:summary', NS).text, (e.find('x:comment', NS).text if e.find('x:comment', NS) is not None else '')]))
            code = sorted({u.rstrip('.,);') for u in CODE.findall(text)})
            best = {'arxiv': re.sub(r'v\d+$', '', aid), 'title': t, 'sim': round(sim, 3), 'shared_authors': shared, 'code': code}
    cache[key] = best or {}
    if done % 20 == 0:
        json.dump(cache, open(cache_path, 'w'))
        print(done, 'queried,', sum(1 for v in cache.values() if v), 'found', flush=True)
json.dump(cache, open(cache_path, 'w'))
found = [v for v in cache.values() if v]
print('total checked', len(cache), 'arXiv found', len(found), 'with code', sum(1 for v in found if v['code']))
