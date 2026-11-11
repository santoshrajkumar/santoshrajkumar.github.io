"""Find arXiv copies and code links for RA-L papers and write links.json for build.py.

1. Harvest arXiv metadata with the official API (3 s between requests), in cached slices under <cache_dir>:
     - every cs.RO paper (cross-lists included), one slice per quarter since 2015
     - every paper whose comments or journal reference mention RA-L
   Slices that ended more than 120 days ago are never downloaded again, so updates only fetch recent ones.
2. Match: an arXiv entry is the paper's preprint when the titles are near-identical (≥ 0.92) and at least
   one author surname is shared. OpenAlex's own arXiv links (from fetch.py) are kept as well.
3. Code: GitHub/GitLab URLs in the paper abstract, or in the matched arXiv abstract or comments.

Usage: python3 -I links.py <ral.json> <cache_dir> <out links.json>
"""
import datetime as dt
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

src, cache, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cache.mkdir(parents=True, exist_ok=True)
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/'}
UA = {'User-Agent': 'ral-explorer-link-check/1.0'}
PAGE = 1000
last = [0.0]


def fetch(query, start):
    url = 'https://export.arxiv.org/api/query?' + urllib.parse.urlencode(
        {'search_query': query, 'start': start, 'max_results': PAGE, 'sortBy': 'submittedDate', 'sortOrder': 'ascending'})
    for attempt in range(9):
        wait = 3.5 - (time.time() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()
        try:
            root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read())
            total = int(root.find('o:totalResults', NS).text)
            entries = root.findall('a:entry', NS)
            if entries or start >= total:
                return total, entries
            raise RuntimeError('empty page')       # the API sometimes returns an empty page; just ask again
        except Exception as e:
            wait = min(600, 20 * 2 ** attempt)
            print(f'  arXiv: {e}; waiting {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('arXiv API unreachable')


def entry(e):
    g = lambda p: (e.find(p, NS).text if e.find(p, NS) is not None else '') or ''
    return {'id': re.sub(r'v\d+$', '', g('a:id').rsplit('/abs/', 1)[-1]), 'title': ' '.join(g('a:title').split()),
            'authors': [a.find('a:name', NS).text for a in e.findall('a:author', NS)],
            'text': ' '.join([g('a:summary'), g('x:comment'), g('x:journal_ref')])}


def harvest(name, query, ended):
    f = cache / f'{name}.json'
    if f.exists() and ended < dt.date.today() - dt.timedelta(days=120):
        return json.loads(f.read_text())
    got, start, total = [], 0, None
    while total is None or start < total:
        total, entries = fetch(query, start)
        got += [entry(e) for e in entries]
        start += PAGE
    f.write_text(json.dumps(got))
    print(f'  {name}: {len(got)} entries', flush=True)
    return got


today = dt.date.today()
ARX = []
ARX += harvest('mentions_ral', 'co:"Robotics and Automation Letters" OR jr:"Robotics and Automation Letters" OR co:RA-L OR jr:RA-L OR co:RAL OR jr:RAL', today)
for y in range(2015, today.year + 1):
    for qn, (m0, m1) in enumerate([(1, 3), (4, 6), (7, 9), (10, 12)]):
        a = dt.date(y, m0, 1)
        if a > today:
            break
        b = dt.date(y, m1, 31 if m1 in (3, 12) else 30)
        ARX += harvest(f'csro_{y}q{qn + 1}', f'cat:cs.RO AND submittedDate:[{a:%Y%m%d}0000 TO {b:%Y%m%d}2359]', b)
print('arXiv entries harvested', len(ARX), flush=True)


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def surname(n):
    return norm(n).split(' ')[-1] if n else ''


# index arXiv entries by their 3 rarest-looking title words for fast candidate lookup
by_id = {}
for e in ARX:
    by_id[e['id']] = e
words = defaultdict(set)
for e in by_id.values():
    for w in set(norm(e['title']).split()):
        if len(w) > 3:
            words[w].add(e['id'])
CODE = re.compile(r'https?://(?:www\.)?(?:github\.com|gitlab\.com|gitlab\.[a-z0-9.-]+)/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+', re.I)
NOTCODE = re.compile(r'github\.com/(?:features|about|orgs|topics|sponsors|marketplace)/', re.I)


def codes(text):
    return [u for u in dict.fromkeys(re.sub(r'\.git$', '', u.rstrip('.,);:/')) for u in CODE.findall(text or '')) if not NOTCODE.search(u)]


D = json.loads(src.read_text())
res, n_oa, n_new = {}, 0, 0
for p in D['papers']:
    t = norm(p['title'])
    ours = {norm(a['name'].split(',')[0]).split(' ')[-1] for a in p['authors']}
    best = None
    tw = sorted({w for w in t.split() if len(w) > 3}, key=lambda w: len(words.get(w, ())))[:3]
    cands = set().union(*(words.get(w, set()) for w in tw)) if tw else set()
    for cid in cands:
        e = by_id[cid]
        sim = SequenceMatcher(None, t, norm(e['title'])).ratio()
        if sim >= 0.92 and ours & {surname(n) for n in e['authors']} and (best is None or sim > best[0]):
            best = (sim, e)
    arxiv = best[1]['id'] if best else ''
    if p['arxiv']:
        n_oa += 1
        arxiv = arxiv or p['arxiv']
    elif arxiv:
        n_new += 1
    e = by_id.get(arxiv)
    code = codes(p['abstract']) + (codes(e['text']) if e else [])
    code = list(dict.fromkeys(code))[:3]
    if arxiv or code:
        res[p['id']] = {'arxiv': arxiv, 'code': code}
out.write_text(json.dumps(res, indent=0, sort_keys=True))
print('papers', len(D['papers']), '| arXiv', sum(1 for v in res.values() if v['arxiv']),
      f'(OpenAlex {n_oa}, title match adds {n_new})', '| with code', sum(1 for v in res.values() if v['code']))
