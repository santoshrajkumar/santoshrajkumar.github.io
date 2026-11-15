"""Build the CoRL 2026 Explorer data files.

Usage: python3 -I build.py <corl2026_papers.json> <raw_dir> <emb.npy> <site_dir>
Reads the merged paper list (scripts/tally_merge.py, plus OpenAlex / arXiv affiliations), OpenReview author IDs
from the gisbi-kim snapshot in raw/, and bge-small-en-v1.5 embeddings (scripts/embed.py). Writes data.js,
papers.js, papers.bin, corl2026_institutions.csv and corl2026_explorer_papers.csv into <site_dir>.
"""
import csv, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import institutions as I  # noqa: E402

src, raw, embf, site = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
D = json.loads(src.read_text())
PAP, SESS = D['papers'], D['sessions']
E = np.load(embf)
assert json.loads(Path(str(embf) + '.ids.json').read_text()) == [p['id'] for p in PAP], 'emb.npy is stale: re-run embed.py'
SNAPSHOT = '2026-11-14'
PROGRAM = 'https://www.corl.org/program/accepted-papers'

# ---------------- research areas: CoRL's official subject areas (each paper's primary area), grouped ----------------
AREAS = [  # (name, short, color, [official subject areas])
    ('Robot manipulation', 'Manipulation', '#9d0208', ['Robot manipulation']),
    ('Reinforcement learning & control', 'RL & control', '#e63946', ['Reinforcement learning for physical robot control', 'Model-based and model-free learning for robotic control']),
    ('Representation learning for perception & control', 'Representations', '#f4845f', ['Learning representations for robotic perception and control']),
    ('Imitation learning', 'Imitation', '#f9c74f', ['Imitation learning (behavioral cloning, inverse RL)']),
    ('Robot foundation models & VLAs', 'Foundation models', '#2b2d42', ['Robot foundation models and general-purpose knowledge systems']),
    ('Video & latent world models', 'World models', '#6a040f', ['Video models and latent world models for robot learning']),
    ('Multimodal perception & robot vision', 'Perception', '#577590', ['Multimodal perception, sensor fusion, and robot vision']),
    ('Learning & planning, TAMP', 'Planning', '#277da1', ['Combination of learning and planning in robotics', 'Task and motion planning']),
    ('Data generation, benchmarks & datasets', 'Data & benchmarks', '#4d908e', ['Benchmarks and datasets for robot learning', 'Robotic data generation']),
    ('Navigation & locomotion', 'Nav & locomotion', '#9b5de5', ['Robot navigation and locomotion']),
    ('Human-robot interaction & language', 'HRI & language', '#c77dff', ['Human-robot interaction and natural language instruction']),
    ('Autonomous driving & flight', 'Driving & flight', '#e85d75', ['Autonomous driving and flight']),
    ('Sim-to-real transfer', 'Sim-to-real', '#43aa8b', ['Sim-to-real transfer']),
    ('Safety, evaluation & red teaming', 'Safety & eval', '#90be6d', ['Robot safety, alignment, and safe learning-based systems', 'Policy evaluation, adversarial scenarios generation, and red teaming']),
    ('Systems, hardware & sensors', 'Systems & hardware', '#f28482', ['Robot systems, hardware, and sensors for learning', 'Hardware design and optimization']),
    ('Uncertainty & theory', 'Uncertainty & theory', '#2a9d8f', ['Probabilistic learning and uncertainty in robotics', 'Theoretical foundations of robot learning']),
]
SUB2A = {s: i for i, a in enumerate(AREAS) for s in a[3]}
NA = len(AREAS)
OFFICIAL = set(SUB2A)


def area_of(p):
    for k in p['keywords']:
        if k in SUB2A:
            return SUB2A[k]
    raise SystemExit(f"no official subject area for {p['id']}: {p['keywords']}")


for p in PAP:
    p['area'] = area_of(p)
    p['free_kw'] = [k for k in p['keywords'] if k not in OFFICIAL]

# ---------------- DSC labels (NeurIPS 2026 DSC Explorer rubric, scripts/dsc_rubric.md) ----------------
DSC = [  # (code, name, short, color, tier) as in the NeurIPS DSC Explorer
    ('OC', 'Optimal control & MPC', 'Optimal/MPC', '#1d4ed8', 'core'),
    ('ID', 'System identification & learned dynamics for control', 'Identification', '#0ea5e9', 'core'),
    ('SF', 'Stability, safety & certificates', 'Safety', '#dc2626', 'core'),
    ('ES', 'Estimation & filtering', 'Estimation', '#7c3aed', 'core'),
    ('LC', 'Learning-based & adaptive control theory', 'Learning-based control', '#0f766e', 'core'),
    ('RC', 'Robotics & embodied control', 'Robotics', '#ea580c', 'core'),
    ('MB', 'Model-based RL & world models', 'Model-based RL', '#f59e0b', 'adjacent'),
    ('NO', 'Neural ODE/PDE surrogates & physics-informed dynamics', 'Neural ODE/PDE', '#10b981', 'adjacent'),
    ('TD', 'Dynamical-systems view of learning', 'Learning dynamics', '#64748b', 'adjacent'),
    ('TS', 'Time series & dynamical-system reconstruction', 'Time series', '#db2777', 'adjacent'),
    ('SD', 'Sequential decision making close to control', 'Decision making', '#a16207', 'adjacent'),
]
DSC_I = {d[0]: i for i, d in enumerate(DSC)}
DSC_DIR = src.parent / 'work' / 'dsc'
LBL = {}
for f in sorted((DSC_DIR / 'labels').glob('batch_*.json')) if (DSC_DIR / 'labels').exists() else []:
    for l in json.loads(f.read_text()): LBL[l['id']] = l
if (DSC_DIR / 'overrides.json').exists():
    for pid, l in json.loads((DSC_DIR / 'overrides.json').read_text()).items(): LBL[pid] = {**LBL.get(pid, {}), **l, 'id': pid}
for p in PAP:
    l = LBL.get(p['id'], {})
    p['dsc_tier'] = {'core': 2, 'adjacent': 1}.get(l.get('tier'), 0)
    p['dsc_sub'] = DSC_I.get(l.get('sub'), -1) if p['dsc_tier'] else -1
    p['dsc_reason'] = l.get('reason', '')

# ---------------- institutions ----------------
EXTRA = '\n'.join((Path(__file__).parent / f).read_text() for f in ('institutions_corl.txt', 'institutions_extra.txt'))
extra_rules = []
for line in EXTRA.strip().splitlines():
    line = line.strip()
    if not line or line.startswith('#'): continue
    name, cc, sec, pats = line.split('|', 3)
    rx = re.compile(r'(?<![a-z0-9])(?:' + '|'.join(x.strip() for x in pats.split(';')) + r')(?![a-z0-9])')
    extra_rules.append((name, cc, sec, rx))
I.RULES[:0] = extra_rules
resolve, RULES = I.resolve, I.RULES
curated = {r[0] for r in RULES}
OA_CC = {'US', 'CN', 'GB', 'DE', 'FR', 'CH', 'JP', 'KR', 'SG', 'HK', 'CA', 'IT', 'NL', 'AU', 'IN', 'IL', 'SE', 'TW', 'ES', 'AT', 'BE', 'DK'}

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
    'DZ': 'Algeria', 'KZ': 'Kazakhstan', 'UA': 'Ukraine', 'NZ': 'New Zealand', 'TH': 'Thailand', 'ID': 'Indonesia',
    'MY': 'Malaysia', 'BG': 'Bulgaria', 'ZA': 'South Africa', 'IR': 'Iran', 'BD': 'Bangladesh', 'NG': 'Nigeria', 'KE': 'Kenya',
}

info, aliases = {}, defaultdict(Counter)


CTRY_SUFFIX = re.compile(r'\s*\((' + '|'.join(re.escape(v) for v in COUNTRY.values()) + r'|United States|China|Japan|Germany|Switzerland|Belgium)\)\s*$')


LIKELY_CO = re.compile(r'(robotics?|dynamics|technolog|intelligence|\.ai\b|\bai\b|\binc\b|corp|motors?|automotive|systems)', re.I)
ACADEMIC = re.compile(r'(universit|institut|academy|college|school|laborator|\blab\b|cent(er|re)|association|hospital|foundation|ministry|national)', re.I)


def res_list(names, countries=()):
    """Resolve a list of institution strings; unmatched names keep the author's single country when known.
    OpenAlex disambiguation suffixes such as 'Honda (Japan)' are dropped first."""
    out = []
    for raw_name in names:
        for name, cc, sec in resolve(CTRY_SUFFIX.sub('', raw_name)):
            if not cc and name not in curated and len(set(countries)) == 1:
                cc = list(countries)[0]
            if name not in curated and sec == 'A' and LIKELY_CO.search(name) and not ACADEMIC.search(name):
                sec = 'I'   # uncurated startups ("Noetix Robotics", "Spirit.AI") are companies, not academia
            if name not in info or (not info[name][0] and cc):
                info[name] = (cc, sec)
            aliases[name][raw_name.strip()] += 1
            if name not in out:
                out.append(name)
    return out


# OpenReview author ids (gisbi-kim snapshot of OpenReview); e-mail ids are hashed, never published
G = {p['id']: p for p in json.loads((raw / 'gisbi_corl2026_data.json').read_text())['papers']}


def author_id(pid, j, name):
    ids = G.get(pid, {}).get('authorids') or []
    a = ids[j] if j < len(ids) and len(ids) == len(G[pid]['authors']) else ''
    if a.startswith('~'):
        return a
    return 'x' + hashlib.sha1(((a or name).lower()).encode()).hexdigest()[:10]


for p in PAP:
    per = {a['name']: a for a in p.get('author_affiliations') or []}
    p['au'] = []
    frac = defaultdict(float)
    n = len(p['authors']) or 1
    for j, name in enumerate(p['authors']):
        a = per.get(name) or {}
        insts = res_list(a.get('institutions') or [], a.get('countries') or [])
        p['au'].append([name, insts, author_id(p['id'], j, name)])
        for k in insts:
            frac[k] += 1 / n / len(insts)
    by_author = [k for a in p['au'] for k in a[1]]
    paper_level = res_list(p.get('institutions_gisbi') or [])
    insts = list(dict.fromkeys(by_author + paper_level))
    if not by_author and paper_level:   # no per-author data: split the paper evenly across its listed institutions
        for k in paper_level:
            frac[k] += 1 / len(paper_level)
    p['insts'], p['frac'] = insts, frac

stat = defaultdict(lambda: {'p': 0, 'c': 0, 'f': 0.0, 'a': [0] * NA})
for p in PAP:
    hl = p['presentation'] in ('Oral', 'Spotlight')
    for name in p['insts']:
        s = stat[name]; s['p'] += 1; s['f'] += p['frac'].get(name, 0); s['a'][p['area']] += 1
        if hl: s['c'] += 1
names = sorted(info, key=lambda k: (-stat[k]['p'], -stat[k]['f'], k))
names = [k for k in names if stat[k]['p']]
rank, prev, INST = 0, None, []
for i, name in enumerate(names):
    s = stat[name]
    if s['p'] != prev: rank, prev = i + 1, s['p']
    cc, sec = info[name]
    al = [a for a, _ in aliases[name].most_common() if a != name][:12]
    x = {'n': name, 'p': s['p'], 'core': s['c'], 'f': round(s['f'], 1), 's': sec, 'a': s['a'], 'r': rank}
    if cc: x['c'], x['g'] = cc, COUNTRY.get(cc, cc)
    if al: x['k'] = al
    if name in curated: x['cur'] = 1
    INST.append(x)
IDX = {x['n']: i for i, x in enumerate(INST)}
area_tot = [sum(1 for p in PAP if p['area'] == i) for i in range(NA)]
countries = Counter()
for p in PAP:
    for c in {info[n][0] for n in p['insts'] if info[n][0]}: countries[c] += 1
n_hl = sum(1 for p in PAP if p['presentation'] in ('Oral', 'Spotlight'))
AX = lambda p: (re.search(r'(\d{4}\.\d{4,5})', p.get('arxiv') or '') or [None, ''])[1]
n_auth_aff = sum(1 for p in PAP for a in p['au'] if a[1])
meta = {
    'conference': 'CoRL 2026', 'full': 'Conference on Robot Learning 2026', 'where': 'Austin, Texas', 'when': 'November 9–12, 2026',
    'papers': len(PAP), 'core': n_hl, 'orals': sum(1 for p in PAP if p['presentation'] == 'Oral'),
    'spotlights': sum(1 for p in PAP if p['presentation'] == 'Spotlight'), 'all': len(PAP), 'institutions': len(INST),
    'authors': len({a[2] for p in PAP for a in p['au']}), 'snapshot': SNAPSHOT, 'program': PROGRAM,
    'with_arxiv': sum(1 for p in PAP if AX(p)), 'with_code': sum(1 for p in PAP if p.get('code')),
    'with_inst': sum(1 for p in PAP if p['insts']), 'author_slots': sum(len(p['au']) for p in PAP), 'author_slots_aff': n_auth_aff,
    'industry_share': round(sum(1 for p in PAP if any(info[n][1] == 'I' for n in p['insts'])) / max(1, len(PAP)), 4),
    'countries': [[c, COUNTRY.get(c, c), n] for c, n in countries.most_common()],
    'areas': [{'name': a[0], 'short': a[1], 'color': a[2], 'subs': a[3], 'total': area_tot[i]} for i, a in enumerate(AREAS)],
    'dsc': {'labelled': sum(1 for p in PAP if p['id'] in LBL), 'core': sum(1 for p in PAP if p['dsc_tier'] == 2),
            'adjacent': sum(1 for p in PAP if p['dsc_tier'] == 1),
            'subs': [{'code': d[0], 'name': d[1], 'short': d[2], 'color': d[3], 'tier': d[4],
                      'total': sum(1 for p in PAP if p['dsc_sub'] == i)} for i, d in enumerate(DSC)]},
}
(site / 'data.js').write_text('window.CDC=' + json.dumps({'meta': meta, 'inst': INST}, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------- authors (OpenReview profile ids) ----------------
slots = defaultdict(list)
for p in PAP:
    for name, insts, aid in p['au']: slots[aid].append((name, tuple(insts)))
AUTH, AI = [], {}
for aid in sorted(slots, key=lambda q: Counter(n for n, _ in slots[q]).most_common(1)[0][0].split(' ')[-1]):
    sl = slots[aid]
    name = Counter(n for n, _ in sl).most_common(1)[0][0]
    insts = []
    for _, ii in sl:
        for k in ii:
            if k not in insts: insts.append(k)
    AI[aid] = len(AUTH)
    AUTH.append([name, aid, ' · '.join(insts[:3]), [IDX[k] for k in insts if k in IDX]])

# ---------------- sessions ----------------
WD = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4}
MON = {'11': 'Nov'}
def when_parts(w):   # "Mon 11/9, 5:00–6:30 PM" -> ("Mon Nov 9", "5:00–6:30 PM", 0)
    m = re.match(r'(\w{3}) (\d+)/(\d+),\s*(.+)$', w)
    if not m: return '', w, 9
    return f"{m.group(1)} {MON.get(m.group(2), m.group(2))} {m.group(3)}", m.group(4), WD.get(m.group(1), 9)
ses_rows, SI = [], {}
for s in SESS:
    day, tm, wd = when_parts(s['when'])
    typ = {'poster': 0, 'spotlight': 1, 'oral': 2}[s['kind']]
    SI[s['name']] = len(ses_rows)
    ses_rows.append([s['code'] if s['kind'] != 'poster' else 'Poster ' + s['code'][1:], s['name'], day, tm, s['venue'], typ, wd, [], s.get('rooms') or []])

# ---------------- papers.js + papers.bin ----------------
PRES = {'Poster': 0, 'Spotlight': 1, 'Oral': 2}
rows = []
for p in PAP:
    talk = (p['oral_session'] or p['spotlight_session']).split('; ')[0]
    rows.append([p['title'], [IDX[n] for n in p['insts']], p['area'], p['id'], SI.get(p['poster_session'], -1),
                 PRES[p['presentation']], [], 1 if p['presentation'] != 'Poster' else 0, [AI[a[2]] for a in p['au']],
                 f"{p['poster_session']}-{(p['poster_number'] or 0):03d}", AX(p), p.get('code') or [], p['id'],
                 ' · '.join(p['free_kw'][:6]), p['poster_number'] or 0, SI.get(talk, -1), (p.get('project') or [''])[0],
                 p['dsc_tier'], p['dsc_sub'], p['dsc_reason']])
(site / 'papers.js').write_text('window.PAPERS=' + json.dumps({
    'n': len(rows), 'dim': int(E.shape[1]), 'model': 'Xenova/bge-small-en-v1.5', 'types': ['Poster session', 'Spotlight session', 'Oral session'],
    'pres': ['Poster', 'Spotlight', 'Oral'], 'keywords': [], 'sessions': ses_rows, 'authors': AUTH, 'rows': rows},
    ensure_ascii=False, separators=(',', ':')) + ';\n')
scale = np.abs(E).max(axis=1) / 127.0
Q = np.clip(np.round(E / scale[:, None]), -127, 127).astype(np.int8)
with open(site / 'papers.bin', 'wb') as f:
    f.write(scale.astype('<f4').tobytes()); f.write(Q.tobytes())

# ---------------- CSVs ----------------
with open(site / 'corl2026_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'institution', 'papers', 'orals_and_spotlights', 'pct_of_papers', 'fractional_papers', 'country', 'sector'] + [a[0] for a in AREAS])
    for x in INST:
        w.writerow([x['r'], x['n'], x['p'], x['core'], round(100 * x['p'] / len(PAP), 2), x['f'], x.get('c', ''), 'industry' if x['s'] == 'I' else 'academia'] + x['a'])
with open(site / 'corl2026_explorer_papers.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['openreview_id', 'title', 'presentation', 'area', 'primary_subject_area', 'keywords', 'poster_session', 'poster_number', 'talk_session',
                'authors', 'author_institutions', 'institutions', 'openreview_url', 'arxiv', 'code', 'project', 'dsc_tier', 'dsc_subcategory', 'dsc_reason'])
    for p in PAP:
        w.writerow([p['id'], p['title'], p['presentation'], AREAS[p['area']][0], next(k for k in p['keywords'] if k in OFFICIAL), '; '.join(p['keywords']),
                    p['poster_session'], p['poster_number'], p['oral_session'] or p['spotlight_session'], '; '.join(p['authors']),
                    '; '.join(f"{a[0]} ({' / '.join(a[1])})" if a[1] else a[0] for a in p['au']), '; '.join(p['insts']),
                    p['openreview'], p.get('arxiv') or '', ' '.join(p.get('code') or []), ' '.join(p.get('project') or []),
                    ['out', 'adjacent', 'core'][p['dsc_tier']], DSC[p['dsc_sub']][1] if p['dsc_sub'] >= 0 else '', p['dsc_reason']])
DP = [p for p in PAP if p['dsc_tier']]
dstat = defaultdict(lambda: [0, 0])
for p in DP:
    for k in p['insts']: dstat[k][0] += 1; dstat[k][1] += p['dsc_tier'] == 2
with open(site / 'corl2026_dsc_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['institution', 'dsc_papers', 'core_papers', 'country', 'sector'])
    for k, (a, c) in sorted(dstat.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0])):
        w.writerow([k, a, c, info[k][0], 'industry' if info[k][1] == 'I' else 'academia'])

print(f"DSC: labelled {meta['dsc']['labelled']}, core {meta['dsc']['core']}, adjacent {meta['dsc']['adjacent']};", [(d['short'], d['total']) for d in meta['dsc']['subs']])
print('DSC top institutions', [(k, v) for k, v in sorted(dstat.items(), key=lambda kv: -kv[1][0])[:12]])
print(f"papers {len(PAP)} (orals+spotlights {n_hl}); institutions {len(INST)}; authors {len(AUTH)}; sessions {len(ses_rows)}")
print(f"papers with institutions {meta['with_inst']}; author slots with affiliation {n_auth_aff}/{meta['author_slots']}")
print('areas', [(a[1], area_tot[i]) for i, a in enumerate(AREAS)])
print('top 25', [(x['r'], x['n'], x['p']) for x in INST[:25]])
print('top industry', [(x['n'], x['p']) for x in INST if x['s'] == 'I'][:12])
print('countries', countries.most_common(12), 'industry share', meta['industry_share'], 'no-country insts', sum(1 for x in INST if not x.get('c')))
unres = Counter()
for p in PAP:
    for a in p.get('author_affiliations') or []:
        for raw_name in a['institutions']:
            if all(n not in curated for n, _, _ in resolve(CTRY_SUFFIX.sub('', raw_name))): unres[raw_name] += 1
    for raw_name in p.get('institutions_gisbi') or []:
        if all(n not in curated for n, _, _ in resolve(CTRY_SUFFIX.sub('', raw_name))): unres[raw_name] += 1
print('uncurated affiliations (top 60):', unres.most_common(60))
