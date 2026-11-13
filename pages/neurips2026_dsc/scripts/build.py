"""Build the NeurIPS 2026 DSC Explorer data files.

Usage: venv/bin/python -I build.py <neurips.json> <work_dir> <site_dir> [links.json]
Reads work_dir/final_labels.json (tier + subcategory per paper, from scripts/classify/) and work_dir/emb.npy
(bge-small-en-v1.5 embeddings from recall.py). Writes data.js, papers.js, papers.bin,
neurips2026_dsc_institutions.csv and neurips2026_dsc_papers.csv into <site_dir>.
"""
import csv, json, re, sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import institutions as I  # noqa: E402

src, work, site = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
LINKS = json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv) > 4 else {}
site.mkdir(parents=True, exist_ok=True)
D = json.load(src.open()); ALL = D['papers']
LAB = json.load((work / 'final_labels.json').open())
E_ALL = np.load(work / 'emb.npy'); assert E_ALL.shape[0] == len(ALL)
SNAPSHOT = '2026-11-12'
PROGRAM = 'https://neurips.cc/virtual/2026/'

# ---------------- DSC subcategories (= research areas of this site) ----------------
AREAS = [  # (name, short, color, code, tier)
    ('Optimal control & MPC', 'Optimal/MPC', '#1d4ed8', 'OC', 'core'),
    ('System identification & learned dynamics for control', 'Identification', '#0ea5e9', 'ID', 'core'),
    ('Stability, safety & certificates', 'Safety', '#dc2626', 'SF', 'core'),
    ('Estimation & filtering', 'Estimation', '#7c3aed', 'ES', 'core'),
    ('Learning-based & adaptive control theory', 'Learning-based control', '#0f766e', 'LC', 'core'),
    ('Robotics & embodied control', 'Robotics', '#ea580c', 'RC', 'core'),
    ('Model-based RL & world models', 'Model-based RL', '#f59e0b', 'MB', 'adjacent'),
    ('Neural ODE/PDE surrogates & physics-informed dynamics', 'Neural ODE/PDE', '#10b981', 'NO', 'adjacent'),
    ('Dynamical-systems view of learning', 'Learning dynamics', '#64748b', 'TD', 'adjacent'),
    ('Time series & dynamical-system reconstruction', 'Time series', '#db2777', 'TS', 'adjacent'),
    ('Sequential decision making close to control', 'Decision making', '#a16207', 'SD', 'adjacent'),
]
CODE2A = {a[3]: i for i, a in enumerate(AREAS)}
NA = len(AREAS)

# extra institution rules for NeurIPS affiliations (OpenReview profile institution names); applied before the CDC table
EXTRA = (Path(__file__).parent / 'institutions_extra.txt').read_text() if (Path(__file__).parent / 'institutions_extra.txt').exists() else ''
extra_rules = []
for line in EXTRA.strip().splitlines():
    line = line.strip()
    if not line or line.startswith('#'): continue
    name, cc, sec, pats = line.split('|', 3)
    rx = re.compile(r'(?<![a-z0-9])(?:' + '|'.join(p.strip() for p in pats.split(';')) + r')(?![a-z0-9])')
    extra_rules.append((name, cc, sec, rx))
I.RULES[:0] = extra_rules
resolve, RULES = I.resolve, I.RULES

PAP = [p for p in ALL if LAB.get(p['id'], {}).get('tier') in ('core', 'adjacent')]
IDX_ALL = {p['id']: i for i, p in enumerate(ALL)}
E = E_ALL[[IDX_ALL[p['id']] for p in PAP]]
for p in PAP:
    l = LAB[p['id']]; p['tier'] = l['tier']; p['area'] = CODE2A[l['sub']]; p['reason'] = l.get('reason', '')

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
    'DZ': 'Algeria', 'KZ': 'Kazakhstan', 'UA': 'Ukraine', 'NZ': 'New Zealand', 'TH': 'Thailand', 'ID': 'Indonesia',
    'MY': 'Malaysia', 'ZA': 'South Africa', 'IR': 'Iran', 'BD': 'Bangladesh', 'NG': 'Nigeria', 'KE': 'Kenya',
}
curated = {r[0] for r in RULES}
info, aliases = {}, defaultdict(Counter)
for p in PAP:
    insts, frac = [], defaultdict(float)
    n = len(p['authors']) or 1
    for a in p['authors']:
        aff = a[1]
        res = resolve(aff) if aff and aff.strip().lower() not in ('none', 'n/a', '-') else []
        for name, cc, sec in res:
            info.setdefault(name, (cc, sec))
            aliases[name][aff.strip()] += 1
            frac[name] += 1 / n / len(res)
            if name not in insts:
                insts.append(name)
    p['insts'], p['frac'] = insts, frac

stat = defaultdict(lambda: {'p': 0, 'c': 0, 'f': 0.0, 'a': [0] * NA})
for p in PAP:
    for name in p['insts']:
        s = stat[name]; s['p'] += 1; s['f'] += p['frac'][name]; s['a'][p['area']] += 1
        if p['tier'] == 'core': s['c'] += 1
names = sorted(info, key=lambda k: (-stat[k]['p'], -stat[k]['f'], k))
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
n_core = sum(1 for p in PAP if p['tier'] == 'core')
meta = {
    'conference': 'NeurIPS 2026', 'full': 'Thirty-Ninth Annual Conference on Neural Information Processing Systems',
    'where': 'Sydney · Atlanta · Paris', 'when': 'December 2026', 'track': 'Main track · Dynamic Systems & Control',
    'papers': len(PAP), 'core': n_core, 'adjacent': len(PAP) - n_core, 'all': len(ALL), 'institutions': len(INST),
    'sessions': len({s for p in PAP for s in p['sessions']}), 'authors': len({a[2] for p in PAP for a in p['authors']}),
    'snapshot': SNAPSHOT, 'program': PROGRAM,
    'with_arxiv': sum(1 for p in PAP if LINKS.get(p['id'], {}).get('arxiv')),
    'with_code': sum(1 for p in PAP if LINKS.get(p['id'], {}).get('code')),
    'industry_share': round(sum(1 for p in PAP if any(info[n][1] == 'I' for n in p['insts'])) / max(1, len(PAP)), 4),
    'countries': [[c, COUNTRY.get(c, c), n] for c, n in countries.most_common()],
    'areas': [{'name': a[0], 'short': a[1], 'color': a[2], 'code': a[3], 'tier': a[4], 'total': area_tot[i]} for i, a in enumerate(AREAS)],
}
(site / 'data.js').write_text('window.CDC=' + json.dumps({'meta': meta, 'inst': INST}, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------- authors (neurips.cc profile ids) ----------------
slots = defaultdict(list)
for p in PAP:
    for a in p['authors']: slots[a[2]].append((a[0], a[1]))
AUTH, AI = [], {}
for pid in sorted(slots, key=lambda q: Counter(n for n, _ in slots[q]).most_common(1)[0][0].split(' ')[-1]):
    sl = slots[pid]
    name = Counter(n for n, _ in sl).most_common(1)[0][0]
    affs = [a for a, _ in Counter(a for _, a in sl if a).most_common()]
    insts = []
    for aff in affs:
        for n, _, _ in resolve(aff):
            if n not in insts: insts.append(n)
    AI[pid] = len(AUTH)
    AUTH.append([name, pid, affs[0] if affs else '', [IDX[n] for n in insts if n in IDX]])

# ---------------- sessions ----------------
def day_of(iso):
    try: d = datetime.fromisoformat(iso); return d.strftime('%a %b %-d'), d.strftime('%H:%M'), d.weekday()
    except Exception: return '', '', 9
TYPES = ['Poster session', 'Oral session']
sess = {}
for p in PAP:
    for s in p['sessions']:
        sess.setdefault(s, []).append(p)
ses_rows, SI = [], {}
for s in sorted(sess):
    ps = sess[s]
    starts = Counter(p['start'] for p in ps if p['start']).most_common(1)
    day, tm, wd = day_of(starts[0][0]) if starts else ('', '', 9)
    room = Counter(p['room'] for p in ps if p['room']).most_common(1)
    typ = 1 if 'oral' in s.lower() else 0
    m = re.match(r'^(Sydney|Atlanta|Paris)\s+(Poster|Oral) Session (\d+)$', s)
    code = f"{m.group(1)} {'PS' if m.group(2) == 'Poster' else 'OS'}{m.group(3)}" if m else re.sub(r'^Orals? ', 'Oral ', s)[:28]
    SI[s] = len(ses_rows)
    ses_rows.append([code, s, day, tm, room[0][0] if room else '', typ, wd, [], ''])

# ---------------- papers.js + papers.bin ----------------
PRES = {'Poster': 0, 'Spotlight': 1, 'Oral': 2}
rows = []
for p in PAP:
    forum = p['openreview'].split('id=')[-1] if p['openreview'] else ''
    rows.append([p['title'], [IDX[n] for n in p['insts']], p['area'], p['id'], SI[p['sessions'][0]] if p['sessions'] else -1,
                 PRES[p['presentation']], [], 1 if p['tier'] == 'core' else 0, [AI[a[2]] for a in p['authors']], p['start'][:16],
                 LINKS.get(p['id'], {}).get('arxiv') or '', LINKS.get(p['id'], {}).get('code') or [], forum, p['reason']])
(site / 'papers.js').write_text('window.PAPERS=' + json.dumps({
    'n': len(rows), 'dim': int(E.shape[1]), 'model': 'Xenova/bge-small-en-v1.5', 'types': TYPES, 'pres': ['Poster', 'Spotlight', 'Oral'],
    'keywords': [], 'sessions': ses_rows, 'authors': AUTH, 'rows': rows}, ensure_ascii=False, separators=(',', ':')) + ';\n')
scale = np.abs(E).max(axis=1) / 127.0
Q = np.clip(np.round(E / scale[:, None]), -127, 127).astype(np.int8)
with open(site / 'papers.bin', 'wb') as f:
    f.write(scale.astype('<f4').tobytes()); f.write(Q.tobytes())

# ---------------- CSVs ----------------
with open(site / 'neurips2026_dsc_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'institution', 'dsc_papers', 'core_papers', 'pct_of_dsc_papers', 'fractional_papers', 'country', 'sector'] + [a[0] for a in AREAS])
    for x in INST:
        w.writerow([x['r'], x['n'], x['p'], x['core'], round(100 * x['p'] / len(PAP), 2), x['f'], x.get('c', ''), 'industry' if x['s'] == 'I' else 'academia'] + x['a'])
with open(site / 'neurips2026_dsc_papers.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['neurips_id', 'title', 'tier', 'subcategory', 'subcategory_code', 'reason', 'presentation', 'session', 'authors', 'institutions', 'neurips_url', 'openreview_url', 'arxiv', 'unofficial_area_label'])
    for p in sorted(PAP, key=lambda p: (p['tier'] != 'core', p['area'], p['title'])):
        w.writerow([p['id'], p['title'], p['tier'], AREAS[p['area']][0], AREAS[p['area']][3], p['reason'], p['presentation'], ' | '.join(p['sessions']),
                    '; '.join(a[0] for a in p['authors']), '; '.join(p['insts']), p['url'], p['openreview'], LINKS.get(p['id'], {}).get('arxiv') or '', p['jarea']])

print(f"DSC papers {len(PAP)} (core {n_core}, adjacent {len(PAP) - n_core}) of {len(ALL)} main-track; institutions {len(INST)}; authors {len(AUTH)}; sessions {len(ses_rows)}")
print('areas', [(a[1], area_tot[i]) for i, a in enumerate(AREAS)])
print('top 20', [(x['r'], x['n'], x['p']) for x in INST[:20]])
print('top industry', [(x['n'], x['p']) for x in INST if x['s'] == 'I'][:10])
print('countries', countries.most_common(10), 'industry share', meta['industry_share'])
unres = Counter(a[1] for p in PAP for a in p['authors'] if a[1] and all(n not in curated for n, _, _ in resolve(a[1])))
print('uncurated affiliations (top 40):', unres.most_common(40))
