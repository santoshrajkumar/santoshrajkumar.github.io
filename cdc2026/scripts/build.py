"""Build the CDC 2026 Explorer data files from cdc.json.

Usage: venv/bin/python -I build.py <cdc.json> <site_dir>
Writes data.js, papers.js, papers.bin and cdc2026_institutions.csv into <site_dir>.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from institutions import resolve, RULES  # noqa: E402

src, site = Path(sys.argv[1]), Path(sys.argv[2])
# optional: {paper id: {"arxiv": "2604.03086", "code": [urls]}} from scripts/links/
LINKS = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}
site.mkdir(parents=True, exist_ok=True)
D = json.loads(src.read_text())
SES, PAP = D['sessions'], D['papers']
SNAPSHOT = '2026-11-10'
PROGRAM = 'https://css.paperplaza.net/conferences/conferences/CDC26/program/'
TECH = {'Regular Session', 'Invited Session', 'RI Session'}

# ---------------- research areas from official CDC keywords ----------------
AREAS = [
    ('Optimal & predictive control', 'Optimal/MPC', '#9d0208', [
        'Optimal control', 'Predictive control for nonlinear systems', 'Predictive control for linear systems',
        'Constrained control', 'Variational methods']),
    ('Optimization & algorithms', 'Optimization', '#e63946', [
        'Optimization', 'Optimization algorithms', 'Numerical algorithms', 'Computational methods', 'LMIs',
        'Randomized algorithms', 'Evolutionary computing']),
    ('Learning-based & data-driven control', 'Learning', '#f4845f', [
        'Learning-based Control', 'Learning-based control', 'Data driven control', 'Machine learning and control',
        'Machine learning', 'Neural networks', 'Statistical learning', 'Learning', 'AI/LLM and control',
        'Human - AI decision making']),
    ('Reinforcement & multi-agent learning', 'RL', '#f9c74f', [
        'Reinforcement learning', 'Reinforcement Learning', 'Multi-agent learning']),
    ('Safety, security & privacy', 'Safety', '#2b2d42', [
        'Safety-critical control', 'Cyber-Physical Security', 'Resilient Control Systems', 'Control Systems Privacy',
        'Attack Detection', 'Computer/Network Security']),
    ('Hybrid, discrete-event & formal methods', 'Hybrid/formal', '#6a040f', [
        'Hybrid systems', 'Stability of hybrid systems', 'Switched systems', 'Automata', 'Discrete event systems',
        'Supervisory control', 'Petri nets', 'Boolean control networks and logic networks',
        'Formal Verification/Synthesis']),
    ('Nonlinear systems & stability', 'Nonlinear', '#577590', [
        'Nonlinear systems', 'Stability of nonlinear systems', 'Lyapunov methods', 'Algebraic/geometric methods',
        'Backstepping', 'Feedback linearization', 'Nonlinear output feedback', 'Nonholonomic systems',
        'Output regulation', 'Chaotic systems']),
    ('Linear, delay & infinite-dim. systems', 'Linear/PDE', '#277da1', [
        'Linear systems', 'Stability of linear systems', 'Time-varying systems', 'Delay systems',
        'Distributed parameter systems', 'Differential-algebraic systems', 'Behavioural systems',
        'Linear parameter-varying systems', 'Compartmental and Positive systems', 'Model/Controller reduction',
        'Reduced order modeling', 'Sampled-data control', 'Quantized systems']),
    ('Robust & adaptive control', 'Robust/adaptive', '#4d908e', [
        'Robust control', 'Uncertain systems', 'Adaptive control', 'Robust adaptive control', 'Direct adaptive control',
        'Indirect adaptive control', 'Adaptive systems', 'Extremum seeking', 'Variable-structure/sliding-mode control',
        'Iterative learning control', 'PID control', 'Fault tolerant systems']),
    ('Stochastic systems & estimation', 'Estimation', '#9b5de5', [
        'Stochastic systems', 'Stochastic optimal control', 'Markov processes', 'Estimation', 'Filtering',
        'Kalman filtering', 'Observers for nonlinear systems', 'Observers for Linear systems', 'Sensor fusion',
        'Fault detection', 'Fault diagnosis', 'Queueing systems']),
    ('System identification & modeling', 'Identification', '#c77dff', [
        'Identification', 'Nonlinear systems identification', 'Identification for control', 'Subspace methods',
        'Grey-box modeling', 'Modeling', 'Model Validation', 'Closed-loop identification', 'Simulation']),
    ('Game theory & mean-field', 'Games', '#e85d75', [
        'Game theory', 'Learning in Game theory', 'Mean field games', 'Finance']),
    ('Networked & multi-agent systems', 'Networks', '#43aa8b', [
        'Networked control systems', 'Network analysis and control', 'Distributed control', 'Cooperative control',
        'Agents-based systems', 'Control of networks', 'Large-scale systems', 'Decentralized control',
        'Event-triggered/resource-aware control', 'Sensor networks', 'Control over communications',
        'Communication networks', 'Information theory and control', 'Hierarchical control',
        'Agents and autonomous systems']),
    ('Robotics, autonomy & aerospace', 'Robotics', '#90be6d', [
        'Robotics', 'Autonomous systems', 'Autonomous robots', 'Autonomous vehicles', 'Aerospace', 'Flight control',
        'Maritime control', 'Human-in-the-loop control', 'Mechatronics', 'Perception', 'Vision-based control',
        'Visual servo control', 'Automotive control', 'Automotive systems']),
    ('Energy, transportation & applications', 'Energy/apps', '#f28482', [
        'Power systems', 'Energy systems', 'Smart grid', 'Transportation networks', 'Traffic control',
        'Air traffic management', 'Control applications', 'Emerging control applications', 'Process Control',
        'Chemical process control', 'Manufacturing systems and automation', 'Power electronics', 'Power generation',
        'Electrical machine control', 'Building and facility automation', 'Smart cities/houses', 'Fluid flow systems',
        'Flexible structures', 'Smart structures', 'Embedded systems', 'Control software',
        'Control system architecture', 'Computer-aided control design', 'Information technology systems',
        'Intelligent systems', 'Fuzzy systems']),
    ('Biology, medicine & quantum', 'Bio/quantum', '#2a9d8f', [
        'Biological systems', 'Systems biology', 'Biomolecular systems', 'Cellular dynamics',
        'Genetic regulatory systems', 'Metabolic systems', 'Biomedical', 'Healthcare and medical systems',
        'Biologically-inspired methods', 'Biotechnology', 'Quantum information and control',
        'Biological systems, Biologically-inspired methods, Neural dynamics']),
]
KW2A = {k: i for i, a in enumerate(AREAS) for k in a[3]}
allkw = Counter(k for p in PAP for k in p['keywords'])
missing = [k for k in allkw if k not in KW2A]
assert not missing, missing


def area_from_keywords(kws):
    sc = defaultdict(float)
    for j, k in enumerate(kws):
        sc[KW2A[k]] += 1.5 if j == 0 else 1.0
    if not sc:
        return None
    best = max(sc.values())
    for k in kws:  # tie -> earliest keyword
        if sc[KW2A[k]] == best:
            return KW2A[k]


# ---------------- embeddings ----------------
from sentence_transformers import SentenceTransformer  # noqa: E402

texts = [(p['title'] + '. ' + p['abstract']).strip() for p in PAP]
model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
E = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True).astype(np.float32)

for p in PAP:
    p['area'] = area_from_keywords(p['keywords'])
lab = np.array([p['area'] is not None for p in PAP])
LE, LA = E[lab], np.array([p['area'] for p in PAP if p['area'] is not None])
for i, p in enumerate(PAP):  # papers without keywords: vote of 15 nearest keyworded papers
    if p['area'] is None:
        nn = np.argsort(-(LE @ E[i]))[:15]
        p['area'] = int(Counter(LA[nn]).most_common(1)[0][0])
        p['area_guess'] = True

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
    'DZ': 'Algeria', 'KZ': 'Kazakhstan', 'UA': 'Ukraine',
}
curated = {r[0] for r in RULES}
info, aliases = {}, defaultdict(Counter)
for p in PAP:
    insts, frac = [], defaultdict(float)
    n = len(p['authors']) or 1
    for a in p['authors']:
        aff = a[1]
        res = resolve(aff)
        for name, cc, sec in res:
            info.setdefault(name, (cc, sec))
            aliases[name][aff.strip()] += 1
            frac[name] += 1 / n / len(res)
            if name not in insts:
                insts.append(name)
    p['insts'], p['frac'] = insts, frac

NA = len(AREAS)
stat = defaultdict(lambda: {'p': 0, 'f': 0.0, 'a': [0] * NA})
tech = [p for p in PAP if SES[p['session']]['type'] in TECH]
for p in tech:
    for name in p['insts']:
        s = stat[name]
        s['p'] += 1
        s['f'] += p['frac'][name]
        s['a'][p['area']] += 1
names = sorted(info, key=lambda k: (-stat[k]['p'] if k in stat else 1, -(stat[k]['f'] if k in stat else 0), k))
rank, prev = 0, None
INST = []
for i, name in enumerate(names):
    s = stat.get(name, {'p': 0, 'f': 0.0, 'a': [0] * NA})
    if s['p'] != prev:
        rank, prev = i + 1, s['p']
    cc, sec = info[name]
    al = [a for a, _ in aliases[name].most_common() if a != name][:12]
    x = {'n': name, 'p': s['p'], 'f': round(s['f'], 1), 's': sec, 'a': s['a']}
    if cc:
        x['c'], x['g'] = cc, COUNTRY.get(cc, cc)
    if al:
        x['k'] = al
    if name in curated:
        x['cur'] = 1
    x['r'] = rank if s['p'] else None
    INST.append(x)
IDX = {x['n']: i for i, x in enumerate(INST)}
ranked = [x for x in INST if x['p']]
area_tot = [sum(1 for p in tech if p['area'] == i) for i in range(NA)]
countries = Counter()
for p in tech:
    for c in {info[n][0] for n in p['insts'] if info[n][0]}:
        countries[c] += 1

meta = {
    'conference': 'CDC 2026', 'full': '2026 65th IEEE Conference on Decision and Control',
    'where': 'Honolulu, HI, USA', 'when': 'December 15–18, 2026', 'track': 'Technical sessions',
    'papers': len(tech), 'all': len(PAP), 'institutions': len(ranked), 'sessions': sum(1 for s in SES if s['type'] in TECH),
    'authors': len({a[2] for p in tech for a in p['authors']}), 'snapshot': SNAPSHOT, 'program': PROGRAM,
    'with_arxiv': sum(1 for p in tech if LINKS.get(p['id'], {}).get('arxiv')),
    'with_code': sum(1 for p in tech if LINKS.get(p['id'], {}).get('code')),
    'industry_share': round(sum(1 for p in tech if any(info[n][1] == 'I' for n in p['insts'])) / len(tech), 4),
    'countries': [[c, COUNTRY.get(c, c), n] for c, n in countries.most_common()],
    'areas': [{'name': a[0], 'short': a[1], 'color': a[2], 'total': area_tot[i], 'keywords': a[3]} for i, a in enumerate(AREAS)],
}
(site / 'data.js').write_text('window.CDC=' + json.dumps({'meta': meta, 'inst': INST}, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------- papers.js + papers.bin ----------------
# ---------------- authors (PaperPlaza author IDs; same name + shared institution = same person) ----------------
slots = defaultdict(list)  # id -> [(name, affiliation)]
for p in PAP:
    for a in p['authors']:
        slots[a[2]].append((a[0], a[1]))
for x in SES:
    for c in x['chairs']:
        slots[c[2]].append((c[0], c[1]))
def inst_set(pid):
    return {n for _, aff in slots[pid] for n, _, _ in resolve(aff)}
canon = {}
by_name = defaultdict(list)
for pid, sl in slots.items():
    by_name[Counter(n for n, _ in sl).most_common(1)[0][0]].append(pid)
for name, pids in by_name.items():
    groups = []
    for pid in pids:
        for g in groups:
            if inst_set(pid) & set().union(*(inst_set(q) for q in g)):
                g.append(pid)
                break
        else:
            groups.append([pid])
    for g in groups:
        for pid in g:
            canon[pid] = g[0]
AUTH, AI = [], {}
for pid in sorted({canon[p] for p in slots}, key=lambda q: Counter(n for n, _ in slots[q]).most_common(1)[0][0]):
    members = [q for q in slots if canon[q] == pid]
    sl = [x for q in members for x in slots[q]]
    name = Counter(n for n, _ in sl).most_common(1)[0][0]
    affs = [a for a, _ in Counter(a for _, a in sl if a).most_common()]
    insts = []
    for aff in affs:
        for n, _, _ in resolve(aff):
            if n not in insts:
                insts.append(n)
    AI[pid] = len(AUTH)
    AUTH.append([name, pid, affs[0] if affs else '', [IDX[n] for n in insts if n in IDX]])
for q in slots:
    AI[q] = AI[canon[q]]
print('authors', len(AUTH), 'merged ids', len(slots) - len(AUTH))

DAYNUM = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5}
TYPES = ['Regular Session', 'Invited Session', 'RI Session', 'Plenary Session', 'HT Session', 'Tutorial Session', 'Workshop']
KWS = [k for k, _ in allkw.most_common()]
KI = {k: i for i, k in enumerate(KWS)}
used_ses = sorted({p['session'] for p in PAP})
SI = {s: i for i, s in enumerate(used_ses)}
ses_rows = []
for s in used_ses:
    x = SES[s]
    ses_rows.append([x['code'], x['title'], x['day'][:3], x['time'].replace('-', '–'), x['room'], TYPES.index(x['type']), DAYNUM[x['day']],
                     [[AI[c[2]], c[3]] for c in x['chairs']], x['code'].lower()])
rows = []
for p in PAP:
    s = SES[p['session']]
    rows.append([p['title'], [IDX[n] for n in p['insts']], p['area'], p['anchor'], SI[p['session']], p['code'],
                 [KI[k] for k in p['keywords']], 1 if s['type'] in TECH else 0, [AI[a[2]] for a in p['authors']], p['time'],
                 LINKS.get(p['id'], {}).get('arxiv') or '', LINKS.get(p['id'], {}).get('code') or []])
(site / 'papers.js').write_text('window.PAPERS=' + json.dumps({
    'n': len(rows), 'dim': int(E.shape[1]), 'model': 'Xenova/bge-small-en-v1.5', 'types': TYPES,
    'keywords': KWS, 'sessions': ses_rows, 'authors': AUTH, 'rows': rows}, ensure_ascii=False, separators=(',', ':')) + ';\n')
scale = np.abs(E).max(axis=1) / 127.0
Q = np.clip(np.round(E / scale[:, None]), -127, 127).astype(np.int8)
with open(site / 'papers.bin', 'wb') as f:
    f.write(scale.astype('<f4').tobytes())
    f.write(Q.tobytes())
recon = (Q.astype(np.float32) * scale[:, None])
print('quantization cos error (max)', float(1 - (recon * E).sum(1).min()))

# ---------------- CSV ----------------
with open(site / 'cdc2026_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'institution', 'papers', 'pct_of_papers', 'fractional_papers', 'country', 'sector'] + [a[0] for a in AREAS])
    for x in ranked:
        w.writerow([x['r'], x['n'], x['p'], round(100 * x['p'] / len(tech), 2), x['f'], x.get('c', ''),
                    'industry' if x['s'] == 'I' else 'academia'] + x['a'])

print(f"tech papers {len(tech)}, all {len(PAP)}, ranked institutions {len(ranked)}, all institutions {len(INST)}")
print('areas', [(a[1], area_tot[i]) for i, a in enumerate(AREAS)])
print('guessed areas', sum(1 for p in PAP if p.get('area_guess')))
print('top 25', [(x['r'], x['n'], x['p'], x['f']) for x in ranked[:25]])
print('top industry', [(x['n'], x['p']) for x in ranked if x['s'] == 'I'][:12])
print('countries', countries.most_common(12), 'industry share', meta['industry_share'])
