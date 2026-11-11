"""Build the L-CSS Explorer data files from lcss.json.

Usage: venv/bin/python -I build.py <lcss.json> <site_dir> [links.json] [cdc_site_dir]
Writes data.js, papers.js, papers.bin and lcss_institutions.csv into <site_dir>.

L-CSS papers have no author keywords, so each paper gets a research area from its 15 nearest
CDC 2026 papers (same embedding model), whose areas come from the official CDC keywords.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from institutions import resolve, RULES  # noqa: E402

src, site = Path(sys.argv[1]), Path(sys.argv[2])
LINKS = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 and Path(sys.argv[3]).exists() else {}
CDC = Path(sys.argv[4]) if len(sys.argv) > 4 else site.resolve().parents[2] / 'cdc2026'
site.mkdir(parents=True, exist_ok=True)
D = json.loads(src.read_text())
PAP = D['papers']
SNAPSHOT = D['meta']['fetched']
JOURNAL = 'https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=7782633'

# ---------------- research areas (same 16 areas and colors as the CDC 2026 Explorer) ----------------
cdc_data = (CDC / 'data.js').read_text()
CDC_META = json.loads(cdc_data[cdc_data.index('=') + 1:].rstrip().rstrip(';'))['meta']
AREAS = [(a['name'], a['short'], a['color']) for a in CDC_META['areas']]
cdc_p = (CDC / 'papers.js').read_text()
CP = json.loads(cdc_p[cdc_p.index('=') + 1:].rstrip().rstrip(';'))
buf = (CDC / 'papers.bin').read_bytes()
n_c, dim = CP['n'], CP['dim']
c_scale = np.frombuffer(buf, '<f4', n_c)
CE = np.frombuffer(buf, np.int8, n_c * dim, n_c * 4).reshape(n_c, dim).astype(np.float32) * c_scale[:, None]
CE /= np.linalg.norm(CE, axis=1, keepdims=True)
keep = np.array([bool(r[6]) for r in CP['rows']])  # only CDC papers whose area came from their own keywords
CE, CA = CE[keep], np.array([r[2] for r in CP['rows']])[keep]

# ---------------- embeddings ----------------
from sentence_transformers import SentenceTransformer  # noqa: E402

texts = [(p['title'] + '. ' + p['abstract']).strip() for p in PAP]
model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
E = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True).astype(np.float32)
S = E @ CE.T
for i, p in enumerate(PAP):
    nn = np.argpartition(-S[i], 15)[:15]
    votes = defaultdict(float)
    for j in nn:
        votes[int(CA[j])] += float(S[i, j])
    p['area'] = max(votes, key=votes.get)

# ---------------- institutions ----------------
COUNTRY = {
    'US': 'United States', 'CN': 'China', 'SE': 'Sweden', 'NL': 'Netherlands', 'CH': 'Switzerland', 'IT': 'Italy',
    'GB': 'United Kingdom', 'KR': 'South Korea', 'JP': 'Japan', 'DE': 'Germany', 'FR': 'France', 'CA': 'Canada',
    'AU': 'Australia', 'SG': 'Singapore', 'HK': 'Hong Kong', 'CY': 'Cyprus', 'BE': 'Belgium', 'NO': 'Norway',
    'AT': 'Austria', 'IL': 'Israel', 'TR': 'Turkey', 'IN': 'India', 'SA': 'Saudi Arabia', 'TW': 'Taiwan',
    'DK': 'Denmark', 'GR': 'Greece', 'FI': 'Finland', 'ES': 'Spain', 'PT': 'Portugal', 'BR': 'Brazil', 'MX': 'Mexico',
    'CZ': 'Czechia', 'HU': 'Hungary', 'PL': 'Poland', 'SK': 'Slovakia', 'RO': 'Romania', 'RU': 'Russia',
    'AE': 'United Arab Emirates', 'MO': 'Macau', 'MA': 'Morocco', 'TN': 'Tunisia', 'AM': 'Armenia', 'CL': 'Chile',
    'AR': 'Argentina', 'CO': 'Colombia', 'PE': 'Peru', 'EE': 'Estonia', 'IE': 'Ireland', 'LU': 'Luxembourg',
    'QA': 'Qatar', 'LB': 'Lebanon', 'OM': 'Oman', 'PK': 'Pakistan', 'LK': 'Sri Lanka', 'VN': 'Vietnam', 'EG': 'Egypt',
    'DZ': 'Algeria', 'KZ': 'Kazakhstan', 'UA': 'Ukraine', 'IR': 'Iran', 'NZ': 'New Zealand', 'ZA': 'South Africa',
    'SI': 'Slovenia', 'HR': 'Croatia', 'RS': 'Serbia', 'BG': 'Bulgaria', 'LT': 'Lithuania', 'LV': 'Latvia',
    'IS': 'Iceland', 'MY': 'Malaysia', 'TH': 'Thailand', 'ID': 'Indonesia', 'PH': 'Philippines', 'BD': 'Bangladesh',
    'NG': 'Nigeria', 'KE': 'Kenya', 'JO': 'Jordan', 'KW': 'Kuwait', 'BH': 'Bahrain', 'IQ': 'Iraq', 'EC': 'Ecuador',
    'UY': 'Uruguay', 'VE': 'Venezuela', 'CR': 'Costa Rica', 'MT': 'Malta', 'GE': 'Georgia', 'BY': 'Belarus',
}
# country names at the end of printed affiliations ("..., Ann Arbor, MI, USA")
CNAME2CC = {v.lower(): k for k, v in COUNTRY.items()}
CNAME2CC.update({'usa': 'US', 'u.s.a.': 'US', 'u.s.': 'US', 'uk': 'GB', 'u.k.': 'GB', 'england': 'GB', 'scotland': 'GB',
                 'wales': 'GB', 'p. r. china': 'CN', 'p.r. china': 'CN', 'pr china': 'CN', "people's republic of china": 'CN',
                 'republic of korea': 'KR', 'korea': 'KR', 'the netherlands': 'NL', 'hong kong sar': 'HK',
                 'macao': 'MO', 'turkiye': 'TR', 'türkiye': 'TR', 'czech republic': 'CZ', 'uae': 'AE', 'russian federation': 'RU'})
curated = {r[0] for r in RULES}
UNIT = re.compile(r'^(department|dept|school|faculty|college of|division|institute for|centre for|center for|laboratory for|lab for|'
                  r'key laboratory|state key|graduate school|chair|group|unit|section)\b', re.I)
ORG = re.compile(r'universi|institut|college|école|ecole|polytechn|academy|laborator|\blab\b|research|centre|center|'
                 r'\binc\b|corp|company|gmbh|\bltd\b|\bllc\b|agency|council|hospital|\bcnrs\b|\binria\b', re.I)


def raw_org(aff):
    """Pick the organisation out of a printed affiliation: the first comma part that names one."""
    parts = [x.strip() for x in aff.split(',') if x.strip()]
    for x in parts:
        if ORG.search(x) and not UNIT.match(x):
            return x
    for x in parts:
        if ORG.search(x):
            return x
    return parts[0] if parts else ''


def aff_country(aff):
    tail = aff.rsplit(',', 1)[-1].strip().rstrip('.').lower()
    return CNAME2CC.get(tail, '')


def inst_of(author):
    """[(canonical, country, sector)] for one author. Order: hand-checked table on the printed
    affiliation, then OpenAlex institutions (mapped through the table when possible), then the raw string."""
    affs = [a for a in author['aff'].split('; ') if a]
    hits = []
    for a in affs:
        for h in resolve(a):
            if h[0] == 'Northeastern University' and aff_country(a) == 'CN':  # the table assumes Boston
                h = ('Northeastern University (Shenyang)', 'CN', 'A')
            elif h[0] not in curated:
                continue
            if h not in hits:
                hits.append(h)
    if hits:
        return hits
    for name, cc, typ, _ in author['oa_insts']:
        r = [h for h in resolve(name) if h[0] in curated and (not cc or h[1] == cc)]
        h = r[0] if r else (name, cc, 'I' if typ == 'company' else 'A')
        if h not in hits:
            hits.append(h)
    if hits:
        return hits
    for a in affs:
        org = raw_org(a)
        if org:
            for name, cc, sec in resolve(org):
                h = (name, cc or aff_country(a), sec)
                if h not in hits:
                    hits.append(h)
    return hits


YEARS = sorted({p['year'] for p in PAP})
YI = {y: i for i, y in enumerate(YEARS)}
info, aliases = {}, defaultdict(Counter)
for p in PAP:
    insts, frac = [], defaultdict(float)
    n = len(p['authors']) or 1
    for a in p['authors']:
        res = inst_of(a)
        a['insts'] = [h[0] for h in res]
        for name, cc, sec in res:
            if name not in info or (not info[name][0] and cc):
                info[name] = (cc, sec)
            for x in a['aff'].split('; '):
                if x:
                    aliases[name][raw_org(x)] += 1
            frac[name] += 1 / n / len(res)
            if name not in insts:
                insts.append(name)
    p['insts'], p['frac'] = insts, frac

NA = len(AREAS)
stat = defaultdict(lambda: {'p': 0, 'f': 0.0, 'a': [0] * NA, 'y': [0] * len(YEARS)})
for p in PAP:
    for name in p['insts']:
        s = stat[name]
        s['p'] += 1
        s['f'] += p['frac'][name]
        s['a'][p['area']] += 1
        s['y'][YI[p['year']]] += 1
names = sorted(info, key=lambda k: (-stat[k]['p'], -stat[k]['f'], k))
rank, prev = 0, None
INST = []
for i, name in enumerate(names):
    s = stat[name]
    if s['p'] != prev:
        rank, prev = i + 1, s['p']
    cc, sec = info[name]
    al = [a for a, _ in aliases[name].most_common() if a and a != name][:12]
    x = {'n': name, 'p': s['p'], 'f': round(s['f'], 1), 's': sec, 'a': s['a'], 'y': s['y'], 'r': rank}
    if cc:
        x['c'], x['g'] = cc, COUNTRY.get(cc, cc)
    if al:
        x['k'] = al
    if name in curated:
        x['cur'] = 1
    INST.append(x)
IDX = {x['n']: i for i, x in enumerate(INST)}
area_tot = [sum(1 for p in PAP if p['area'] == i) for i in range(NA)]
countries = Counter()
for p in PAP:
    for c in {info[n][0] for n in p['insts'] if info[n][0]}:
        countries[c] += 1

# ---------------- authors (ORCID, then OpenAlex author ID, then name; same name + shared institution = same person) ----------------
def norm_name(s):
    s = unicodedata.normalize('NFKD', s)
    return re.sub(r'[^a-z ]+', '', ''.join(c for c in s if not unicodedata.combining(c)).lower().replace('-', ' ')).strip()


parent = {}
def find(k):
    while parent.setdefault(k, k) != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k
def union(a, b):
    parent[find(a)] = find(b)


def compatible(n1, n2):
    """Same surname, and given names agree word by word (an initial matches a full name)."""
    f1, _, g1 = n1.partition(','); f2, _, g2 = n2.partition(',')
    if norm_name(f1) != norm_name(f2):
        return False
    return all(x.startswith(y) or y.startswith(x) for x, y in zip(norm_name(g1).split(), norm_name(g2).split()))


# IEEE sometimes deposits one author's ORCID on a co-author too, so an ID only counts when the
# name fits the name most often seen with that ID
id_names = defaultdict(Counter)
for p in PAP:
    for a in p['authors']:
        for k in (f'orcid:{a["orcid"]}' if a['orcid'] else None, f'oa:{a["oa_id"]}' if a['oa_id'] else None):
            if k:
                id_names[k][a['name']] += 1
slots = []  # (paper idx, author idx, key)
for pi, p in enumerate(PAP):
    for ai, a in enumerate(p['authors']):
        keys = [f'orcid:{a["orcid"]}' if a['orcid'] else None, f'oa:{a["oa_id"]}' if a['oa_id'] else None]
        keys = [k for k in keys if k and compatible(a['name'], id_names[k].most_common(1)[0][0])]
        keys = keys or [f'name:{norm_name(a["name"])}:{pi}']
        for k in keys[1:]:
            union(keys[0], k)
        slots.append((pi, ai, keys[0]))
# same normalized name and a shared institution -> same person
by_name = defaultdict(lambda: defaultdict(set))
for pi, ai, k in slots:
    a = PAP[pi]['authors'][ai]
    by_name[norm_name(a['name'])][find(k)].update(a['insts'])
for nm, groups in by_name.items():
    g = list(groups.items())
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            if g[i][1] & g[j][1]:
                union(g[i][0], g[j][0])
people = defaultdict(list)
for pi, ai, k in slots:
    people[find(k)].append((pi, ai))
AUTH, AI = [], {}
order = sorted(people, key=lambda r: Counter(PAP[pi]['authors'][ai]['name'] for pi, ai in people[r]).most_common(1)[0][0])
used_ids = set()
for r in order:
    sl = sorted(people[r], key=lambda t: PAP[t[0]]['date'], reverse=True)
    name = Counter(PAP[pi]['authors'][ai]['name'] for pi, ai in sl).most_common(1)[0][0]
    latest = PAP[sl[0][0]]['authors'][sl[0][1]]
    insts = []
    for pi, ai in sl:
        for n_ in PAP[pi]['authors'][ai]['insts']:
            if n_ not in insts:
                insts.append(n_)
    orcid = next((PAP[pi]['authors'][ai]['orcid'] for pi, ai in sl if PAP[pi]['authors'][ai]['orcid']), '')
    oaid = next((PAP[pi]['authors'][ai]['oa_id'] for pi, ai in sl if PAP[pi]['authors'][ai]['oa_id']), '')
    sid = re.sub(r'[^a-z0-9]+', '-', norm_name(name)).strip('-') or 'author'
    base, k = sid, 2
    while sid in used_ids:
        sid, k = f'{base}-{k}', k + 1
    used_ids.add(sid)
    for t in sl:
        AI[t] = len(AUTH)
    AUTH.append([name, sid, ', '.join(latest['insts'][:2]), [IDX[n_] for n_ in insts if n_ in IDX], orcid, oaid])
print('authors', len(AUTH), 'from', len(slots), 'author slots')

meta = {
    'journal': 'IEEE L-CSS', 'full': 'IEEE Control Systems Letters', 'issn': '2475-1456',
    'papers': len(PAP), 'institutions': len(INST), 'years': YEARS,
    'authors': len(AUTH), 'snapshot': SNAPSHOT, 'program': JOURNAL,
    'early': sum(p['early'] for p in PAP),
    'with_arxiv': sum(1 for p in PAP if p['arxiv'] or LINKS.get(p['id'], {}).get('arxiv')),
    'with_code': sum(1 for p in PAP if LINKS.get(p['id'], {}).get('code')),
    'open_access': sum(p['open_access'] for p in PAP),
    'industry_share': round(sum(1 for p in PAP if any(info[n][1] == 'I' for n in p['insts'])) / len(PAP), 4),
    'countries': [[c, COUNTRY.get(c, c), n] for c, n in countries.most_common()],
    'areas': [{'name': a[0], 'short': a[1], 'color': a[2], 'total': area_tot[i]} for i, a in enumerate(AREAS)],
    'year_totals': [sum(1 for p in PAP if p['year'] == y) for y in YEARS],
}
def first_last(n):
    i = n.find(', ')
    return n if i < 0 else n[i + 2:] + ' ' + n[:i]


def vol(p):
    s = f"Vol. {p['volume']}" if p['volume'] else ''
    return s + (f", pp. {p['pages'].replace('-', '–')}" if p['pages'] else '')


# most cited papers of all time: [title, doi, year, citations, authors, volume/pages]
meta['top_cited'] = [[p['title'], p['id'], p['year'], p.get('cites', 0),
                      ', '.join(first_last(a['name']) for a in p['authors'][:3]) + (' et al.' if len(p['authors']) > 3 else ''), vol(p)]
                     for p in sorted(PAP, key=lambda p: (-p.get('cites', 0), p['date']))[:10]]
(site / 'data.js').write_text('window.LCSS=' + json.dumps({'meta': meta, 'inst': INST}, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------- papers.js + papers.bin ----------------
def cite(p):
    if p['early']:
        return 'Early access'
    s = f"Vol. {p['volume']}" if p['volume'] else ''
    if p['pages']:
        s += f", pp. {p['pages'].replace('-', '–')}"
    return s


rows = []
for pi, p in enumerate(PAP):
    lk = LINKS.get(p['id'], {})
    rows.append([p['title'], [IDX[n] for n in p['insts']], p['area'], p['id'], p['year'], cite(p), 1 if p['early'] else 0,
                 1 if p['open_access'] else 0, [AI[(pi, ai)] for ai in range(len(p['authors']))], p['date'],
                 p['arxiv'] or lk.get('arxiv') or '', lk.get('code') or [], p.get('cites', 0)])
(site / 'papers.js').write_text('window.PAPERS=' + json.dumps({
    'n': len(rows), 'dim': int(E.shape[1]), 'model': 'Xenova/bge-small-en-v1.5', 'authors': AUTH, 'rows': rows},
    ensure_ascii=False, separators=(',', ':')) + ';\n')
scale = np.abs(E).max(axis=1) / 127.0
Q = np.clip(np.round(E / scale[:, None]), -127, 127).astype(np.int8)
with open(site / 'papers.bin', 'wb') as f:
    f.write(scale.astype('<f4').tobytes())
    f.write(Q.tobytes())

# ---------------- CSVs ----------------
with open(site / 'lcss_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'institution', 'papers', 'pct_of_papers', 'fractional_papers', 'country', 'sector']
               + [a[0] for a in AREAS] + [str(y) for y in YEARS])
    for x in INST:
        w.writerow([x['r'], x['n'], x['p'], round(100 * x['p'] / len(PAP), 2), x['f'], x.get('c', ''),
                    'industry' if x['s'] == 'I' else 'academia'] + x['a'] + x['y'])
with open(site / 'lcss_papers.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['doi', 'title', 'date', 'year', 'volume', 'pages', 'early_access', 'open_access', 'authors',
                'institutions', 'area', 'arxiv', 'code', 'citations', 'url'])
    for p, r in zip(PAP, rows):
        w.writerow([p['id'], p['title'], p['date'], p['year'], p['volume'], p['pages'], int(p['early']), int(p['open_access']),
                    '; '.join(a['name'] for a in p['authors']), '; '.join(p['insts']), AREAS[p['area']][0],
                    f'https://arxiv.org/abs/{r[10]}' if r[10] else '', ' '.join(r[11]), r[12], f"https://doi.org/{p['id']}"])

print(f"papers {len(PAP)}, institutions {len(INST)}, countries {len(countries)}, years {YEARS[0]}–{YEARS[-1]}")
print('areas', [(a[1], area_tot[i]) for i, a in enumerate(AREAS)])
print('top 25', [(x['r'], x['n'], x['p']) for x in INST[:25]])
print('top industry', [(x['n'], x['p']) for x in INST if x['s'] == 'I'][:12])
print('countries', countries.most_common(12), 'industry share', meta['industry_share'])
print('institutions without country', sum(1 for x in INST if not x.get('c')), 'of', len(INST))
