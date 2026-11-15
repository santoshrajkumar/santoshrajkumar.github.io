"""Assemble index.html from the template parts. Usage: python3 -I assemble.py <site_dir> <corl2026_papers.json>"""
import hashlib, html, json, sys
from collections import Counter
from pathlib import Path
site, src = Path(sys.argv[1]), Path(sys.argv[2])
T = Path(__file__).parent / 'template'
css = (T / '_base.css').read_text()
# CoRL tone: deep rust -> orange -> amber gradient, orange accent
css = css.replace('--grad: linear-gradient(92deg, #2563eb 0%, #7c3aed 50%, #ea580c 100%);',
                  '--grad: linear-gradient(92deg, #7c2d12 0%, #ea580c 55%, #f59e0b 100%);')
css = css.replace('--accent: #4f46e5;', '--accent: #c2410c;').replace('--accent: #8b8cff;', '--accent: #fb923c;')
body = (T / '_body.html').read_text()
h = lambda f: hashlib.sha1((site / f).read_bytes()).hexdigest()[:10]
d = json.loads(src.read_text())
EXAMPLE_ID = 'Bshs9HDDiu'   # "World Action Models are Zero-shot Policies" (Oral O2): example paper on the Topics page
pl = next(p for p in d['papers'] if p['id'] == EXAMPLE_ID)
body = body.replace('__IMGVER__', h('assets/poster.png')).replace('__DVER__', h('data.js')).replace('__PVER__', hashlib.sha1((site / 'papers.js').read_bytes() + (site / 'papers.bin').read_bytes()).hexdigest()[:10])
body = body.replace('"__EXAMPLE__"', json.dumps(pl['title'] + '. ' + pl['abstract'], ensure_ascii=False).replace('</', '<\\/'))
body = body.replace('__EXAMPLE_TITLE__', html.escape(pl['title']))
# author hints: the four authors with the most papers (ties broken by orals/spotlights)
ps = (site / 'papers.js').read_text(); PP = json.loads(ps[ps.index('=') + 1:].strip().rstrip(';'))
cnt, hl = Counter(), Counter()
for r in PP['rows']:
    for a in r[8]: cnt[a] += 1; hl[a] += r[7]
top = sorted(cnt, key=lambda a: (-cnt[a], -hl[a], PP['authors'][a][0]))[:4]
hints = '·'.join(f'<button data-a="{html.escape(PP["authors"][a][0])}">{html.escape(PP["authors"][a][0])}</button>' for a in top)
body = body.replace('__AUTHOR_HINTS__', hints)
(site / 'index.html').write_text((T / '_head.html').read_text() + css + (T / '_extra.css').read_text() + body)
print('ok', len((site / 'index.html').read_text()), 'hints', [PP['authors'][a][0] for a in top])
