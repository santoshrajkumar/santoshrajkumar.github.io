"""Find GitHub repositories whose README or description names a T-RO paper, by exact title (and by arXiv ID
when known). Public search API, kept under 10 requests per minute (30 with GITHUB_TOKEN set); cached and resumable,
newest papers first. A hit only counts if the repo's description or README actually contains the title or arXiv ID.

Usage: python3 -I github_match.py <tro.json> <cache.json> [links.json] [max_papers]
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

src, cache_path = sys.argv[1], sys.argv[2]
links = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else {}
limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
D = json.load(open(src))
try:
    cache = json.load(open(cache_path))
except FileNotFoundError:
    cache = {}
H = {'User-Agent': 'tro-explorer-link-check/1.0', 'Accept': 'application/vnd.github+json'}
if os.environ.get('GITHUB_TOKEN'):
    H['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
GAP = 2.2 if 'Authorization' in H else 6.5


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower()).strip()


last = [0.0]


def get(url):
    while True:
        wait = GAP - (time.time() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = int(e.headers.get('X-RateLimit-Reset', time.time() + 60))
                time.sleep(max(5, reset - time.time() + 2))
                continue
            if e.code in (404, 422):
                return None
            raise
        except Exception:
            time.sleep(15)


def readme_has(full_name, needles):
    # raw file server, not the REST API (which allows only 60 requests/hour without a login)
    for name in ('README.md', 'readme.md', 'README.rst', 'README', 'Readme.md', 'README.txt'):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                f'https://raw.githubusercontent.com/{full_name}/HEAD/{name}', headers={'User-Agent': H['User-Agent']}), timeout=30)
            txt = norm(r.read().decode('utf-8', 'ignore'))
            return any(n and n in txt for n in needles)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return False


done = 0
for p in sorted(D['papers'], key=lambda p: p['date'], reverse=True):
    key = p['id']
    aid = (links.get(key) or {}).get('arxiv') or p.get('arxiv') or ''
    if key in cache and (not aid or cache[key].get('aid') == aid):
        continue
    if limit is not None and done >= limit:
        break
    title = p['title'].strip()
    if len(norm(title).split()) < 5:
        cache[key] = {'repos': [], 'aid': aid}
        continue
    terms = [f'"{title[:200]}"'] + ([f'"{aid}"'] if aid else [])
    j = get('https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': ' OR '.join(terms) + ' in:readme,description', 'per_page': 5}))
    repos = []
    for it in (j or {}).get('items', [])[:3]:
        needles = [norm(title)] + ([aid.replace('.', ' ')] if aid else [])
        if norm(title) in norm(it.get('description') or '') or readme_has(it['full_name'], needles):
            repos.append(it['html_url'])
    prev = (cache.get(key) or {}).get('repos') or []
    cache[key] = {'repos': list(dict.fromkeys(prev + repos)), 'aid': aid}
    done += 1
    if done % 25 == 0:
        json.dump(cache, open(cache_path, 'w'))
        print(done, 'searched,', sum(1 for v in cache.values() if v['repos']), 'with repos', flush=True)
json.dump(cache, open(cache_path, 'w'))
print('done; searched', len(cache), 'papers; with repos:', sum(1 for v in cache.values() if v['repos']))
