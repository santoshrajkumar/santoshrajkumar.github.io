"""Build the RA-L Explorer data files from ral.json.

Usage: venv/bin/python -I build.py <ral.json> <site_dir> <institutions.json> [links.json] [icra26.json]
Writes data.js, papers.js, papers.bin and ral_institutions.csv into <site_dir>.
Embeddings are cached in <site_dir>/raw/embeddings.npz, so an update only embeds new or changed papers.
"""
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

src, site, imeta_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
LINKS = json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv) > 4 and Path(sys.argv[4]).exists() else {}
D = json.loads(src.read_text())
IMETA = json.loads(imeta_path.read_text())
PAP = sorted(D['papers'], key=lambda p: (p['date'], p['id']), reverse=True)  # newest first
SNAPSHOT = D['meta']['fetched']

# ---------------- research areas from the RAS keywords used by ICRA 2026 and IROS 2026 ----------------
# All 305 ICRA 2026 keywords, grouped by hand into 16 broad areas (groups follow the IROS 2026 session themes).
AREAS = [
    ('Manipulation & grasping', 'Manipulation', '#e63946', [
        'Grasping', 'Dexterous Manipulation', 'In-Hand Manipulation', 'Bimanual Manipulation', 'Dual Arm Manipulation',
        'Mobile Manipulation', 'Manipulation Planning', 'Deformable Object Manipulation', 'Dynamic Manipulation',
        'Deep Learning in Grasping and Manipulation', 'Perception for Grasping and Manipulation', 'Assembly', 'Compliant Assembly',
        'Disassembly', 'Collaborative Pushing', 'Object Placement', 'Affordance', 'Contact Modeling', 'Multifingered Hands',
        'Grippers and Other End-Effectors', 'Pin-array gripper', 'Force Control', 'Compliance and Impedance Control', 'Interactive Perception']),
    ('Robot learning', 'Learning', '#f9c74f', [
        'Reinforcement Learning', 'Imitation Learning', 'Learning from Demonstration', 'Machine Learning for Robot Control',
        'Deep Learning Methods', 'Deep Learning in Robotics and Automation', 'Transfer Learning', 'Continual Learning', 'Incremental Learning',
        'Representation Learning', 'Learning from Experience', 'Learning and Adaptive Systems', 'Model Learning for Control',
        'Sensorimotor Learning', 'Bioinspired Robot Learning', 'Data Sets for Robot Learning', 'Physics-Informed Machine Learning',
        'Stable Dynamical System Learning', 'Graph Neural Networks', 'Visual Learning', 'Learning Categories and Concepts',
        'Developmental Robotics', 'Evolutionary Robotics', 'Integrated Planning and Learning', 'Motion Retargeting']),
    ('Perception & vision', 'Perception', '#577590', [
        'Deep Learning for Visual Perception', 'Object Detection, Segmentation and Categorization', 'Semantic Scene Understanding',
        'RGB-D Perception', 'Recognition', 'Visual Tracking', 'Computer Vision for Automation', 'Computer Vision for Manufacturing',
        'Computer Vision for Other Robotic Applications', 'Data Sets for Robotic Vision', 'Omnidirectional Vision', 'Range Sensing',
        'Gaussian Splatting', 'Neural Radiance Field', 'Dense Reconstruction', 'Non-rigid structure-from-motion', 'Similarity Matching',
        'Point-polygon Matching', 'Human Detection and Tracking', 'Robot Audition', 'Perception-Action Coupling', 'Visual Servoing',
        'Inverse Problems', 'Water flow vector perception']),
    ('SLAM & localization', 'SLAM', '#277da1', [
        'SLAM', 'Localization', 'Mapping', 'Visual-Inertial SLAM', 'Dynamic SLAM', 'Multi-Robot SLAM', 'Audio-Visual SLAM',
        'Bathymetric SLAM', 'Data Sets for SLAM', 'View Planning for SLAM', 'Sensor Fusion', 'Calibration and Identification',
        'Lie group and Lie algebra', 'UWB Array', 'Probabilistic Inference', 'Probability and Statistical Methods']),
    ('Motion & task planning', 'Planning', '#f4845f', [
        'Motion and Path Planning', 'Task and Motion Planning', 'Task Planning', 'Planning under Uncertainty', 'Collision Avoidance',
        'Constrained Motion Planning', 'Nonholonomic Motion Planning', 'Reactive and Sensor-Based Planning', 'Trajectory Generation',
        'Integrated Planning and Control', 'Search Algorithms', 'Constrained Anytime Belief Space Planning', 'Computational Geometry',
        'Hybrid Logical/Dynamical Planning and Verification', 'Inspection planning under uncertainty', 'Stochastic Shortest Path With Recourse',
        'Homotopy Optimization Method', 'Curvature-Constrained Vector Field', 'Human-Aware Motion Planning', 'Planning, Scheduling and Coordination']),
    ('Control, optimization & safety', 'Control', '#9d0208', [
        'Optimization and Optimal Control', 'Model Predictive Control', 'Model-Predictive Control', 'Robust/Adaptive Control',
        'Robust/Adaptive Control of Robotic Systems', 'Motion Control', 'Motion Control of Manipulators', 'Control Barrier Functions',
        'Hamilton-Jacobi Reachability Analysis', 'Robot Safety', 'Formal Methods in Robotics and Automation', 'Sensor-based Control',
        'Neural and Fuzzy Control', 'Convex Optimization', 'Differentiable Optimization', 'Dynamics', 'Direct/Inverse Dynamics Formulation',
        'Kinematics', 'Redundant Robots', 'Singular Configuration', 'Underactuated Robots', 'Failure Detection and Recovery',
        'False Data Injection Attack', 'Privacy for Robotic Applications', 'Energy Tank', 'Motion Compensation', 'Natural Machine Motion',
        'Nonholonomic Mechanisms and Systems', 'Process Control', 'Configuration Stability Estimation']),
    ('Legged & humanoid robots', 'Legged', '#90be6d', [
        'Legged Robots', 'Humanoid and Bipedal Locomotion', 'Humanoid Robots', 'Humanoid Robot Systems', 'Quadrupedal Robot',
        'Multi-Contact Whole-Body Motion Planning and Control', 'Whole-Body Motion Planning and Control', 'Body Balancing',
        'Passive Walking', 'Hybrid Locomotion', 'Climbing Robots', 'Human and Humanoid Motion Analysis and Synthesis', 'Wheeled Robots']),
    ('Aerial robots', 'Aerial', '#4d908e', [
        'Aerial Systems: Applications', 'Aerial Systems: Mechanics and Control', 'Aerial Systems: Perception and Autonomy',
        'Aerial Manipulation', 'Fluid Mechanics']),
    ('Field, marine & space robots', 'Field', '#6a040f', [
        'Field Robots', 'Marine Robotics', 'Space Robotics and Automation', 'Robotics in Agriculture and Forestry',
        'Robotics and Automation in Agriculture and Forestry', 'Agricultural Automation', 'Robotics and Automation in Construction',
        'Mining Robotics', 'Robotics in Hazardous Fields', 'Search and Rescue Robots', 'Environment Monitoring and Management',
        'Surveillance Robotic Systems', 'Robotics in Under-Resourced Settings', 'Energy and Environment-Aware Automation']),
    ('Autonomous vehicles & navigation', 'Driving/nav', '#2b2d42', [
        'Autonomous Vehicle Navigation', 'Intelligent Transportation Systems', 'Computer Vision for Transportation',
        'Vision-Based Navigation', 'Visual-Based Navigation', 'Automation Technologies for Smart Cities', 'Autonomous Agents']),
    ('Multi-robot systems & swarms', 'Multi-robot', '#43aa8b', [
        'Multi-Robot Systems', 'Path Planning for Multiple Mobile Robots or Agents', 'Swarm Robotics', 'Swarms', 'Cooperating Robots',
        'Distributed Robot Systems', 'Networked Robots', 'Sensor Networks', 'Agent-Based Systems', 'Deadlock Detection and Avoidance']),
    ('Human-robot interaction', 'HRI', '#9b5de5', [
        'Human-Robot Collaboration', 'Human-Robot Teaming', 'Physical Human-Robot Interaction', 'Social HRI', 'Safety in HRI',
        'Cognitive Human-Robot Interaction', 'Multi-Modal Perception for HRI', 'Natural Dialog for HRI', 'Touch in HRI',
        'Telerobotics and Teleoperation', 'Haptics and Haptic Interfaces', 'Shared Autonomy', 'Virtual Reality and Interfaces',
        'Human Factors and Human-in-the-Loop', 'Human-Centered Robotics', 'Human-Centered Automation', 'Intention Recognition',
        'Gesture, Posture and Facial Expressions', 'Acceptability and Trust', 'Long term Interaction', 'Robot Companions',
        'Emotional Robotics', 'Design and Human Factors', 'Modeling and Simulating Humans', 'Datasets for Human Motion',
        'Education Robotics', 'Art and Entertainment Robotics', 'Ethics and Philosophy', 'Domestic Robotics', 'Service Robotics', 'Service Robots']),
    ('Medical, rehab & micro-robots', 'Medical', '#2a9d8f', [
        'Medical Robots and Systems', 'Surgical Robotics: Laparoscopy', 'Surgical Robotics: Planning',
        'Surgical Robotics: Steerable Catheters/Needles', 'Computer Vision for Medical Robotics', 'Magnetic-Assisted Endoscopy',
        'MRI-compatible robot', 'Rehabilitation Robotics', 'Prosthetics and Exoskeletons', 'Exoskeletons', 'Wearable Robotics',
        'Wearable Robots', 'Physically Assistive Devices', 'Human Performance Augmentation', 'Brain-Machine Interfaces', 'Gait phase estimation',
        'gait phase estimation', 'Health Care Management', 'Robotics and Automation in Life Sciences', 'Micro/Nano Robots',
        'Automation at Micro-Nano Scales', 'Micromanipulators', 'Biological Cell Manipulation', 'Nanomanufacturing', 'Neurorobotics']),
    ('Soft & continuum robots', 'Soft', '#f28482', [
        'Modeling, Control, and Learning for Soft Robots', 'Soft Robot Applications', 'Soft Robot Control', 'Soft Robot Materials and Design',
        'Soft Sensors and Actuators', 'Soft Continuum Robots', 'Flexible Robotics', 'Tendon/Wire Mechanism', 'Hydraulic/Pneumatic Actuators',
        'Biologically-Inspired Robots', 'Biomimetics', 'Bio-inspired Actuation of Robot', 'Magnetorheological technology']),
    ('Mechanisms, actuators & sensing', 'Mechanisms', '#c77dff', [
        'Mechanism Design', 'Robot Design', 'Actuation and Joint Mechanisms', 'Compliant Joint/Mechanism', 'Compliant Joints and Mechanisms',
        'Parallel Robots', 'Cellular and Modular Robots', 'Co-Design', 'Force and Tactile Sensing', 'Vision-based Tactile Perception',
        'Visuotactile simulation', 'Impact Absorption', 'Energy Regeneration', 'Polar Robot', 'Additive Manufacturing',
        'Methods and Tools for Robot System Design', 'Product Design, Development and Prototyping', 'Engineering for Robotic Systems']),
    ('AI, software & automation', 'AI/systems', '#e85d75', [
        'AI-Based Methods', 'AI-Enabled Robotics', 'Cognitive Control Architectures', 'Cognitive Modeling', 'Embodied Cognitive Science',
        'Behavior-Based Systems', 'Active Inference', 'Big Data in Robotics and Automation', 'Software Architecture for Robotic and Automation',
        'Software Tools for Benchmarking and Reproducibility', 'Software Tools for Robot Programming',
        'Software, Middleware and Programming Environments', 'Software-Hardware Integration for Robot Systems',
        'Hardware-Software Integration in Robotics', 'Control Architectures and Programming', 'Computer Architecture for Robotic and Automation',
        'Embedded Systems for Robotic and Automation', 'Autonomous Embedded Robotics', 'Performance Evaluation and Benchmarking',
        'Simulation and Animation', 'Industrial Robots', 'Factory Automation', 'Intelligent and Flexible Manufacturing',
        'AI and Machine Learning in Manufacturing and Logistics Systems', 'Manufacturing, Maintenance and Supply Chains',
        'Inventory Management', 'Logistics', 'Foundations of Automation', 'Discrete Event Dynamic Automation Systems', 'Building Automation',
        'Collaborative Robotics']),
]
KW2A = {k: i for i, a in enumerate(AREAS) for k in a[3]}
ICRA = json.loads((src.parent / 'raw' / 'icra26.json').read_text()) if len(sys.argv) <= 5 else json.loads(Path(sys.argv[5]).read_text())
missing = sorted({k for p in ICRA['papers'] for k in p['keywords']} - set(KW2A))
assert not missing, missing
unused = sorted(set(KW2A) - set(ICRA['keywords']) - {k for p in ICRA['papers'] for k in p['keywords']})
assert not unused, unused


def area_from_keywords(kws):
    sc = defaultdict(float)
    for j, k in enumerate(kws):
        sc[KW2A[k]] += 1.5 if j == 0 else 1.0
    best = max(sc.values())
    return next(KW2A[k] for k in kws if sc[KW2A[k]] == best)  # tie -> earliest keyword


# ---------------- embeddings (cached by text hash) ----------------
IPAP = [p for p in ICRA['papers'] if p['abstract']]
texts = [(p['title'] + '. ' + p['abstract']).strip() for p in PAP] + [(p['title'] + '. ' + p['abstract']).strip() for p in IPAP]
keys = [hashlib.sha1(t.encode()).hexdigest()[:16] for t in texts]
cache_f = site / 'raw' / 'embeddings.npz'
cached = {}
if cache_f.exists():
    z = np.load(cache_f)
    cached = dict(zip(z['keys'].tolist(), z['E']))
todo = [i for i, k in enumerate(keys) if k not in cached]
print('embeddings cached', len(keys) - len(todo), '| to embed', len(todo), flush=True)
if todo:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
    new = model.encode([texts[i] for i in todo], batch_size=64, normalize_embeddings=True, show_progress_bar=True).astype(np.float32)
    for i, v in zip(todo, new):
        cached[keys[i]] = v
E = np.stack([cached[k] for k in keys]).astype(np.float32)
cache_f.parent.mkdir(exist_ok=True)
np.savez(cache_f, keys=np.array(keys), E=E)

# ---------------- areas: vote of the 15 most similar ICRA 2026 papers (by their own keywords) ----------------
E, EI = E[:len(PAP)], E[len(PAP):]
IA = np.array([area_from_keywords(p['keywords']) for p in IPAP])
for k in range(0, len(PAP), 2048):
    sims = E[k:k + 2048] @ EI.T
    for i, row in enumerate(sims):
        nn = np.argpartition(-row, 15)[:15]
        sc = np.bincount(IA[nn], weights=row[nn], minlength=len(AREAS))
        PAP[k + i]['area'] = int(sc.argmax())
NA = len(AREAS)

# ---------------- institutions (OpenAlex IDs) ----------------
COUNTRY_SUFFIX = re.compile(r'\s*\((United States|United Kingdom|China|Germany|Japan|France|Switzerland|South Korea|Canada|'
                            r'Netherlands|Italy|Israel|India|Singapore|Sweden|Australia|Spain|Taiwan|Belgium|Austria|Denmark|'
                            r'Finland|Norway|Hong Kong|Ireland|Poland|Brazil|Russia|Czechia|Portugal|Greece|Turkey|[A-Z][a-z]+)\)$')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    return re.sub(r'[^a-z0-9]+', ' ', ''.join(c for c in s if not unicodedata.combining(c)).lower().replace('&', ' and ')).strip()


def canon_id(i):
    """Companies are counted as one: 'Google (United States)' and 'Google (Switzerland)' roll up to Google."""
    m = IMETA.get(i) or {}
    if m.get('t') == 'company' and m.get('lin') and m['lin'][-1] in IMETA and IMETA[m['lin'][-1]].get('n'):
        return m['lin'][-1]
    return i


PRETTY = {'Centre National de la Recherche Scientifique': 'CNRS'}  # shorter names people actually use


def display(i, fallback):
    m = IMETA.get(i) or {}
    n = m.get('n') or fallback
    n = PRETTY.get(n, n)
    if m.get('t') == 'company':
        n = COUNTRY_SUFFIX.sub('', n)
    return n


INFO = {}  # canonical id -> [name, cc, type]
for p in PAP:
    for a in p['authors']:
        for name, cc, typ, iid in a['oa_insts']:
            c = canon_id(iid)
            m = IMETA.get(c) or {}
            INFO.setdefault(c, [display(c, name), m.get('c') or cc, m.get('t') or typ])
# Same display name for different institutions (two "Northeastern University"): add the country
byname = defaultdict(list)
for c, v in INFO.items():
    byname[v[0]].append(c)
for n, cs in byname.items():
    if len(cs) > 1:
        if all(INFO[c][2] == 'company' for c in cs):   # company branches with the same name: merge
            for c in cs[1:]:
                INFO[c] = INFO[cs[0]][:3] + [cs[0]]
        else:
            for c in cs:
                INFO[c][0] = f'{n} ({INFO[c][1]})' if INFO[c][1] else n
MERGE = {c: v[3] for c, v in INFO.items() if len(v) > 3}

# Authors OpenAlex couldn't link: look for a known institution name inside the printed affiliation
NAME2ID = {}
for c, v in INFO.items():
    m = IMETA.get(c) or {}
    for s in [v[0]] + (m.get('alt') or []):
        k = norm(s)
        if len(k) >= 10 and len(k.split()) >= 2:
            NAME2ID.setdefault(k, MERGE.get(c, c))
NAMES_BY_LEN = sorted(NAME2ID, key=len, reverse=True)


def from_text(aff):
    t = ' ' + norm(aff) + ' '
    for k in NAMES_BY_LEN:
        if ' ' + k + ' ' in t:
            return [NAME2ID[k]]
    return []


matched_text = unmatched = 0
for p in PAP:
    insts, frac = [], defaultdict(float)
    n = len(p['authors']) or 1
    for a in p['authors']:
        ids = list(dict.fromkeys(MERGE.get(canon_id(x[3]), canon_id(x[3])) for x in a['oa_insts']))
        if not ids and a['aff']:
            ids = from_text(a['aff'])
            matched_text += bool(ids)
            unmatched += not ids
        a['ids'] = ids
        for c in ids:
            frac[c] += 1 / n / len(ids)
            if c not in insts:
                insts.append(c)
    p['insts'], p['frac'] = insts, frac
print('authors matched by affiliation text', matched_text, '| unmatched', unmatched)

YEARS = sorted({p['year'] for p in PAP})
YI = {y: i for i, y in enumerate(YEARS)}
stat = defaultdict(lambda: {'p': 0, 'f': 0.0, 'a': [0] * NA, 'y': [0] * len(YEARS)})
aliases = defaultdict(Counter)
for p in PAP:
    for c in p['insts']:
        s = stat[c]
        s['p'] += 1
        s['f'] += p['frac'][c]
        s['a'][p['area']] += 1
        s['y'][YI[p['year']]] += 1
    for a in p['authors']:
        if len(a['ids']) == 1 and a['aff']:
            aliases[a['ids'][0]][a['aff'][:80]] += 1
names = sorted(stat, key=lambda c: (-stat[c]['p'], -stat[c]['f'], INFO[c][0]))
INST, rank, prev = [], 0, None
for i, c in enumerate(names):
    s = stat[c]
    if s['p'] != prev:
        rank, prev = i + 1, s['p']
    name, cc, typ = INFO[c][:3]
    m = IMETA.get(c) or {}
    al = list(dict.fromkeys([x for x in (m.get('acr') or []) + (m.get('alt') or []) if x != name and len(x) < 90]))[:10]
    al += [x for x, _ in aliases[c].most_common(4) if x not in al and x != name]
    x = {'n': name, 'p': s['p'], 'f': round(s['f'], 1), 's': 'I' if typ == 'company' else 'A', 'a': s['a'], 'y': s['y'], 'id': c, 'r': rank}
    if cc:
        x['c'] = cc
    if al:
        x['k'] = al
    INST.append(x)
IDX = {x['id']: i for i, x in enumerate(INST)}
COUNTRY = {'US': 'United States', 'CN': 'China', 'DE': 'Germany', 'JP': 'Japan', 'KR': 'South Korea', 'IT': 'Italy', 'GB': 'United Kingdom',
           'CH': 'Switzerland', 'FR': 'France', 'CA': 'Canada', 'NL': 'Netherlands', 'SG': 'Singapore', 'HK': 'Hong Kong', 'AU': 'Australia',
           'ES': 'Spain', 'SE': 'Sweden', 'BE': 'Belgium', 'DK': 'Denmark', 'AT': 'Austria', 'IL': 'Israel', 'IN': 'India', 'TW': 'Taiwan',
           'NO': 'Norway', 'FI': 'Finland', 'PT': 'Portugal', 'IE': 'Ireland', 'PL': 'Poland', 'CZ': 'Czechia', 'GR': 'Greece', 'TR': 'Turkey',
           'BR': 'Brazil', 'MX': 'Mexico', 'RU': 'Russia', 'AE': 'United Arab Emirates', 'SA': 'Saudi Arabia', 'MO': 'Macau', 'NZ': 'New Zealand',
           'LU': 'Luxembourg', 'HU': 'Hungary', 'EE': 'Estonia', 'SI': 'Slovenia', 'HR': 'Croatia', 'RO': 'Romania', 'CY': 'Cyprus',
           'QA': 'Qatar', 'IR': 'Iran', 'PK': 'Pakistan', 'TH': 'Thailand', 'VN': 'Vietnam', 'MY': 'Malaysia', 'CL': 'Chile', 'CO': 'Colombia',
           'AR': 'Argentina', 'EG': 'Egypt', 'ZA': 'South Africa', 'KZ': 'Kazakhstan', 'UA': 'Ukraine', 'SK': 'Slovakia', 'RS': 'Serbia',
           'LT': 'Lithuania', 'LV': 'Latvia', 'IS': 'Iceland', 'MA': 'Morocco', 'TN': 'Tunisia', 'NG': 'Nigeria', 'KE': 'Kenya', 'PE': 'Peru',
           'ID': 'Indonesia', 'PH': 'Philippines', 'BD': 'Bangladesh', 'LK': 'Sri Lanka', 'JO': 'Jordan', 'LB': 'Lebanon', 'OM': 'Oman',
           'KW': 'Kuwait', 'BG': 'Bulgaria', 'MT': 'Malta', 'UY': 'Uruguay', 'EC': 'Ecuador', 'DZ': 'Algeria', 'NP': 'Nepal', 'AM': 'Armenia'}
for x in INST:
    if x.get('c'):
        x['g'] = COUNTRY.get(x['c'], x['c'])
countries = Counter()
for p in PAP:
    for c in {INST[IDX[c]].get('c') for c in p['insts']} - {None}:
        countries[c] += 1
area_tot = [sum(1 for p in PAP if p['area'] == i) for i in range(NA)]

# ---------------- authors (OpenAlex author IDs; same name + shared institution = same person) ----------------
slots = defaultdict(list)  # key -> [(name, aff, ids)]
for p in PAP:
    for a in p['authors']:
        a['key'] = a['oa_id'] or ('n-' + norm(a['name']).replace(' ', '-'))
        slots[a['key']].append((a['name'], a['aff'], a['ids'], a['orcid']))


def top_name(k):
    return Counter(n for n, *_ in slots[k]).most_common(1)[0][0]


inst_of = {k: {c for s in slots[k] for c in s[2]} for k in slots}
orc_of = {k: {s[3] for s in slots[k] if s[3]} for k in slots}
by_name = defaultdict(list)
for k in slots:
    by_name[norm(top_name(k))].append(k)
canon = {}
for name, ks in by_name.items():
    groups = []
    for k in sorted(ks, key=lambda k: -len(slots[k])):
        for g in groups:
            gi = set().union(*(inst_of[q] for q in g))
            go = set().union(*(orc_of[q] for q in g))
            if inst_of[k] & gi or orc_of[k] & go:
                g.append(k)
                break
        else:
            groups.append([k])
    for g in groups:
        for k in g:
            canon[k] = g[0]
AUTH, AI = [], {}
members = defaultdict(list)
for k in slots:
    members[canon[k]].append(k)
for k in sorted(members, key=lambda k: top_name(k)):
    sl = [s for q in members[k] for s in slots[q]]
    name = Counter(s[0] for s in sl).most_common(1)[0][0]
    ids = [c for c, _ in Counter(c for s in sl for c in s[2]).most_common()]
    affs = [a for a, _ in Counter(s[1] for s in sl if s[1]).most_common()]
    shown = INST[IDX[ids[0]]]['n'] if ids else (affs[0][:90] if affs else '')
    AI[k] = len(AUTH)
    AUTH.append([name, k, shown, [IDX[c] for c in ids[:4]]])
for k in slots:
    AI[k] = AI[canon[k]]
print('authors', len(AUTH), '| merged ids', len(slots) - len(AUTH))

# ---------------- data.js ----------------
meta = {
    'journal': 'RA-L', 'full': 'IEEE Robotics and Automation Letters', 'papers': len(PAP), 'early': sum(p['early'] for p in PAP),
    'years': YEARS, 'year_totals': [sum(1 for p in PAP if p['year'] == y) for y in YEARS],
    'institutions': len(INST), 'authors': len(AUTH), 'snapshot': SNAPSHOT,
    'with_arxiv': sum(1 for p in PAP if LINKS.get(p['id'], {}).get('arxiv')),
    'with_code': sum(1 for p in PAP if LINKS.get(p['id'], {}).get('code')),
    'industry_share': round(sum(1 for p in PAP if any(INST[IDX[c]]['s'] == 'I' for c in p['insts'])) / len(PAP), 4),
    'countries': [[c, COUNTRY.get(c, c), n] for c, n in countries.most_common()],
    'areas': [{'name': a[0], 'short': a[1], 'color': a[2], 'total': area_tot[i], 'keywords': a[3]} for i, a in enumerate(AREAS)],
}
# most cited papers of all time (OpenAlex citation counts), shown on the home page
meta['top_cited'] = []
for p in sorted(PAP, key=lambda p: (-p.get('cites', 0), p['date']))[:10]:
    au = [AUTH[i] for i in dict.fromkeys(AI[a['key']] for a in p['authors'])]
    lk = LINKS.get(p['id'], {})
    meta['top_cited'].append({'t': p['title'], 'd': p['id'], 'y': p['year'], 'c': p.get('cites', 0),
                              'au': [[a[0], a[1]] for a in au], 'in': [IDX[c] for c in p['insts']][:4],
                              'ax': lk.get('arxiv') or '', 'code': lk.get('code') or []})
for x in INST:
    del x['id']
(site / 'data.js').write_text('window.RAL=' + json.dumps({'meta': meta, 'inst': INST}, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------- papers.js + papers.bin ----------------
KWS = [k for k, _ in Counter(k for p in PAP for k in p['keywords']).most_common()]
KI = {k: i for i, k in enumerate(KWS)}
rows = []
for p in PAP:
    cite = f"{p['volume']}({p['issue']}):{p['pages'].replace('-', '–')}" if p['issue'] else ''
    lk = LINKS.get(p['id'], {})
    rows.append([p['title'], [IDX[c] for c in p['insts']], p['area'], p['id'], p['year'], 1 if p['early'] else 0,
                 [KI[k] for k in p['keywords']], p['date'], list(dict.fromkeys(AI[a['key']] for a in p['authors'])), cite,
                 lk.get('arxiv') or '', lk.get('code') or [], p.get('cites', 0)])
(site / 'papers.js').write_text('window.PAPERS=' + json.dumps({
    'n': len(rows), 'dim': int(E.shape[1]), 'model': 'Xenova/bge-small-en-v1.5',
    'keywords': KWS, 'authors': AUTH, 'rows': rows}, ensure_ascii=False, separators=(',', ':')) + ';\n')
scale = np.abs(E).max(axis=1) / 127.0
Q = np.clip(np.round(E / scale[:, None]), -127, 127).astype(np.int8)
with open(site / 'papers.bin', 'wb') as f:
    f.write(scale.astype('<f4').tobytes())
    f.write(Q.tobytes())

# ---------------- CSV ----------------
with open(site / 'ral_institutions.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'institution', 'papers', 'pct_of_papers', 'fractional_papers', 'country', 'sector']
               + [a[0] for a in AREAS] + [str(y) for y in YEARS])
    for x in INST:
        w.writerow([x['r'], x['n'], x['p'], round(100 * x['p'] / len(PAP), 2), x['f'], x.get('c', ''),
                    'industry' if x['s'] == 'I' else 'academia'] + x['a'] + x['y'])

print('most cited', [(p['c'], p['t'][:50]) for p in meta['top_cited'][:3]])
print(f"papers {len(PAP)} (early access {meta['early']}), institutions {len(INST)}, countries {len(countries)}")
print('areas', [(a[1], area_tot[i]) for i, a in enumerate(AREAS)])
print('ICRA areas', [(a[1], int((IA == i).sum())) for i, a in enumerate(AREAS)])
print('top 25', [(x['r'], x['n'], x['p']) for x in INST[:25]])
print('top industry', [(x['n'], x['p']) for x in INST if x['s'] == 'I'][:15])
print('countries', countries.most_common(10), 'industry share', meta['industry_share'])
print('sizes', {f: (site / f).stat().st_size // 1024 for f in ('data.js', 'papers.js', 'papers.bin')}, 'KB')
