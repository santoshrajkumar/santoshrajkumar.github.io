"""Assemble <site_dir>/index.html from the template parts. Usage: python3 -I assemble.py <site_dir> <ral.json>"""
import hashlib
import html
import json
import sys
from pathlib import Path

site, src = Path(sys.argv[1]), Path(sys.argv[2])
T = Path(__file__).parent / 'template'
EXAMPLE_DOI = '10.1109/lra.2025.3626234'  # example abstract on the Topics page (my RA-L paper)
INST_HINTS = ['The Ohio State University', 'ETH Zurich', 'CMU', 'KAIST', 'TU Delft', 'Nvidia']
AUTHOR_HINTS = [('Rajkumar, Santosh Mohan', 'Santosh Rajkumar'), ('Hutter, Marco', 'Marco Hutter'),
                ('Scaramuzza, Davide', 'Davide Scaramuzza'), ('Kumar, Vijay', 'Vijay Kumar'), ('Rus, Daniela', 'Daniela Rus')]

css = (T / '_base.css').read_text()
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #1d4ed8 0%, #7c3aed 55%, #db2777 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #7c3aed;').replace('--accent: #8b8cff;', '--accent: #a78bfa;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
d = json.loads(src.read_text())
ex = next(p for p in d['papers'] if p['id'] == EXAMPLE_DOI)
esc = html.escape
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js'))
body = body.replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('"__PLENARY__"', json.dumps(ex['title'] + '. ' + ex['abstract'], ensure_ascii=False).replace('</', '<\\/'))
body = body.replace('__EXAMPLE_TITLE__', esc(ex['title'])).replace('__EXAMPLE_NOTE__', f"my RA-L {ex['year']} paper")
body = body.replace('__AUTHOR_EG__', AUTHOR_HINTS[0][1])
body = body.replace('__INST_HINTS__', '·'.join(f'<button data-q="{esc(q)}">{esc(q)}</button>' for q in INST_HINTS))
body = body.replace('__AUTHOR_HINTS__', '·'.join(f'<button data-a="{esc(a)}">{esc(b)}</button>' for a, b in AUTHOR_HINTS))
assert '__' not in body.replace('__proto__', ''), [l for l in body.split('\n') if '__' in l][:3]
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()))
