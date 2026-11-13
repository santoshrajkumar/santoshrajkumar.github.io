"""Find GitHub repositories whose README or description names a NeurIPS 2026 DSC paper, by exact title (and by
arXiv ID when known). Public search API, kept under 10 requests per minute; cached and resumable. A hit counts
only if the repo description or README text contains the normalized title or the arXiv ID.

Usage: python3 -I github_match.py <neurips.json> <cache.json> <ids.txt> [arxiv_cache.json]
"""
import json, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error

src, cache_path, ids_path = sys.argv[1], sys.argv[2], sys.argv[3]
ax = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
P = {p['id']: p for p in json.load(open(src))['papers']}
ids = [l.strip() for l in open(ids_path) if l.strip()]
try: cache = json.load(open(cache_path))
except FileNotFoundError: cache = {}
H = {'User-Agent': 'neurips2026-dsc-explorer-link-check/1.0', 'Accept': 'application/vnd.github+json'}

def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

last = [0.0]
def get(url):
    while True:
        wait = 6.5 - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = int(e.headers.get('X-RateLimit-Reset', time.time() + 60))
                time.sleep(max(5, reset - time.time() + 2)); continue
            if e.code in (404, 422): return None
            raise
        except Exception:
            time.sleep(15)

def readme_has(full_name, needles):
    # raw file server, not the REST API (60 requests/hour without a login)
    for name in ('README.md', 'readme.md', 'README.rst', 'README', 'Readme.md', 'README.txt'):
        try:
            r = urllib.request.urlopen(urllib.request.Request(f'https://raw.githubusercontent.com/{full_name}/HEAD/{name}', headers={'User-Agent': H['User-Agent']}), timeout=30)
            txt = norm(r.read().decode('utf-8', 'ignore'))
            return any(n and n in txt for n in needles)
        except urllib.error.HTTPError as e:
            if e.code != 404: time.sleep(5)
        except Exception:
            time.sleep(5)
    return False

done = 0
for key in ids:
    p = P[key]
    aid = (ax.get(key) or {}).get('arxiv')
    if key in cache and (not aid or cache[key].get('aid') == aid): continue
    title = p['title'].strip()
    if len(norm(title).split()) < 4: cache[key] = {'repos': [], 'aid': aid}; continue
    terms = [f'"{title}"'] + ([f'"{aid}"'] if aid else [])
    j = get('https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': ' OR '.join(terms) + ' in:readme,description', 'per_page': 5}))
    repos = []
    needles = [norm(title)] + ([aid.replace('.', ' ')] if aid else [])
    for it in (j or {}).get('items', [])[:3]:
        if norm(title) in norm(it.get('description') or '') or readme_has(it['full_name'], needles):
            repos.append(it['html_url'])
    prev = (cache.get(key) or {}).get('repos') or []
    cache[key] = {'repos': list(dict.fromkeys(prev + repos)), 'aid': aid}
    done += 1
    if done % 20 == 0:
        json.dump(cache, open(cache_path, 'w')); print(done, 'searched,', sum(1 for v in cache.values() if v['repos']), 'with repos', flush=True)
json.dump(cache, open(cache_path, 'w'))
print('done; papers with repos:', sum(1 for v in cache.values() if v['repos']))
