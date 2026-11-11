#!/usr/bin/env bash
# Rebuild the T-RO Explorer with the latest T-RO papers (new issues and early access).
#
#   scripts/update.sh            papers, institutions, areas, pages (a few minutes; keeps existing arXiv/code links)
#   scripts/update.sh --arxiv    also refresh arXiv links (re-downloads only the last ~4 months of arXiv)
#   scripts/update.sh --github   also search GitHub for code of papers not searched yet (slow: ~10 papers/min)
#
# Python with sentence-transformers and matplotlib: set PY=/path/to/python, default venv/bin/python.
# Optional: OPENALEX_API_KEY (raises OpenAlex's daily request budget), GITHUB_TOKEN (3x faster GitHub search).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-venv/bin/python}
ARXIV=0; GITHUB=0
for a in "$@"; do case $a in --arxiv) ARXIV=1 ;; --github) GITHUB=1 ;; *) echo "unknown option $a"; exit 1 ;; esac; done
mkdir -p raw/arxiv scripts/links

echo "== papers (Crossref + OpenAlex)"
python3 -I scripts/fetch.py tro.json raw
python3 -I scripts/inst_meta.py tro.json raw/institutions.json
python3 -I scripts/cited.py tro.json raw/cited.json

if [ ! -f raw/icra26.json ]; then
  echo "== ICRA 2026 keywords"
  mkdir -p raw/icra26
  B=https://ras.papercept.net/conferences/conferences/ICRA26/program
  curl -sf -A 'Mozilla/5.0' -o raw/icra26/ICRA26_KeywordIndexWeb.html $B/ICRA26_KeywordIndexWeb.html
  for d in 1 2 3 4 5 6; do curl -sf -A 'Mozilla/5.0' -o raw/icra26/ICRA26_ContentListWeb_$d.html $B/ICRA26_ContentListWeb_$d.html || true; done
  python3 -I scripts/parse_icra.py raw/icra26 raw/icra26.json
fi

if [ $GITHUB = 1 ]; then
  echo "== GitHub search"
  python3 -I scripts/github_match.py tro.json scripts/links/github_cache.json scripts/links/links.json
fi
if [ $ARXIV = 1 ] || [ $GITHUB = 1 ] || [ ! -f scripts/links/links.json ]; then
  echo "== arXiv + code links"
  python3 -I scripts/links.py tro.json raw/arxiv scripts/links/links.json scripts/links/github_cache.json
fi

echo "== build"
$PY -I scripts/build.py tro.json . raw/institutions.json scripts/links/links.json raw/icra26.json
$PY -I scripts/poster.py .
python3 -I scripts/assemble.py . tro.json
echo "done: open index.html through a web server, e.g. python3 -m http.server"
