"""Download every IEEE Transactions on Robotics (T-RO) paper since 2004 (volume 20), including early access, into tro.json.

Sources (both free, no key):
  - Crossref: decides which papers exist. DOI, title, authors and affiliations as printed, volume/issue/pages.
  - OpenAlex: abstract, institutions (with country and type), author IDs, topics, keywords, arXiv copies.
Raw responses are saved in raw/ so build steps can be re-run without downloading again.

Usage: python3 -I fetch.py <out tro.json> [raw_dir]

T-RO volume 20 (2004) is split in Crossref: issues 1-3 carry the old T-RA ISSN 1042-296X, issue 4+ the print
ISSN 1546-1904 or 1552-3098, later years the online ISSN 1941-0468. All are fetched and merged by DOI.
"""
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

out = Path(sys.argv[1])
raw = Path(sys.argv[2] if len(sys.argv) > 2 else out.parent / 'raw')
raw.mkdir(parents=True, exist_ok=True)
ISSNS = ['1552-3098', '1546-1904', '1042-296X']  # T-RO, T-RO print 2004, T-RA (only volume >= 20 is kept)
OA_ISSN = '1552-3098'
FIRST_YEAR = 2004
UA = {'User-Agent': 'tro-explorer/1.0 (static site build script)'}


def get(url):
    for attempt in range(8):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read())
        except Exception as e:
            wait = min(600, 15 * 2 ** attempt)
            print(f'  {e}; retry in {wait} s', flush=True)
            time.sleep(wait)
    raise RuntimeError('gave up on ' + url)


def fresh(f, hours=12):
    """Reuse a raw download younger than 12 hours (so a failed run can be resumed cheaply)."""
    return f.exists() and time.time() - f.stat().st_mtime < hours * 3600


# ---------------- Crossref ----------------
cr = []
if fresh(raw / 'crossref.json'):
    cr = json.load((raw / 'crossref.json').open())
    print('crossref: reusing', len(cr), 'items from', raw / 'crossref.json')
else:
    seen = set()
    for issn in ISSNS:
        cursor, got = '*', 0
        filt = f'from-pub-date:{FIRST_YEAR - 1}' if issn == '1042-296X' else None
        while True:
            q = {'rows': 1000, 'cursor': cursor,
                 'select': 'DOI,title,author,volume,issue,page,published,published-print,published-online,created,type'}
            if filt:
                q['filter'] = filt
            m = get(f'https://api.crossref.org/journals/{issn}/works?' + urllib.parse.urlencode(q))['message']
            for x in m['items']:
                if x['DOI'].lower() not in seen:
                    seen.add(x['DOI'].lower())
                    cr.append(x)
            got += len(m['items'])
            print('crossref', issn, got, 'of', m['total-results'], flush=True)
            if not m['items'] or got >= m['total-results']:
                break
            cursor = m['next-cursor']
    json.dump(cr, (raw / 'crossref.json').open('w'))

# ---------------- OpenAlex ----------------
# Keyless use allows page= paging up to 10,000 results per query, so ask one publication year at a time.
# Set OPENALEX_API_KEY (free at https://openalex.org/settings/api) to raise the daily request budget.
KEY = os.environ.get('OPENALEX_API_KEY', '')
oa = []
if fresh(raw / 'openalex.json'):
    oa = json.load((raw / 'openalex.json').open())
    print('openalex: reusing', len(oa), 'items')
else:
    src = get(f'https://api.openalex.org/sources/issn:{OA_ISSN}')['id'].rsplit('/', 1)[-1]
    for year in range(FIRST_YEAR - 1, int(time.strftime('%Y')) + 2):
        page, n = 1, None
        while n is None or (page - 1) * 200 < n:
            params = {'filter': f'primary_location.source.id:{src},publication_year:{year}', 'per-page': 200, 'page': page,
                      'select': 'id,doi,title,publication_date,abstract_inverted_index,authorships,open_access,'
                                'locations,biblio,type,primary_topic,keywords'}
            if KEY:
                params['api_key'] = KEY
            j = get('https://api.openalex.org/works?' + urllib.parse.urlencode(params))
            n = j['meta']['count']
            oa += j['results']
            page += 1
            time.sleep(0.2)
        print('openalex', year, n, '| total', len(oa), flush=True)
    json.dump(oa, (raw / 'openalex.json').open('w'))

# Papers OpenAlex files under another source (T-RA for 2004) or misses by year: look them up by DOI
have = {(w.get('doi') or '').lower().replace('https://doi.org/', '') for w in oa}
need = sorted({x['DOI'].lower() for x in cr if x.get('author')} - have)
if need and not fresh(raw / 'openalex_bydoi.json'):
    extra = []
    for k in range(0, len(need), 50):
        params = {'filter': 'doi:' + '|'.join(need[k:k + 50]), 'per-page': 50,
                  'select': 'id,doi,title,publication_date,abstract_inverted_index,authorships,open_access,'
                            'locations,biblio,type,primary_topic,keywords'}
        if KEY:
            params['api_key'] = KEY
        extra += get('https://api.openalex.org/works?' + urllib.parse.urlencode(params))['results']
        time.sleep(0.2)
    json.dump(extra, (raw / 'openalex_bydoi.json').open('w'))
    print('openalex by DOI: asked', len(need), 'found', len(extra))
if (raw / 'openalex_bydoi.json').exists():
    oa += json.load((raw / 'openalex_bydoi.json').open())

# ---------------- merge ----------------
TAG = re.compile(r'<[^>]+>')


def clean(s):
    s = html.unescape(TAG.sub('', s or ''))
    return re.sub(r'\s+', ' ', s).strip()


def ascii_(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z]', '', ''.join(c for c in s if not unicodedata.combining(c)).lower())


def abstract(inv):
    if not inv:
        return ''
    pos = sorted((i, w) for w, ii in inv.items() for i in ii)
    s = clean(' '.join(w for _, w in pos))
    return re.sub(r'^(abstract|summary)\s*[:.—-]?\s*', '', s, flags=re.I)


def date(x, keys=('published-online', 'published-print', 'published', 'created')):
    for k in keys:
        dp = (x.get(k) or {}).get('date-parts') or [[]]
        if dp[0] and dp[0][0]:
            return '-'.join(f'{v:02d}' if i else str(v) for i, v in enumerate(dp[0]))
    return ''


def doi_key(d):
    return (d or '').lower().replace('https://doi.org/', '')


def short(u):
    return (u or '').rsplit('/', 1)[-1]


OA = {doi_key(w['doi']): w for w in oa if w.get('doi')}
# Not research papers: journal front matter, calls for papers, editorials
SKIP = re.compile(r'^(ieee transactions on robotics|ieee robotics and automation society|table of contents|'
                  r'information for authors|call for papers|front cover|back cover|editorial|guest editorial|introducing ieee|introduction to the special|'
                  r'ieee open access|publication information|blank page|\[?front matter|errat|corrections? to|'
                  r'retraction|expression of concern|reviewers? list|list of reviewers|ieee )', re.I)


def pair_authors(cra, ws):
    """Line up OpenAlex authorships with Crossref authors: by position when the counts agree, else by surname."""
    if len(cra) == len(ws):
        return ws
    out, used = [], set()
    for a in cra:
        fam = ascii_(a.get('family') or (a.get('name') or '').split(' ')[-1])
        hit = None
        for k, w in enumerate(ws):
            if k in used:
                continue
            dn = ascii_(((w.get('author') or {}).get('display_name') or '').split(' ')[-1])
            if fam and dn and (fam == dn or fam in ascii_((w.get('author') or {}).get('display_name'))):
                hit = k
                break
        if hit is not None:
            used.add(hit)
        out.append(ws[hit] if hit is not None else {})
    return out


papers, skipped = [], []
for x in cr:
    doi = x['DOI'].lower()
    title = clean((x.get('title') or [''])[0])
    if not title or SKIP.match(title) or not x.get('author'):
        skipped.append(title)
        continue
    w = OA.get(doi, {})
    vol, issue, pages = x.get('volume') or '', x.get('issue') or '', x.get('page') or ''
    online = date(x, ('published-online', 'created')) or (w.get('publication_date') or '')
    # Early-access articles have a DOI but no volume yet. (Since volume 40, 2024, T-RO has no issue numbers:
    # final articles carry a volume and continuous page numbers.) A handful of old records lack a volume; not early access.
    early = not vol and int((online or date(x) or '0')[:4]) >= int(time.strftime('%Y')) - 1
    if vol.isdigit():
        if int(vol) < 20:
            continue  # IEEE Transactions on Robotics and Automation (before T-RO)
        year = 1984 + int(vol)  # volume 20 = 2004
    else:
        year = int((online or date(x))[:4])
    ws = pair_authors(x['author'], w.get('authorships') or [])
    authors = []
    for a, wa in zip(x['author'], ws):
        name = ', '.join(filter(None, [clean(a.get('family')), clean(a.get('given'))])) or clean(a.get('name'))
        affs = [clean(f.get('name')) for f in a.get('affiliation') or [] if f.get('name')]
        if not affs:
            affs = [clean(s) for s in wa.get('raw_affiliation_strings') or []]
        insts = [[t['display_name'], t.get('country_code') or '', t.get('type') or '', short(t['id'])]
                 for t in wa.get('institutions') or [] if t.get('id')]
        authors.append({
            'name': name,
            'aff': '; '.join(dict.fromkeys(affs)),
            'orcid': short(a.get('ORCID') or (wa.get('author') or {}).get('orcid')),
            'oa_id': short((wa.get('author') or {}).get('id')),
            'oa_insts': insts,
        })
    arxiv = ''
    for loc in w.get('locations') or []:
        u = (loc.get('landing_page_url') or '') + ' ' + (loc.get('pdf_url') or '')
        m = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/[0-9]{7})', u)
        if m:
            arxiv = m.group(1)
            break
    pt = w.get('primary_topic') or {}
    papers.append({
        'id': doi,
        'title': title,
        'abstract': abstract(w.get('abstract_inverted_index')),
        'date': online,
        'year': year,
        'volume': vol,
        'issue': issue,
        'pages': pages,
        'early': early,
        'authors': authors,
        'topic': pt.get('display_name') or '',
        'subfield': (pt.get('subfield') or {}).get('display_name') or '',
        'keywords': [k['display_name'] for k in w.get('keywords') or []][:6],
        'open_access': (w.get('open_access') or {}).get('oa_status') in ('gold', 'hybrid', 'diamond'),
        'arxiv': arxiv,
        'openalex': short(w.get('id')),
    })

papers.sort(key=lambda p: (p['date'], p['id']))
meta = {'fetched': time.strftime('%Y-%m-%d'), 'crossref_items': len(cr), 'openalex_items': len(oa)}
json.dump({'meta': meta, 'papers': papers}, out.open('w'), ensure_ascii=False, indent=0)
print('papers', len(papers), '| skipped (front matter etc.)', len(skipped), '| early access', sum(p['early'] for p in papers))
print('by year', sorted(Counter(p['year'] for p in papers).items()))
print('no abstract', sum(not p['abstract'] for p in papers), '| not in OpenAlex', sum(not p['openalex'] for p in papers),
      '| no topic', sum(not p['topic'] for p in papers), '| arXiv via OpenAlex', sum(bool(p['arxiv']) for p in papers))
na = sum(len(p['authors']) for p in papers)
print('authors', na, '| without OpenAlex institution', sum(not a['oa_insts'] for p in papers for a in p['authors']),
      '| without any affiliation', sum(not a['aff'] and not a['oa_insts'] for p in papers for a in p['authors']))
print('skipped titles', Counter(skipped).most_common(15))
