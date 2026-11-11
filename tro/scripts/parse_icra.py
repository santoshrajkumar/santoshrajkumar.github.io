"""Parse the ICRA 2026 PaperCept program into icra26.json: the official RAS keyword list, and every paper's
title, abstract and author-chosen keywords. build.py uses these papers as labeled examples to place RA-L papers
into research areas (RA-L, ICRA and IROS share the same RAS keyword list).

Download first (into <raw_dir>):
  https://ras.papercept.net/conferences/conferences/ICRA26/program/ICRA26_KeywordIndexWeb.html
  https://ras.papercept.net/conferences/conferences/ICRA26/program/ICRA26_ContentListWeb_{1..6}.html

Usage: python3 -I parse_icra.py <raw_dir> <out icra26.json>
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

raw, out = Path(sys.argv[1]), Path(sys.argv[2])


def txt(node):
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)).strip() if node else ''


s = (raw / 'ICRA26_KeywordIndexWeb.html').read_bytes().decode('cp1252', errors='replace')
KW = [BeautifulSoup(k, 'lxml').get_text().strip() for k in re.findall(r'<td width="200"><a name="[^"]*">(.*?)</a></td>', s)]

papers = []
for f in sorted(raw.glob('ICRA26_ContentListWeb_*.html')):
    html = f.read_bytes().decode('cp1252', errors='replace')
    for chunk in html.split('<table class="trk">')[1:]:
        t = BeautifulSoup('<table>' + chunk.split('</table>')[0] + '</table>', 'lxml')
        cur = None
        for r in t.select('tr'):
            cls = r.get('class') or []
            if 'pHdr' in cls:
                cur = {'title': '', 'keywords': [], 'abstract': ''}
                papers.append(cur)
                continue
            if cur is None:
                continue
            ttl = r.find('span', class_='pTtl')
            if ttl:
                cur['title'] = txt(ttl)
                continue
            ab = r.find('div', id=re.compile(r'^Ab\d+'))
            if ab:
                cur['keywords'] = [txt(k) for k in ab.select('a[href*="KeywordIndex"]')]
                full = txt(ab)
                i = full.find('Abstract:')
                cur['abstract'] = full[i + 9:].strip() if i >= 0 else ''
papers = [p for p in papers if p['title'] and p['keywords']]
json.dump({'keywords': KW, 'papers': papers}, out.open('w'), ensure_ascii=False, indent=0)
print(len(KW), 'keywords |', len(papers), 'papers with keywords |', sum(bool(p['abstract']) for p in papers), 'with abstract')
unknown = {k for p in papers for k in p['keywords']} - set(KW)
print('keywords used but not in the index:', sorted(unknown)[:20])
