"""Draw the L-CSS assets/poster.png, assets/og-card.png and assets/favicon.svg from site/data.js.

Usage: venv/bin/python -I poster.py <site_dir>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

site = Path(sys.argv[1])
(site / 'assets').mkdir(exist_ok=True)
s = (site / 'data.js').read_text()
D = json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))
M, INST = D['meta'], D['inst']
Y0, Y1 = M['years'][0], M['years'][-1]
A = M['areas']
INK, MUTED, FAINT, ACA, IND = '#111827', '#6b7280', '#9ca3af', '#2563eb', '#ea580c'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': '#e5e7eb'})


def clean(ax):
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)


# ---------- poster (portrait): top 10 institutions and their leading research area ----------
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ABBR = {'Eindhoven University of Technology': 'TU/e', 'University of Groningen': 'RUG', 'Université Paris-Saclay': 'UPS', 'CentraleSupélec': 'CS', 'Inria': 'Inria', 'Delft University of Technology': 'TUD', 'Politecnico di Milano': 'PoliMi', 'UC San Diego': 'UCSD', 'University of Michigan': 'UMich', 'ETH Zurich': 'ETH', 'University of Illinois Urbana-Champaign': 'UIUC',
        'Georgia Institute of Technology': 'GT', 'KTH Royal Institute of Technology': 'KTH', 'CNRS': 'CNRS',
        'Massachusetts Institute of Technology': 'MIT', 'Purdue University': 'PU', 'UC Berkeley': 'UCB'}
def abbr(n):
    return ABBR.get(n) or ''.join(w[0] for w in n.replace('-', ' ').split() if w[0].isupper())[:4]

ranked = [x for x in INST if x['p']]
top10 = [x for x in ranked if x['r'] <= 10]
fig = plt.figure(figsize=(9, 12.6), dpi=300, facecolor='white')
fig.text(0.06, 0.955, 'L-CSS', fontsize=40, fontweight='bold', color='#6d28d9')
fig.text(0.33, 0.955, 'who publishes what', fontsize=22, color=INK, va='baseline')
fig.text(0.06, 0.928, f"IEEE Control Systems Letters · every paper {Y0}–{Y1}, including early access", fontsize=11.5, color=MUTED)
stats = [(f"{M['papers']:,}", 'papers'), (f"{M['institutions']:,}", 'institutions'),
         (str(len(M['countries'])), 'countries'), (str(len(A)), 'research areas')]
for i, (v, l) in enumerate(stats):
    x = 0.06 + i * 0.23
    fig.text(x, 0.875, v, fontsize=24, fontweight='bold', color=INK)
    fig.text(x, 0.858, l, fontsize=10.5, color=MUTED)
fig.text(0.06, 0.815, 'Top 10 institutions by number of papers', fontsize=15, fontweight='bold', color=INK)
fig.text(0.06, 0.798, 'Papers with at least one author from the institution · bar colors show the research-area mix', fontsize=9.5, color=MUTED)

ax = fig.add_axes([0.04, 0.215, 0.92, 0.57])
ax.set_xlim(0, 100)
ax.set_ylim(len(top10) - 0.5, -0.6)
ax.axis('off')
pmax = max(x['p'] for x in top10)
for i, x in enumerate(top10):
    m = max(x['a'])
    tops = [j for j, v in enumerate(x['a']) if v == m]
    col = A[tops[0]]['color']
    if i % 2 == 0:
        ax.add_patch(FancyBboxPatch((0.5, i - 0.46), 99, 0.92, boxstyle='round,pad=0,rounding_size=1.2', fc='#f5f6f8', ec='none'))
    ax.text(3.4, i, f"#{x['r']}", va='center', ha='center', fontsize=11, fontweight='bold', color=MUTED)
    ax.scatter([10.5], [i], s=1250, color=col, zorder=3)
    ab = abbr(x['n'])
    ax.text(10.5, i, ab, va='center', ha='center', fontsize=9.5 if len(ab) <= 4 else 8, fontweight='bold', color='white', zorder=4)
    ax.text(17, i - 0.2, x['n'], va='center', fontsize=10.8, fontweight='bold', color=INK)
    lab = ' & '.join(A[j]['name'] if len(tops) == 1 else A[j]['short'] for j in tops)
    ax.text(98, i - 0.2, f"Top area: {lab} · {m} papers", va='center', ha='right', fontsize=8.6, fontweight='bold', color=col)
    left = 17
    for j in sorted(range(len(A)), key=lambda j: -x['a'][j]):
        if x['a'][j]:
            w = 74 * x['a'][j] / pmax
            ax.add_patch(plt.Rectangle((left, i + 0.06), w, 0.27, fc=A[j]['color'], ec='white', lw=0.5))
            left += w
    ax.text(left + 0.8, i + 0.2, f"{x['p']} papers", va='center', fontsize=9.5, fontweight='bold', color=INK)

# legend of all areas, 4 columns
fig.text(0.06, 0.188, 'Research areas (matched to CDC 2026 keyword areas)', fontsize=11, fontweight='bold', color=INK)
order = sorted(range(len(A)), key=lambda j: -A[j]['total'])
for k, j in enumerate(order):
    cx, cy = 0.06 + (k % 4) * 0.225, 0.165 - (k // 4) * 0.026
    fig.patches.append(plt.Rectangle((cx, cy - 0.004), 0.012, 0.009, fc=A[j]['color'], transform=fig.transFigure, figure=fig))
    fig.text(cx + 0.017, cy, f"{A[j]['short']} ({A[j]['total']})", fontsize=8.8, color=INK, va='center')
fig.text(0.06, 0.035, 'Badges are abbreviations, colored by each institution’s top area. Unofficial; data: Crossref and OpenAlex, '
         + M['snapshot'] + '.', fontsize=8.3, color=MUTED)
fig.savefig(site / 'assets' / 'poster.png', facecolor='white')
plt.close(fig)

# ---------- og card ----------
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor='white')
fig.text(0.06, 0.70, 'L-CSS', fontsize=72, fontweight='bold', color='#6d28d9')
fig.text(0.06, 0.56, 'Explorer', fontsize=44, fontweight='bold', color=INK)
fig.text(0.06, 0.44, f'Who publishes what in IEEE Control Systems Letters, {Y0}–{Y1}', fontsize=17, color=MUTED)
fig.text(0.06, 0.20, f"{M['papers']:,} papers · {M['institutions']:,} institutions · {len(M['countries'])} countries · {len(A)} research areas",
         fontsize=18, color=INK)
ax = fig.add_axes([0.06, 0.10, 0.88, 0.04])
x0 = 0
for a in sorted(A, key=lambda a: -a['total']):
    ax.barh(0, a['total'], left=x0, color=a['color'], height=1)
    x0 += a['total']
ax.set_xlim(0, x0)
ax.axis('off')
fig.savefig(site / 'assets' / 'og-card.png', facecolor='white')
plt.close(fig)

(site / 'assets' / 'favicon.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="g" x1="0" x2="1">'
    '<stop offset="0" stop-color="#4f46e5"/><stop offset=".5" stop-color="#7c3aed"/><stop offset="1" stop-color="#db2777"/>'
    '</linearGradient></defs><rect width="64" height="64" rx="14" fill="url(#g)"/>'
    '<path d="M10 40 C22 40 22 18 32 18 S42 46 54 30" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>\n')
print('assets written')
