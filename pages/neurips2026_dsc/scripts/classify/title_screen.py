"""Title screen for the unfiltered remainder (cost control): split unlabelled 'rest' papers into title lists.

Usage: python3 -I title_screen.py <work_dir> make [n_files]   -> work_dir/screen/titles_XX.txt ("id<TAB>title")
       python3 -I title_screen.py <work_dir> apply            -> reads screen/flags_XX.txt (one id per line),
          writes batches for flagged papers (batch_fXX.json) and labels every unflagged paper 'out'
          (labels/batch_screen_out.json, reason 'title screen: no dynamics/control signal').
"""
import json, sys
from pathlib import Path
work, mode = Path(sys.argv[1]), sys.argv[2]
plan = json.load((work / 'batch_plan.json').open())
done = {Path(f).name for f in (work / 'labels').glob('batch_*.json')}
todo = [b for b in plan['rest_batches'] if b not in done]
papers = [x for b in todo for x in json.load((work / 'batches' / b).open())]
sd = work / 'screen'; sd.mkdir(exist_ok=True)
if mode == 'make':
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    step = -(-len(papers) // k)
    for i in range(k):
        (sd / f'titles_{i:02d}.txt').write_text('\n'.join(f"{p['id']}\t{p['title']}" for p in papers[i * step:(i + 1) * step]) + '\n')
    json.dump(todo, (sd / 'screened_batches.json').open('w'))
    print('unlabelled batches', len(todo), '| papers', len(papers), '| files', k)
else:
    todo = json.load((sd / 'screened_batches.json').open())
    papers = [x for b in todo for x in json.load((work / 'batches' / b).open())]
    flagged = set()
    for f in sorted(sd.glob('flags_*.txt')):
        flagged |= {l.strip() for l in f.read_text().split() if l.strip()}
    ids = {p['id'] for p in papers}
    assert flagged <= ids, flagged - ids
    fl = [p for p in papers if p['id'] in flagged]
    for i in range(0, len(fl), 80):
        json.dump(fl[i:i + 80], (work / 'batches' / f'batch_f{i // 80:02d}.json').open('w'), ensure_ascii=False, indent=0)
    out = [{'id': p['id'], 'tier': 'out', 'sub': None, 'reason': 'title screen: no dynamics/control signal'} for p in papers if p['id'] not in flagged]
    json.dump(out, (work / 'labels' / 'batch_screen_out.json').open('w'), indent=0)
    print('screened', len(papers), '| flagged for full read', len(fl), 'in', -(-len(fl) // 80), 'batches | screened out', len(out))
