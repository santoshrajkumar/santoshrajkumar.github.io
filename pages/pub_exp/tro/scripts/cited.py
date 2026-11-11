"""Citation counts (OpenAlex cited_by_count) for every paper in tro.json, looked up by OpenAlex ID in batches of 50.

Usage: python3 -I cited.py <tro.json> <out cited.json>
Writes {"fetched": date, "counts": {doi: citations}}. assemble.py lists the top 10 on the home page.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
UA = {'User-Agent': 'tro-explorer/1.0 (static site build script)'}
KEY = os.environ.get('OPENALEX_API_KEY', '')
papers = json.loads(src.read_text())['papers']
by_oa = {p['openalex']: p['id'] for p in papers if p['openalex']}
ids = sorted(by_oa)
counts = {}
for k in range(0, len(ids), 50):
    params = {'filter': 'openalex_id:' + '|'.join(ids[k:k + 50]), 'per-page': 50, 'select': 'id,cited_by_count'}
    if KEY:
        params['api_key'] = KEY
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(params)
    for attempt in range(8):
        try:
            res = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())['results']
            break
        except Exception as e:
            print(' ', e, flush=True)
            time.sleep(5 * 2 ** attempt)
    else:
        raise RuntimeError('OpenAlex unreachable')
    for r in res:
        counts[by_oa[r['id'].rsplit('/', 1)[-1]]] = r['cited_by_count']
    time.sleep(0.15)
out.write_text(json.dumps({'fetched': time.strftime('%Y-%m-%d'), 'counts': counts}))
top = sorted(counts.items(), key=lambda x: -x[1])[:10]
print('papers with counts', len(counts), 'of', len(papers), '| top 10', top)
