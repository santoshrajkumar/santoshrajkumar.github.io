"""Turn the raw neurips.cc feeds into neurips.json: one record per accepted main-track paper.

Usage: python3 -I normalize.py <raw_dir> <out_json>
Oral papers appear twice in the feed (an Oral event and a Poster event); they are merged into one record keyed by
the OpenReview forum, with presentation = Oral. Only the main track (sourceurl .../NeurIPS.cc/2026/Conference).
"""
import html, json, re, sys
from collections import OrderedDict, Counter
from pathlib import Path

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
EV = json.loads((raw / 'neurips-2026-orals-posters.json').read_text())['results']
AB = json.loads((raw / 'neurips-2026-abstracts.json').read_text())
s = (raw / 'juevn_papers.js').read_text(); JP = json.loads(s[s.index('=') + 1:].strip().rstrip(';'))
s = (raw / 'juevn_data.js').read_text(); JD = json.loads(s[s.index('=') + 1:].strip().rstrip(';'))
JAREAS = [a['name'] for a in JD['meta']['areas']]
JIDX = {r[3].split('/')[-1]: r[2] for r in JP['rows']}

def pres(decisions, types):
    if 'Oral' in types or any('oral' in (d or '').lower() for d in decisions): return 'Oral'
    if any('spotlight' in (d or '').lower() for d in decisions): return 'Spotlight'
    return 'Poster'

def clean_abs(t):
    t = html.unescape((t or '').strip())
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)          # OpenReview markdown emphasis
    t = re.sub(r'(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'\1', t)
    return re.sub(r'[ \t]+', ' ', t).strip()

groups = OrderedDict()
for e in EV:
    if '2026/Conference' not in (e.get('sourceurl') or ''):
        continue
    groups.setdefault(e.get('paper_url') or f"event:{e['id']}", []).append(e)
papers = []
for key, evs in groups.items():
    evs.sort(key=lambda e: (e['event_type'] != 'Poster', e['id']))
    e = evs[0]
    jidx = next((JIDX[str(x['id'])] for x in evs if str(x['id']) in JIDX), None)
    papers.append({
        'id': str(e['id']), 'title': html.unescape(' '.join((e.get('name') or '').split())),
        'abstract': clean_abs(next((AB.get(str(x['id'])) for x in evs if AB.get(str(x['id']))), '')),
        'authors': [[html.unescape(a.get('fullname', '').strip()), html.unescape((a.get('institution') or '').strip()), str(a.get('id'))] for a in e.get('authors') or []],
        'presentation': pres([x.get('decision') for x in evs], [x['event_type'] for x in evs]),
        'decision': e.get('decision') or '',
        'sessions': sorted({x.get('session') for x in evs if x.get('session')}),
        'room': e.get('room_name') or '', 'start': e.get('starttime') or '',
        'openreview': e.get('paper_url') or '', 'url': 'https://neurips.cc' + (e.get('virtualsite_url') or ''),
        'jarea': JAREAS[jidx] if jidx is not None else '', 'jidx': jidx,
    })
json.dump({'areas_unofficial': JAREAS, 'papers': papers}, out.open('w'), ensure_ascii=False, indent=0)
print(len(papers), 'main-track papers;', Counter(p['presentation'] for p in papers))
print('no abstract', sum(not p['abstract'] for p in papers), '| no authors', sum(not p['authors'] for p in papers),
      '| no unofficial area', sum(p['jidx'] is None for p in papers))
print('city sessions', Counter(s.split(' Poster')[0] for p in papers for s in p['sessions']))
