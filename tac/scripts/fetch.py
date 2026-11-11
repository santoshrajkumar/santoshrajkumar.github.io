"""Download every IEEE Transactions on Automatic Control (TAC) paper from 2000 on, including early access, into tac.json.

Sources (both free, no key):
  - Crossref: the complete DOI list, titles, authors and affiliations as printed, volume/issue/pages.
  - OpenAlex: abstracts, institution IDs with country and type, open-access status, arXiv copies.
Crossref decides which papers exist. OpenAlex only adds detail. Raw responses are saved in raw/.

Usage: python3 -I fetch.py <out tac.json> [raw_dir] [--offline]
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

out = Path(sys.argv[1])
args = [a for a in sys.argv[1:] if not a.startswith('--')]
raw = Path(args[1] if len(args) > 1 else out.parent / 'raw')
raw.mkdir(parents=True, exist_ok=True)
ISSN = '0018-9286'
UA = {'User-Agent': 'tac-explorer/1.0 (static site build script)'}
START_YEAR = 2000


def get(url):
    for attempt in range(8):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())
        except Exception as e:
            wait = min(300, 5 * 2 ** attempt)
            print(f'  {e}; retry in {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('gave up on ' + url)


OFFLINE = '--offline' in sys.argv  # re-merge the saved raw/ files without downloading
KEY = os.environ.get('OPENALEX_API_KEY', '')  # optional free key from https://openalex.org/settings/api
SELECT = 'id,doi,title,publication_date,abstract_inverted_index,authorships,open_access,locations,biblio,type'


def doi_key(d):
    return (d or '').lower().replace('https://doi.org/', '')


def openalex(params):
    if KEY:
        params['api_key'] = KEY
    return get('https://api.openalex.org/works?' + urllib.parse.urlencode(params))


if OFFLINE:
    cr = json.load((raw / 'crossref.json').open())
    oa = json.load((raw / 'openalex.json').open())
else:
    # ---------------- Crossref ----------------
    cr, cursor = [], '*'
    while True:
        q = urllib.parse.urlencode({'rows': 1000, 'cursor': cursor, 'filter': f'from-pub-date:{START_YEAR - 1}-07-01',
                                    'select': 'DOI,title,author,volume,issue,page,published,published-print,published-online,created,type,article-number'})
        m = get(f'https://api.crossref.org/journals/{ISSN}/works?{q}')['message']
        cr += m['items']
        print('crossref', len(cr), 'of', m['total-results'], flush=True)
        if not m['items'] or len(cr) >= m['total-results']:
            break
        cursor = m['next-cursor']
    json.dump(cr, (raw / 'crossref.json').open('w'))

    # ---------------- OpenAlex ----------------
    # Keyless page= paging stops at 10,000 results per query, so ask one publication year at a time.
    # Pages can overlap when many papers share a date, so results are de-duplicated and any Crossref DOI
    # still missing is fetched by DOI afterwards.
    src = get(f'https://api.openalex.org/sources/issn:{ISSN}')['id'].rsplit('/', 1)[-1]
    got = {}
    for year in range(START_YEAR - 1, int(time.strftime('%Y')) + 2):
        page, n = 1, None
        while n is None or (page - 1) * 200 < n:
            j = openalex({'filter': f'primary_location.source.id:{src},publication_year:{year}', 'per-page': 200,
                          'page': page, 'sort': 'publication_date:asc', 'select': SELECT})
            n = j['meta']['count']
            for w in j['results']:
                got[w['id']] = w
            if not j['results']:
                break
            page += 1
            time.sleep(0.2)
        print('openalex', year, n, '| total', len(got), flush=True)
    have = {doi_key(w.get('doi')) for w in got.values()}
    missing = [x['DOI'].lower() for x in cr if x['DOI'].lower() not in have]
    for i in range(0, len(missing), 50):
        j = openalex({'filter': 'doi:' + '|'.join(missing[i:i + 50]), 'per-page': 50, 'select': SELECT})
        for w in j['results']:
            got[w['id']] = w
        time.sleep(0.3)
    print('openalex', len(got), f'(looked up {len(missing)} missing DOIs one batch at a time)', flush=True)
    oa = list(got.values())
    json.dump(oa, (raw / 'openalex.json').open('w'))

# ---------------- merge ----------------
TAG = re.compile(r'<[^>]+>')


def clean(s):
    s = html.unescape(TAG.sub('', s or ''))
    return re.sub(r'\s+', ' ', s).strip()


def abstract(inv):
    if not inv:
        return ''
    pos = sorted((i, w) for w, ii in inv.items() for i in ii)
    return clean(' '.join(w for _, w in pos))


def date(x):
    """Most precise date: online/print publication if it has a month, else the DOI registration date
    (IEEE registers the DOI when the article goes online), else the year."""
    best = ''
    for k in ('published-online', 'published-print', 'published', 'created'):
        dp = ((x.get(k) or {}).get('date-parts') or [[]])[0]
        if dp and dp[0]:
            d = '-'.join(f'{v:02d}' if i else str(v) for i, v in enumerate(dp))
            if len(d) > len(best) and not (best and k == 'created' and d[:4] != best[:4]):
                best = d
    return best


import unicodedata


def ascii_(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z]', '', ''.join(c for c in s if not unicodedata.combining(c)).lower())


def pair_authors(cra, ws):
    """Line up OpenAlex authorships with Crossref authors: by position when the counts agree, else by surname."""
    if len(cra) == len(ws):
        return ws
    out, used = [], set()
    for a in cra:
        fam = ascii_(a.get('family') or (a.get('name') or '').split(' ')[-1])
        hit = None
        for k, w in enumerate(ws):
            dn = ascii_((w.get('author') or {}).get('display_name'))
            if k not in used and fam and dn and fam in dn:
                hit = k
                break
        if hit is not None:
            used.add(hit)
        out.append(ws[hit] if hit is not None else {})
    return out


OA = {doi_key(w['doi']): w for w in oa if w.get('doi')}
# Not research papers: journal front matter, calls for papers, editorials
SKIP = re.compile(r'^(ieee transactions on automatic control|ieee control systems society|in memoriam|errat|corrections? to|retraction|expression of concern|reviewers? list|list of reviewers|20\d\d index|annual index|author index|subject index|book review|special issue|introduction to the special|in this issue|scanning the issue|a note from the editors?|authors?[\x27\u2019]? ?reply|reply to|<|table of contents|information for authors|'
                  r'call for papers|front cover|back cover|editorial|guest editorial|introducing|ieee open access|'
                  r'publication information|blank page|\[?front matter|ieee[- ]csl? |ieee control systems|ieee transactions on|ieee xplore|ieee copyright|ieee personal)', re.I)
BOOK = re.compile(r'\[book reviews?|book review\]|\[book review|editorial of the editor|</title>', re.I)
papers, skipped = [], []
for x in cr:
    doi = x['DOI'].lower()
    title = clean((x.get('title') or [''])[0])
    if not title or SKIP.match(title) or BOOK.search(title) or not x.get('author'):
        skipped.append(title)
        continue
    w = OA.get(doi, {})
    d = date(x) or (w.get('publication_date') or '')
    if d[:4] and int(d[:4]) < START_YEAR:
        continue
    # OpenAlex authorships line up with Crossref's author order; use them for institution IDs
    ws = pair_authors(x['author'], w.get('authorships') or [])
    authors = []
    for i, a in enumerate(x['author']):
        name = ', '.join(filter(None, [clean(a.get('family')), clean(a.get('given'))])) or clean(a.get('name'))
        affs = [clean(f.get('name')) for f in a.get('affiliation') or [] if f.get('name')]
        wa = ws[i] if i < len(ws) else {}
        if not affs:
            affs = [clean(s) for s in wa.get('raw_affiliation_strings') or []]
        insts = [[t['display_name'], t.get('country_code') or '', t.get('type') or '', t['id'].rsplit('/', 1)[-1]]
                 for t in wa.get('institutions') or []]
        authors.append({
            'name': name,
            'aff': '; '.join(affs),
            'orcid': (a.get('ORCID') or (wa.get('author') or {}).get('orcid') or '').rsplit('/', 1)[-1],
            'oa_id': ((wa.get('author') or {}).get('id') or '').rsplit('/', 1)[-1],
            'oa_insts': insts,
        })
    arxiv = ''
    for loc in w.get('locations') or []:
        u = (loc.get('landing_page_url') or '') + ' ' + (loc.get('pdf_url') or '')
        m = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})', u)
        if m:
            arxiv = m.group(1)
            break
    pages = x.get('page') or ''
    # IEEE early-access articles have a DOI but no volume yet, and a placeholder page "1-1".
    # A few older records were never updated after final publication; those are not called early access.
    no_vol = not x.get('volume') or pages in ('', '1', '1-1')
    if no_vol:
        pages = ''
    early = no_vol and d >= time.strftime('%Y-%m-%d', time.localtime(time.time() - 365 * 86400))
    papers.append({
        'id': doi,
        'title': title,
        'abstract': abstract(w.get('abstract_inverted_index')),
        'date': d,
        'year': int(d[:4]) if d[:4] else None,
        'volume': '' if no_vol else x.get('volume') or '',
        'issue': x.get('issue') or '',
        'pages': pages,
        'early': early,
        'authors': authors,
        'open_access': (w.get('open_access') or {}).get('oa_status') in ('gold', 'hybrid', 'diamond'),
        'arxiv': arxiv,
        'openalex': (w.get('id') or '').rsplit('/', 1)[-1],
    })

papers.sort(key=lambda p: (p['date'], p['id']))
# The same paper registered twice (a reprint, or a DOI with a stray trailing dot): same title and first author.
# Keep the copy with an abstract, then the earlier one. A comment and its reply share a title but not authors.
seen, dedup = {}, []
for p in sorted(papers, key=lambda p: (not p['abstract'], p['id'].endswith('.'), p['date'])):
    k = (re.sub(r'[^a-z0-9]', '', p['title'].lower()), ascii_(p['authors'][0]['name'].split(',')[0].split(' ')[-1]))
    if k in seen:
        skipped.append('duplicate: ' + p['title'][:40])
        continue
    seen[k] = 1
    dedup.append(p)
papers = sorted(dedup, key=lambda p: (p['date'], p['id']))
meta = {'fetched': time.strftime('%Y-%m-%d'), 'crossref_items': len(cr), 'openalex_items': len(oa)}
json.dump({'meta': meta, 'papers': papers}, out.open('w'), ensure_ascii=False, indent=0)
from collections import Counter  # noqa: E402
print('papers', len(papers), '| skipped (front matter etc.)', len(skipped), '| early access', sum(p['early'] for p in papers))
print('by year', sorted(Counter(p['year'] for p in papers).items()))
print('no abstract', sum(not p['abstract'] for p in papers), '| not in OpenAlex', sum(not p['openalex'] for p in papers),
      '| arXiv via OpenAlex', sum(bool(p['arxiv']) for p in papers), '| open access', sum(p['open_access'] for p in papers))
print('authors without affiliation', sum(not a['aff'] for p in papers for a in p['authors']), 'of', sum(len(p['authors']) for p in papers))
print('skipped titles', Counter(skipped).most_common(15))
