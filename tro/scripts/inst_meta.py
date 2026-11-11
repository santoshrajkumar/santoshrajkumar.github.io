"""Fetch acronyms, alternative names, country, type and parent of every OpenAlex institution in tro.json.
Cached in <cache.json>; only institutions not seen before are downloaded.

Usage: python3 -I inst_meta.py <tro.json> <cache.json>
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

src, cpath = Path(sys.argv[1]), Path(sys.argv[2])
cache = json.loads(cpath.read_text()) if cpath.exists() else {}
D = json.loads(src.read_text())
ids = sorted({i[3] for p in D['papers'] for a in p['authors'] for i in a['oa_insts']} - set(cache))
print('institutions', len(ids) + len(cache), '| to fetch', len(ids), flush=True)
UA = {'User-Agent': 'tro-explorer/1.0 (static site build script)'}
for k in range(0, len(ids), 50):
    chunk = ids[k:k + 50]
    q = urllib.parse.urlencode({'filter': 'openalex_id:' + '|'.join(chunk), 'per-page': 50,
                                'select': 'id,display_name,display_name_acronyms,display_name_alternatives,country_code,type,ror,lineage'})
    for attempt in range(8):
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request('https://api.openalex.org/institutions?' + q, headers=UA), timeout=60).read())['results']
            break
        except Exception as e:
            print(' ', e, flush=True)
            time.sleep(5 * 2 ** attempt)
    else:
        raise RuntimeError('OpenAlex unreachable')
    for r in res:
        cache[r['id'].rsplit('/', 1)[-1]] = {
            'n': r['display_name'], 'acr': r.get('display_name_acronyms') or [], 'alt': (r.get('display_name_alternatives') or [])[:8],
            'c': r.get('country_code') or '', 't': r.get('type') or '', 'lin': [x.rsplit('/', 1)[-1] for x in r.get('lineage') or []]}
    for i in chunk:
        cache.setdefault(i, {})
    if k % 1000 == 0:
        print(' ', k + len(chunk), 'of', len(ids), flush=True)
    time.sleep(0.15)
cpath.write_text(json.dumps(cache, ensure_ascii=False))
print('done', len(cache))
