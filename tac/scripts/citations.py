"""Add OpenAlex citation counts to tac.json (field 'cited'), and save them in raw/citations.json.

One small query per publication year (DOI and cited_by_count only), so it takes a minute or two.
Usage: python3 -I citations.py <tac.json> [raw_dir]
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

src = Path(sys.argv[1])
raw = Path(sys.argv[2] if len(sys.argv) > 2 else src.parent / 'raw')
ISSN = '0018-9286'
UA = {'User-Agent': 'tac-explorer/1.0 (static site build script)'}
KEY = os.environ.get('OPENALEX_API_KEY', '')


def get(params):
    if KEY:
        params['api_key'] = KEY
    url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(params)
    for attempt in range(8):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception as e:
            wait = min(300, 5 * 2 ** attempt)
            print(f'  {e}; retry in {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('gave up on ' + url)


D = json.loads(src.read_text())
years = sorted({p['year'] for p in D['papers']})
cites = {}
for year in range(years[0] - 1, years[-1] + 2):
    page, n = 1, None
    while n is None or (page - 1) * 200 < n:
        j = get({'filter': f'primary_location.source.issn:{ISSN},publication_year:{year}', 'per-page': 200,
                 'page': page, 'select': 'doi,cited_by_count'})
        n = j['meta']['count']
        for w in j['results']:
            if w.get('doi'):
                d = w['doi'].lower().replace('https://doi.org/', '')
                cites[d] = max(cites.get(d, 0), w.get('cited_by_count') or 0)
        if not j['results']:
            break
        page += 1
        time.sleep(0.2)
    print('citations', year, n, flush=True)
# papers OpenAlex files under another year or source: look them up by DOI
missing = [p['id'] for p in D['papers'] if p['id'] not in cites and p['openalex']]
for i in range(0, len(missing), 50):
    j = get({'filter': 'doi:' + '|'.join(missing[i:i + 50]), 'per-page': 50, 'select': 'doi,cited_by_count'})
    for w in j['results']:
        cites[w['doi'].lower().replace('https://doi.org/', '')] = w.get('cited_by_count') or 0
    time.sleep(0.2)
for p in D['papers']:
    p['cited'] = cites.get(p['id'], 0)
D['meta']['cited_on'] = time.strftime('%Y-%m-%d')
json.dump(cites, (raw / 'citations.json').open('w'))
json.dump(D, src.open('w'), ensure_ascii=False, indent=0)
top = sorted(D['papers'], key=lambda p: -p['cited'])[:10]
print('with count', sum(p['id'] in cites for p in D['papers']), 'of', len(D['papers']))
for p in top:
    print(p['cited'], p['year'], p['title'][:90])
