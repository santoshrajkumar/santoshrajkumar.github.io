"""Assemble site/index.html from the template parts. Usage: python3 -I assemble.py <site_dir> <cdc.json>"""
import hashlib, json, sys
from pathlib import Path
site, src = Path(sys.argv[1]), Path(sys.argv[2])
T = Path(__file__).parent / 'template'
css = (T / '_base.css').read_text()
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #0369a1 0%, #0d9488 55%, #f97316 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #0f766e;').replace('--accent: #8b8cff;', '--accent: #2dd4bf;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
d = json.loads(src.read_text())
pl = next(p for p in d['papers'] if p['code'] == 'TuPL.1')
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js')).replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('"__PLENARY__"', json.dumps(pl['title'] + '. ' + pl['abstract'], ensure_ascii=False).replace('</', '<\\/'))
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()))
