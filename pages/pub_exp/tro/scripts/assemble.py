"""Assemble <site_dir>/index.html from the template parts. Usage: python3 -I assemble.py <site_dir> <tro.json>"""
import hashlib
import html
import json
import sys
from pathlib import Path

site, src = Path(sys.argv[1]), Path(sys.argv[2])
T = Path(__file__).parent / 'template'
EXAMPLE_DOI = '10.1109/lra.2025.3626234'  # example abstract on the Topics page (my RA-L paper; title and abstract in example_paper.json)
INST_HINTS = ['The Ohio State University', 'ETH Zurich', 'CMU', 'KAIST', 'TU Delft', 'Nvidia']
AUTHOR_HINTS = [('Rajkumar, Santosh Mohan', 'Santosh Rajkumar'), ('Hutter, Marco', 'Marco Hutter'),
                ('Scaramuzza, Davide', 'Davide Scaramuzza'), ('Kumar, Vijay', 'Vijay Kumar'), ('Rus, Daniela', 'Daniela Rus')]

css = (T / '_base.css').read_text()
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #0f766e 0%, #0284c7 55%, #4f46e5 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #0f766e;').replace('--accent: #8b8cff;', '--accent: #2dd4bf;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
d = json.loads(src.read_text())
ex = json.loads((Path(__file__).parent / 'example_paper.json').read_text())
assert ex['id'] == EXAMPLE_DOI
names = {a['name'] for p in d['papers'] for a in p['authors']}
AUTHOR_HINTS = [h for h in AUTHOR_HINTS if h[0] in names]
esc = html.escape
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js'))
body = body.replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('"__PLENARY__"', json.dumps(ex['title'] + '. ' + ex['abstract'], ensure_ascii=False).replace('</', '<\\/'))
body = body.replace('__EXAMPLE_TITLE__', esc(ex['title'])).replace('__EXAMPLE_NOTE__', f"my RA-L {ex['year']} paper")
body = body.replace('__AUTHOR_EG__', AUTHOR_HINTS[0][1])
body = body.replace('__INST_HINTS__', '·'.join(f'<button data-q="{esc(q)}">{esc(q)}</button>' for q in INST_HINTS))
body = body.replace('__AUTHOR_HINTS__', '·'.join(f'<button data-a="{esc(a)}">{esc(b)}</button>' for a, b in AUTHOR_HINTS))
# ---- top 10 most cited papers (OpenAlex counts from cited.py) ----
cf = site / 'raw' / 'cited.json'
lf = site / 'scripts' / 'links' / 'links.json'
links = json.loads(lf.read_text()) if lf.exists() else {}
top = ''
if cf.exists():
    C = json.loads(cf.read_text())
    byid = {p['id']: p for p in d['papers']}
    rows = []
    for i, (doi, n) in enumerate(sorted(((k, v) for k, v in C['counts'].items() if k in byid), key=lambda x: -x[1])[:10]):
        p = byid[doi]
        au = [a['name'].split(',')[0] for a in p['authors']]
        who = ', '.join(au) if len(au) <= 3 else f'{au[0]} et al.'
        ax = (links.get(doi) or {}).get('arxiv') or p.get('arxiv')
        extra = f' · <a href="https://arxiv.org/abs/{esc(ax)}" rel="noopener">arXiv</a>' if ax else ''
        code = ((links.get(doi) or {}).get('code') or [])[:1]
        extra += ''.join(f' · <a href="{esc(u)}" rel="noopener">code</a>' for u in code)
        rows.append(f'<li><span class="rk">{i + 1}</span><a class="t" href="https://doi.org/{esc(doi)}" rel="noopener">{esc(p["title"])}</a>'
                    f'<span class="c">{n:,}<small>citations</small></span><span class="m">{esc(who)} · {p["year"]}{extra}</span></li>')
    top = ('    <section class="cited" aria-label="Most cited papers">\n      <h2>Most cited T-RO papers</h2>\n'
           f'      <p class="sub">All time, by citation count in <a href="https://openalex.org/" rel="noopener">OpenAlex</a> ({C["fetched"]}). '
           'Google Scholar counts are higher.</p>\n      <ol>' + ''.join(rows) + '</ol>\n    </section>')
body = body.replace('__TOPCITED__', top)
assert '__' not in body.replace('__proto__', ''), [l for l in body.split('\n') if '__' in l][:3]
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()))
