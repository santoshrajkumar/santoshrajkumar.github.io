"""Find GitHub repositories whose README or description names a CDC 2026 paper, by exact title
(and by arXiv ID when known). Public search API, kept under 10 requests per minute; cached/resumable.
A hit only counts if the repo's README text actually contains the normalized title or the arXiv ID.

Usage: python3 -I github_match.py <cdc.json> <cache.json> [arxiv_cache.json]
"""
import base64, json, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error

src, cache_path = sys.argv[1], sys.argv[2]
ax = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
D = json.load(open(src)); S = D['sessions']
try:
    cache = json.load(open(cache_path))
except FileNotFoundError:
    cache = {}
TECH = {'Regular Session', 'Invited Session', 'RI Session'}
H = {'User-Agent': 'cdc2026-explorer-link-check/1.0', 'Accept': 'application/vnd.github+json'}

def norm(s):
    s = unicodedata.normalize('NFKD', s); s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'\(I\)\s*$', '', s)
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()

last = [0.0]
def get(url):
    while True:
        wait = 6.5 - (time.time() - last[0])
        if wait > 0: time.sleep(wait)
        last[0] = time.time()
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40)
            return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = int(e.headers.get('X-RateLimit-Reset', time.time() + 60))
                time.sleep(max(5, reset - time.time() + 2)); continue
            if e.code == 404: return None
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
            if e.code != 404: time.sleep(5)
        except Exception:
            time.sleep(5)
    return False

done = 0
for p in D['papers']:
    if S[p['session']]['type'] not in TECH: continue
    key = p['id']
    aid = (ax.get(key) or {}).get('arxiv')
    if key in cache and (not aid or cache[key].get('aid') == aid): continue
    title = re.sub(r'\s*\(I\)\s*$', '', p['title']).strip()
    if len(norm(title).split()) < 5: cache[key] = {'repos': [], 'aid': aid}; continue
    terms = [f'"{title}"'] + ([f'"{aid}"'] if aid else [])
    q = ' OR '.join(terms) + ' in:readme,description'
    j = get('https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': q, 'per_page': 5}))
    repos = []
    for it in (j or {}).get('items', [])[:3]:
        needles = [norm(title)] + ([aid.replace('.', ' ')] if aid else [])
        if norm(title) in norm(it.get('description') or '') or readme_has(it['full_name'], needles):
            repos.append(it['html_url'])
    cache[key] = {'repos': repos, 'aid': aid}
    done += 1
    if done % 20 == 0:
        json.dump(cache, open(cache_path, 'w'))
        print(done, 'searched,', sum(1 for v in cache.values() if v['repos']), 'with repos', flush=True)
json.dump(cache, open(cache_path, 'w'))
print('done; papers with repos:', sum(1 for v in cache.values() if v['repos']))
