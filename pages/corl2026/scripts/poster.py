"""CoRL 2026 Explorer. Draw assets/poster.png, assets/og-card.png and assets/favicon.svg from site/data.js.

Usage: venv/bin/python -I poster.py <site_dir>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

site = Path(sys.argv[1])
(site / 'assets').mkdir(exist_ok=True)
s = (site / 'data.js').read_text()
D = json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))
M, INST = D['meta'], D['inst']
A = M['areas']
INK, MUTED, FAINT, BRAND = '#111827', '#6b7280', '#9ca3af', '#ea580c'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': '#e5e7eb'})

ABBR = {'Massachusetts Institute of Technology': 'MIT', 'ETH Zurich': 'ETH', 'Stanford University': 'STAN', 'UC Berkeley': 'UCB',
        'Tsinghua University': 'THU', 'Peking University': 'PKU', 'Carnegie Mellon University': 'CMU', 'Google': 'GOOG',
        'University of Illinois Urbana-Champaign': 'UIUC', 'Georgia Institute of Technology': 'GT', 'California Institute of Technology': 'CIT',
        'University of Oxford': 'OXF', 'University of Cambridge': 'CAM', 'Imperial College London': 'ICL', 'Princeton University': 'PRIN',
        'Harvard University': 'HARV', 'University of Washington': 'UW', 'University of Michigan': 'UMich', 'Cornell University': 'CORN',
        'Shanghai Jiao Tong University': 'SJTU', 'Zhejiang University': 'ZJU', 'Nanjing University': 'NJU', 'Microsoft': 'MSFT', 'Meta': 'META',
        'NVIDIA': 'NVDA', 'KTH Royal Institute of Technology': 'KTH', 'EPFL': 'EPFL', 'Technical University of Munich': 'TUM',
        'University of Toronto': 'UofT', 'National University of Singapore': 'NUS', 'KAIST': 'KAIST', 'Seoul National University': 'SNU',
        'University of Pennsylvania': 'UPenn', 'University of Texas at Austin': 'UT', 'UT Austin': 'UT', 'UCLA': 'UCLA', 'UC San Diego': 'UCSD', 'University of Hong Kong': 'HKU', 'Shanghai Innovation Institute': 'SII', 'Fudan University': 'FDU', 'Georgia Institute of Technology': 'GT'}
def abbr(n):
    return ABBR.get(n) or ''.join(w[0] for w in n.replace('-', ' ').split() if w[0].isupper())[:4]

def draw_poster(out, dpi=300, S=1.0):
    """Portrait poster. S scales every font (S > 1 also shortens the 'Top:' labels)."""
    ranked = [x for x in INST if x['p']]
    top10 = [x for x in ranked if x['r'] <= 10][:12]
    fig = plt.figure(figsize=(9, 12.6), dpi=dpi, facecolor='white')
    dy = 0.035 if S > 1 else 0.0   # large version: push the body down under the stacked header
    if S > 1:   # large version: title, tagline and subtitle on separate lines so nothing overlaps or clips
        fig.text(0.06, 0.950, 'CoRL 2026', fontsize=38 * S, fontweight='bold', color=BRAND, va='baseline')
        fig.text(0.06, 0.922, 'Conference on Robot Learning', fontsize=17 * S, color=INK, va='baseline')
        fig.text(0.06, 0.900, "All accepted papers · Austin, Texas · November 9–12, 2026", fontsize=10 * S, color=MUTED, va='baseline')
        fig.text(0.06, 0.885, f"snapshot {M['snapshot']}", fontsize=10 * S, color=MUTED, va='baseline')
    else:
        fig.text(0.06, 0.955, 'CoRL 2026', fontsize=38 * S, fontweight='bold', color=BRAND)
        fig.text(0.43, 0.955, 'Conference on Robot Learning', fontsize=17 * S, color=INK, va='baseline')
        fig.text(0.06, 0.928, f"All accepted papers · Austin, Texas · November 9–12, 2026 · snapshot {M['snapshot']}", fontsize=11 * S, color=MUTED)
    stats = [(f"{M['papers']:,}", 'papers'), (f"{M['core']:,}", 'orals & spotlights'), (f"{M['institutions']:,}", 'institutions'),
             (str(len(M['countries'])), 'countries')]
    for i, (v, l) in enumerate(stats):
        x = 0.06 + i * 0.23
        fig.text(x, 0.875 - dy, v, fontsize=24 * S, fontweight='bold', color=INK)
        fig.text(x, 0.858 - dy, l, fontsize=10.5 * S, color=MUTED)
    fig.text(0.06, 0.815 - dy, 'Top 10 institutions by number of papers', fontsize=15 * S, fontweight='bold', color=INK)
    fig.text(0.06, 0.798 - dy, 'Papers with at least one author from the institution · bar colors show the research-area mix', fontsize=9.5 * S, color=MUTED)

    ax = fig.add_axes([0.04, 0.215, 0.92, 0.57 - dy])
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
        ax.text(3.4, i, f"#{x['r']}", va='center', ha='center', fontsize=11 * S, fontweight='bold', color=MUTED)
        ax.scatter([10.5], [i], s=1250 * S * S, color=col, zorder=3)
        ab = abbr(x['n'])
        ax.text(10.5, i, ab, va='center', ha='center', fontsize=(9.5 if len(ab) <= 4 else 8) * S, fontweight='bold', color='white', zorder=4)
        ax.text(17, i - 0.2, x['n'], va='center', fontsize=10.8 * S, fontweight='bold', color=INK)
        lab = ' & '.join(A[j]['name'] if len(tops) == 1 else A[j]['short'] for j in tops)
        if len(lab) > 48 or S > 1: lab = ' & '.join(A[j]['short'] for j in tops)
        if S > 1 and len(tops) > 1: lab = f"{A[tops[0]]['short']} +{len(tops) - 1} tied"
        ax.text(98, i - 0.2, f"Top: {lab} · {m}", va='center', ha='right', fontsize=8.6 * S, fontweight='bold', color=col)
        left = 17
        for j in sorted(range(len(A)), key=lambda j: -x['a'][j]):
            if x['a'][j]:
                w = (60 / S) * x['a'][j] / pmax
                ax.add_patch(plt.Rectangle((left, i + 0.06), w, 0.27, fc=A[j]['color'], ec='white', lw=0.5))
                left += w
        ax.text(left + 0.8, i + 0.2, f"{x['p']} papers · {x['core']} oral/spot.", va='center', fontsize=9.5 * S, fontweight='bold', color=INK)

    fig.text(0.06, 0.188, 'Research areas (grouped CoRL subject areas)', fontsize=11 * S, fontweight='bold', color=INK)
    order = sorted(range(len(A)), key=lambda j: -A[j]['total'])
    for k, j in enumerate(order):
        cx, cy = 0.06 + (k % 4) * 0.225, 0.165 - (k // 4) * 0.026
        fig.patches.append(plt.Rectangle((cx, cy - 0.004), 0.012, 0.009, fc=A[j]['color'], transform=fig.transFigure, figure=fig))
        fig.text(cx + 0.017, cy, f"{A[j]['short']} ({A[j]['total']})", fontsize=(8.8 if S == 1 else 7.6) * S, color=INK, va='center')
    fig.text(0.06, 0.045, 'Badges are abbreviations, colored by each institution’s top research area.', fontsize=8.0 * S, color=MUTED)
    fig.text(0.06, 0.030, 'Unofficial; papers from corl.org, authors from OpenReview, affiliations from OpenAlex and arXiv.', fontsize=8.0 * S, color=MUTED)
    fig.savefig(out, facecolor='white')
    plt.close(fig)


draw_poster(site / 'assets' / 'poster.png')
# poster_2.png: print version (600 dpi, text 1.3x larger); not linked from the site
draw_poster(site / 'assets' / 'poster_2.png', dpi=600, S=1.3)

fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor='white')
fig.text(0.06, 0.70, 'CoRL 2026', fontsize=66, fontweight='bold', color=BRAND)
fig.text(0.06, 0.56, 'Conference on Robot Learning', fontsize=36, fontweight='bold', color=INK)
fig.text(0.06, 0.44, 'Who publishes what at CoRL 2026, by institution, topic and author', fontsize=17, color=MUTED)
fig.text(0.06, 0.20, f"{M['papers']:,} papers · {M['core']:,} orals & spotlights · {M['institutions']:,} institutions · {len(M['countries'])} countries",
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
    '<stop offset="0" stop-color="#7c2d12"/><stop offset=".55" stop-color="#ea580c"/><stop offset="1" stop-color="#f59e0b"/>'
    '</linearGradient></defs><rect width="64" height="64" rx="14" fill="url(#g)"/>'
    '<path d="M10 40 C22 40 22 18 32 18 S42 46 54 30" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>\n')
print('assets written')
