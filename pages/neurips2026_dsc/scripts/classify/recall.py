"""Recall stage of the DSC funnel: lexicon scoring + embedding similarity to seed papers.

Usage: venv/bin/python -I recall.py <neurips.json> <out_dir> [seeds.txt]
Writes out_dir/emb.npy (bge-small-en-v1.5 embeddings of title + abstract, reused by build.py),
out_dir/recall.json (per paper: lexicon hits, false-friend hits, seed similarity, candidate flag) and
out_dir/seed_candidates.txt (strict title matches, to help choose seeds by hand).
"""
import json, re, sys
from pathlib import Path
import numpy as np

src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
P = json.load(src.open())['papers']
seeds = set(Path(sys.argv[3]).read_text().split()) if len(sys.argv) > 3 else set()

# ---- lexicon (weights ~ how diagnostic the phrase is); matched case-insensitively on title + abstract ----
LEX = [
    (3, r'model[- ]predictive control|\bmpc\b'), (3, r'optimal control'), (3, r'\blqr\b|linear[- ]quadratic (regulator|gaussian|control)|\blqg\b'),
    (3, r'koopman'), (3, r'lyapunov'), (3, r'barrier (function|certificate)s?|\bcbfs?\b'), (3, r'system identification'),
    (3, r'kalman'), (2, r'\bobservers?\b'), (3, r'reachab(le|ility)'), (2, r'contraction (metric|theory|analysis|property)|contracting (system|dynamics)'),
    (3, r'trajectory optimi[sz]ation'), (3, r'port[- ]hamiltonian'), (3, r'control barrier'), (3, r'\bcontrol (theory|theoretic|systems?|design|law|policy|policies|input|inputs|synthesis)\b'),
    (3, r'(feedback|closed[- ]loop|adaptive|robust|nonlinear|stochastic|distributed|networked|safety[- ]critical|data[- ]driven|learning[- ]based|optimal|sampled[- ]data|event[- ]triggered|predictive|tracking|output|hybrid) control'),
    (2, r'\bcontroller'), (3, r'state estimation|state estimator'), (2, r'\bfilter(ing)? (for|of) (nonlinear|dynamical|state)'),
    (3, r'dynamical systems?'), (2, r'dynamic(al)? model(s|ing)?|dynamics model'), (2, r'world model'), (2, r'hamilton[- ]jacobi|\bhjb\b|pontryagin'),
    (2, r'stabili[sz](e|ing|ation)\b.*(system|dynamics|equilibrium)|asymptotic(ally)? stab'), (2, r'input[- ]to[- ]state|dissipativ|passivity'),
    (2, r'safety filter|safe control|safe set|invariant set|forward invarian'), (2, r'\bsafe (reinforcement learning|rl)\b|constrained (mdp|markov|rl|reinforcement)'),
    (2, r'neural (ode|sde|cde)s?|neural ordinary|neural stochastic differential'), (2, r'physics[- ]informed|physics[- ]based|hamiltonian neural|lagrangian neural'),
    (2, r'\bpde\b|partial differential equation|navier|fluid (flow|dynamics|simulation)|operator learning|neural operator'),
    (2, r'(regret|sample complexity).*(control|linear system|lqr|dynamical)'), (2, r'linear (dynamical )?systems?\b'), (2, r'unknown (linear|nonlinear|dynamical) system'),
    (2, r'model[- ]based (reinforcement learning|rl|planning|control)'), (2, r'robot(ic)? (control|manipulation|locomotion|dynamics)|legged|quadrotor|quadruped|humanoid|whole[- ]body control'),
    (2, r'sim[- ]to[- ]real|dynamics randomi'), (1, r'\bdynamics\b'), (1, r'\bplanning\b'), (1, r'gradient flow|training dynamics|learning dynamics'),
    (2, r'\bsindy\b|equation discovery|dynamic mode decomposition|chaotic|attractor|lorenz|limit cycle|bifurcation'),
    (2, r'stochastic (optimal )?control|schr[öo]dinger bridge|hamilton'), (2, r'mean[- ]field (game|control)'), (2, r'inverse (optimal control|reinforcement learning)'),
    (2, r'power (grid|system)|smart grid|traffic (control|signal)|hvac|building (energy|control)|process control|plasma|tokamak|autonomous driving|vehicle dynamics'),
    (2, r'data assimilation|ensemble kalman|particle filter|sequential monte carlo.*(state|dynamic)'), (2, r'differentiable (simulat|physics|mpc|control)'),
    (2, r'imitation learning|behavio(u)?r cloning|diffusion polic'), (2, r'markov decision process|\bmdp\b|\bpomdp\b'),
]
FALSE = [
    r'state[- ]space model', r'\bmamba\b|\bs4\b|selective state space', r'controllable (generation|diffusion|text|image|video|synthesis)|controlnet|control tokens?',
    r'human feedback|\brlhf\b|\bgrpo\b|\bdpo\b', r'control group', r'access control|congestion control|version control|quality control',
    r'stable diffusion', r'kv cache', r'large language model|\bllms?\b|vision[- ]language', r'diffusion (model|transformer)|flow matching|text[- ]to[- ](image|video)',
    r'classifier|image classification|segmentation|object detection', r'adversarial (example|attack|robust)', r'\bgraph neural\b|\bgnn',
]
LEXC = [(w, re.compile(p, re.I)) for w, p in LEX]
FALSEC = [re.compile(p, re.I) for p in FALSE]
STRICT = re.compile(r'model[- ]predictive control|\bmpc\b|optimal control|\blqr\b|koopman|lyapunov|barrier function|system identification|kalman|reachab|contraction|trajectory optimi|port[- ]hamiltonian|control barrier|\bcontrol(ler|lers)?\b|state estimation|dynamical system|safety filter|safe control|hamilton[- ]jacobi', re.I)

rows = {}
for p in P:
    text = p['title'] + '\n' + p['abstract']
    hits = [(w, rx.pattern) for w, rx in LEXC if rx.search(text)]
    thits = sum(w for w, rx in LEXC if rx.search(p['title']))
    fhits = [rx.pattern for rx in FALSEC if rx.search(text)]
    lex = sum(w for w, _ in hits) + thits          # title hits count double
    rows[p['id']] = {'lex': lex, 'nhits': len(hits), 'hits': [h[1][:30] for h in hits], 'false': len(fhits), 'title_strict': bool(STRICT.search(p['title']))}

(out / 'seed_candidates.txt').write_text('\n'.join(f"{p['id']}\t{rows[p['id']]['lex']}\t{p['jarea']}\t{p['title']}"
    for p in sorted(P, key=lambda p: -rows[p['id']]['lex']) if rows[p['id']]['title_strict']) + '\n')

# ---- embeddings ----
from sentence_transformers import SentenceTransformer
emb_path = out / 'emb.npy'
if emb_path.exists() and np.load(emb_path).shape[0] == len(P):
    E = np.load(emb_path)
else:
    model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
    E = model.encode([(p['title'] + '. ' + p['abstract']).strip() for p in P], batch_size=32, normalize_embeddings=True, show_progress_bar=True).astype(np.float32)
    np.save(emb_path, E)
ID2I = {p['id']: i for i, p in enumerate(P)}
if not seeds:   # default seeds: strongest strict-title lexicon papers
    seeds = {p['id'] for p in sorted(P, key=lambda p: -rows[p['id']]['lex']) if rows[p['id']]['title_strict']}
    seeds = set(list(seeds)[:30])
SI = [ID2I[s] for s in seeds if s in ID2I]
# bge-small cosine similarities are compressed (every paper scores > 0.6 against the seeds), so scores are made
# relative: subtract each paper's similarity to the corpus centroid, and threshold by percentile, not by value.
g = E.mean(axis=0); g /= np.linalg.norm(g); sg = E @ g
sims = E @ E[SI].T
top3 = np.sort(sims, axis=1)[:, -3:].mean(axis=1) - sg
centroid = E[SI].mean(axis=0); centroid /= np.linalg.norm(centroid)
cen = E @ centroid - sg
# rubric subcategory descriptions as retrieval queries (bge query instruction), max over the 11 descriptions
RUBRIC_Q = ['optimal control and model predictive control of dynamical systems, LQR, trajectory optimization with dynamics constraints',
 'system identification and learning dynamical models from data for control, Koopman operator methods, data-driven control',
 'stability and safety certificates for controllers: Lyapunov functions, control barrier functions, reachability analysis, verification of closed-loop systems',
 'state estimation and filtering for dynamical systems: Kalman filter, observers, data assimilation',
 'learning-based and adaptive control theory: online control of unknown linear systems with regret guarantees, robust control, control of networked systems',
 'robot control: locomotion and manipulation controllers, dynamics-aware planning, whole-body control, model predictive control for robots',
 'model-based reinforcement learning with learned world models for planning',
 'neural ODEs, physics-informed neural networks and neural operators for simulating physical dynamical systems and PDEs',
 'dynamical systems analysis of training dynamics: gradient flow, stability of optimization algorithms as dynamical systems',
 'forecasting and reconstructing chaotic dynamical systems from time series, equation discovery, dynamic mode decomposition',
 'safe constrained and robust reinforcement learning for continuous control, stochastic optimal control for sampling']
rs_path = out / 'rubric_sims.npy'
if rs_path.exists() and np.load(rs_path).shape == (len(P), len(RUBRIC_Q)):
    RS = np.load(rs_path)
else:
    model = SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')
    QE = model.encode(['Represent this sentence for searching relevant passages: ' + q for q in RUBRIC_Q], normalize_embeddings=True)
    RS = E @ QE.T; np.save(rs_path, RS)
rub = RS.max(axis=1) - sg
pct = lambda a, q: float(np.percentile(a, q))
T = {'top3_85': pct(top3, 85), 'cen_85': pct(cen, 85), 'rub_85': pct(rub, 85), 'top3_70': pct(top3, 70), 'cen_70': pct(cen, 70), 'rub_70': pct(rub, 70)}
for p in P:
    r = rows[p['id']]; i = ID2I[p['id']]
    r['sim_top3'] = round(float(top3[i]), 4); r['sim_centroid'] = round(float(cen[i]), 4); r['sim_rubric'] = round(float(rub[i]), 4)
    r['rubric_best'] = int(RS[i].argmax())
    emb_strong = top3[i] >= T['top3_85'] or cen[i] >= T['cen_85'] or rub[i] >= T['rub_85']
    emb_weak = top3[i] >= T['top3_70'] or cen[i] >= T['cen_70'] or rub[i] >= T['rub_70']
    r['candidate'] = bool(r['lex'] >= 4 or emb_strong or (r['lex'] >= 2 and emb_weak))
    r['seed'] = p['id'] in seeds
cand = [p for p in P if rows[p['id']]['candidate']]
print('papers', len(P), 'seeds', len(SI), 'candidates', len(cand), 'thresholds', {k: round(v, 3) for k, v in T.items()})
print('lex>=4', sum(r['lex'] >= 4 for r in rows.values()), '| embedding-only candidates', sum(r['candidate'] and r['lex'] < 4 for r in rows.values()))
json.dump({'seeds': sorted(seeds), 'thresholds': T, 'rows': rows}, (out / 'recall.json').open('w'))
