"""Parse the CDC 2026 PaperPlaza daily program pages into papers.json.

Usage: python3 -I parse_cdc.py <raw_dir> <out_json>
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
DAYS = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday'}
HDR = re.compile(r'^(\S+)\s+(.+?),\s*(.+?),\s*(\d\d:\d\d\s*-\s*\d\d:\d\d)\s*$')


def aid(td):
    a = td.find('a', href=re.compile(r'AuthorIndex'))
    return a['href'].split('#')[-1] if a else ''


def txt(node):
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True)).strip() if node else ''


sessions, papers = [], []
for d, dayname in DAYS.items():
    html = (raw / f'CDC26_ContentListWeb_{d}.html').read_bytes().decode('cp1252', errors='replace')
    soup = BeautifulSoup(html, 'lxml')
    h3 = soup.find('h3')
    date = txt(h3).replace('Technical Program for ', '') if h3 else dayname
    for chunk in html.split('<table class="trk">')[1:]:
        chunk = chunk.split('</table>')[0]
        t = BeautifulSoup('<table>' + chunk + '</table>', 'lxml')
        rows = t.select('tr')
        shdr = [r for r in rows if 'sHdr' in (r.get('class') or [])]
        if not shdr:
            continue
        head = txt(shdr[0].find('td')).replace('\xa0', ' ')
        m = HDR.match(head)
        if not m:
            print('?? header', head, file=sys.stderr)
            continue
        code, stype, room, time = m.groups()
        stitle = txt(shdr[1].find('td')) if len(shdr) > 1 else ''
        ses = {'code': code, 'type': stype, 'room': room, 'time': time.replace(' ', ''),
               'day': dayname, 'date': date, 'title': stitle, 'chairs': []}
        sidx = len(sessions)
        sessions.append(ses)
        cur = None
        for r in rows:
            cls = r.get('class') or []
            tds = r.find_all('td', recursive=False)
            if 'sHdr' in cls:
                continue
            first = txt(tds[0]) if tds else ''
            if cur is None and re.match(r'^(Chair|Co-Chair|Organizer|Co-Organizer)s?:', first):
                ses['chairs'].append([first.split(':', 1)[1].strip(), txt(tds[1]) if len(tds) > 1 else '', aid(tds[0]), first.split(':', 1)[0]])
                continue
            if 'pHdr' in cls:
                a = tds[0].find('a')
                hm = re.match(r'^(\S+),\s*Paper\s+(\S+)', txt(tds[0]))
                inp = r.find('input')
                num = re.search(r'modify\((\d+)', inp.get('onclick', '')).group(1) if inp else None
                cur = {'id': num, 'code': hm.group(2) if hm else '', 'time': hm.group(1) if hm else '',
                       'anchor': a.get('name') if a else '', 'session': sidx, 'title': '',
                       'authors': [], 'keywords': [], 'abstract': ''}
                papers.append(cur)
                continue
            if cur is None:
                continue
            ttl = r.find('span', class_='pTtl')
            if ttl:
                cur['title'] = txt(ttl)
                continue
            if 'author-row' in cls:
                cur['authors'].append([txt(tds[0]), txt(tds[1]) if len(tds) > 1 else '', aid(tds[0])])
                continue
            ab = r.find('div', id=re.compile(r'^Ab\d+'))
            if ab:
                cur['keywords'] = [txt(k) for k in ab.select('a[href*="KeywordIndex"]')]
                full = txt(ab)
                i = full.find('Abstract:')
                cur['abstract'] = full[i + 9:].strip() if i >= 0 else ''

for p in papers:
    p['title'] = p['title'].strip()
json.dump({'sessions': sessions, 'papers': papers}, out.open('w'), ensure_ascii=False, indent=0)
print(len(sessions), 'sessions,', len(papers), 'papers')
from collections import Counter
print(Counter(s['type'] for s in sessions))
print(Counter(sessions[p['session']]['type'] for p in papers))
print('no abstract', sum(not p['abstract'] for p in papers), 'no authors', sum(not p['authors'] for p in papers),
      'no kw', sum(not p['keywords'] for p in papers), 'no title', sum(not p['title'] for p in papers))
