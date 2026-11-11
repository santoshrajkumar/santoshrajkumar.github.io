"""Assemble <site>/index.html from the template parts. Usage: python3 -I assemble.py <site_dir>"""
import hashlib, json, sys
from pathlib import Path
site = Path(sys.argv[1])
T = Path(__file__).parent / 'template'
css = (T / '_base.css').read_text()
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #6d28d9;').replace('--accent: #8b8cff;', '--accent: #a78bfa;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
s = (site / 'data.js').read_text()
M = json.loads(s[s.index('=') + 1:].rstrip().rstrip(';'))['meta']
example = (T / 'example.txt').read_text().strip()  # abstract for the "try a whole abstract" button
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js')).replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('__LASTYEAR__', str(M['years'][-1]))
body = body.replace('"__PLENARY__"', json.dumps(example, ensure_ascii=False).replace('</', '<\\/'))
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()))
