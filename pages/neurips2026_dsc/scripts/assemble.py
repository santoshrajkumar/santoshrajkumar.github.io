"""Assemble site/index.html from the template parts. Usage: python3 -I assemble.py <site_dir> <neurips.json>"""
import hashlib, json, sys
from pathlib import Path
site, src = Path(sys.argv[1]), Path(sys.argv[2])
T = Path(__file__).parent / 'template'
css = (T / '_base.css').read_text()
# NeurIPS tone: slate -> sky blue -> indigo gradient, sky accent
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #1e3a8a 0%, #0ea5e9 55%, #6366f1 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #0284c7;').replace('--accent: #8b8cff;', '--accent: #38bdf8;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
d = json.loads(src.read_text())
EXAMPLE_ID = '152141'   # K-PWM (my NeurIPS 2026 paper): example paper on the Topics page
pl = next(p for p in d['papers'] if p['id'] == EXAMPLE_ID)
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js')).replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('"__EXAMPLE__"', json.dumps(pl['title'] + '. ' + pl['abstract'], ensure_ascii=False).replace('</', '<\\/'))
body = body.replace('__EXAMPLE_TITLE__', pl['title'])
# author hints: the four authors with the most DSC papers (ties broken by core papers)
from collections import Counter
import html
ps = (site / 'papers.js').read_text(); PP = json.loads(ps[ps.index('=') + 1:].strip().rstrip(';'))
cnt, core = Counter(), Counter()
for r in PP['rows']:
    for a in r[8]: cnt[a] += 1; core[a] += r[7]
top = [a for a in sorted(cnt, key=lambda a: (-cnt[a], -core[a], PP['authors'][a][0])) if PP['authors'][a][0] != 'Santosh M Rajkumar'][:3]
hints = '<button data-a="Santosh M Rajkumar">Santosh Rajkumar</button>·' + '·'.join(f'<button data-a="{html.escape(PP["authors"][a][0])}">{html.escape(PP["authors"][a][0])}</button>' for a in top)
body = body.replace('__AUTHOR_HINTS__', hints)
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()))
