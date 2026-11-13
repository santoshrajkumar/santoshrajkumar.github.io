"""Download the public NeurIPS 2026 program data into raw/.

Usage: python3 -I fetch.py <raw_dir>
Files: neurips-2026-orals-posters.json (events with authors and institutions), neurips-2026-abstracts.json
(event id -> abstract), both from neurips.cc; juevn_papers.js / juevn_data.js from the unofficial NeurIPS 2026
Explorer (github.com/juevn/neurips2026), used only for its research-area clusters.
"""
import sys, urllib.request
from pathlib import Path

raw = Path(sys.argv[1]); raw.mkdir(parents=True, exist_ok=True)
FILES = {
    'neurips-2026-orals-posters.json': 'https://neurips.cc/static/virtual/data/neurips-2026-orals-posters.json',
    'neurips-2026-abstracts.json': 'https://neurips.cc/static/virtual/data/neurips-2026-abstracts.json',
    'juevn_papers.js': 'https://raw.githubusercontent.com/juevn/neurips2026/main/papers.js',
    'juevn_data.js': 'https://raw.githubusercontent.com/juevn/neurips2026/main/data.js',
}
for name, url in FILES.items():
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (neurips2026-dsc explorer)'})
    data = urllib.request.urlopen(req, timeout=120).read()
    (raw / name).write_bytes(data)
    print(name, len(data), 'bytes')
