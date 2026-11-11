"""Find TAC papers on arXiv (official API, one request every 5 s) and pull GitHub/GitLab links from the
arXiv abstract and comments. Cached per DOI, so the run can stop and resume and later runs only search new papers.

  1. Papers whose arXiv ID OpenAlex already knows: looked up 100 at a time by ID.
  2. All other papers: title search. A hit needs a near-identical title and a shared author surname.

Usage: python3 -I arxiv_match.py <tac.json> <cache.json> [limit] [--retry-misses]
  --retry-misses  search again the papers not found last time (preprints appear later)
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

args = [a for a in sys.argv[1:] if not a.startswith('--')]
src, cache_path = args[0], args[1]
limit = int(args[2]) if len(args) > 2 else None
retry = '--retry-misses' in sys.argv
D = json.load(open(src))
try:
    cache = json.load(open(cache_path))
except FileNotFoundError:
    cache = {}
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
STOP = set('a an the of for and in on with via to by from under using towards toward is are at as its into over'.split())
CODE = re.compile(r'https?://(?:www\.)?(?:github\.com|gitlab\.com|gitlab\.[a-z0-9.-]+)/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+', re.I)


def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def surname(name):                            # names are "Last, First"
    return norm(name.split(',')[0]).split(' ')[-1] if name else ''


last = [0.0]
def api(params):
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'tac-explorer-link-check/1.0'})
    for attempt in range(9):
        wait = 5 - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            return ET.fromstring(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:                 # 429/503: arXiv asks us to slow down; back off 1 to 15 min
            wait = min(900, 60 * 2 ** attempt)
            print(f'arXiv said {e}; waiting {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('arXiv API unreachable after long back-off')


def entry(e):
    aid = re.sub(r'v\d+$', '', e.find('a:id', NS).text.rsplit('/abs/', 1)[-1])
    t = ' '.join((e.find('a:title', NS).text or '').split())
    com = e.find('x:comment', NS)
    text = ' '.join(filter(None, [e.find('a:summary', NS).text, com.text if com is not None else '']))
    code = sorted({u.rstrip('.,);') for u in CODE.findall(text)})
    names = [a.find('a:name', NS).text for a in e.findall('a:author', NS)]
    return aid, t, code, names


def save():
    json.dump(cache, open(cache_path, 'w'))


# ---- 1. known arXiv IDs: batch lookup for code links ----
known = [p for p in D['papers'] if p['arxiv'] and p['id'] not in cache]
for i in range(0, len(known), 100):
    chunk = known[i:i + 100]
    root = api({'id_list': ','.join(p['arxiv'] for p in chunk), 'max_results': 100})
    got = {}
    for e in root.findall('a:entry', NS):
        if e.find('a:id', NS) is None: continue
        aid, t, code, _ = entry(e)
        got[aid] = (t, code)
    for p in chunk:
        t, code = got.get(p['arxiv'], ('', []))
        cache[p['id']] = {'arxiv': p['arxiv'], 'title': t, 'sim': None, 'via': 'openalex', 'code': code}
    save()
    print('known IDs', min(i + 100, len(known)), 'of', len(known), flush=True)

# ---- 2. title search for the rest ----
done = 0
for p in sorted(D['papers'], key=lambda p: p['date'], reverse=True):  # newest first: most likely on arXiv
    if p['arxiv'] or len(norm(p['title'])) < 15:
        continue
    key = p['id']
    if key in cache and (cache[key] or not retry):
        continue
    if limit is not None and done >= limit:
        break
    words = [w for w in norm(p['title']).split() if w not in STOP and len(w) > 1][:12]
    root = api({'search_query': ' AND '.join(f'ti:{w}' for w in words), 'max_results': 8})
    done += 1
    best = None
    ours = {surname(a['name']) for a in p['authors']}
    for e in root.findall('a:entry', NS):
        if e.find('a:id', NS) is None: continue
        aid, t, code, names = entry(e)
        sim = SequenceMatcher(None, norm(p['title']), norm(t)).ratio()
        shared = len(ours & {norm(n).split(' ')[-1] for n in names})
        if sim >= 0.9 and shared >= 1 and (best is None or sim > best['sim']):
            best = {'arxiv': aid, 'title': t, 'sim': round(sim, 3), 'shared_authors': shared, 'via': 'search', 'code': code}
    cache[key] = best or {}
    if done % 20 == 0:
        save()
        print(done, 'searched,', sum(1 for v in cache.values() if v), 'with arXiv so far', flush=True)
save()
found = [v for v in cache.values() if v]
print('checked', len(cache), '| on arXiv', len(found), '| with code', sum(1 for v in found if v['code']))
