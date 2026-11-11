#!/usr/bin/env bash
# Rebuild the TAC Explorer with the latest papers.
#
#   ./update.sh            download new papers, search arXiv/GitHub for new ones, rebuild the site
#   ./update.sh --quick    download new papers and rebuild; skip the slow arXiv/GitHub searches
#   ./update.sh --links    only run the arXiv/GitHub searches (resumable) and rebuild
#
# The arXiv and GitHub searches are cached in scripts/links/, so after the first full run they only
# look at papers they haven't seen. The first full run takes several hours (API rate limits).
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-}"

if [ ! -x venv/bin/python ]; then
  python3 -m venv venv
  venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
  venv/bin/pip install sentence-transformers numpy matplotlib
fi

if [ "$MODE" != "--links" ]; then
  echo "== downloading papers (Crossref + OpenAlex)"
  python3 -I scripts/fetch.py tac.json raw
  echo "== citation counts (OpenAlex)"
  python3 -I scripts/citations.py tac.json raw
fi

if [ "$MODE" != "--quick" ]; then
  echo "== arXiv search"
  python3 -I -u scripts/links/arxiv_match.py tac.json scripts/links/arxiv_cache.json
  echo "== GitHub search"
  python3 -I -u scripts/links/github_match.py tac.json scripts/links/github_cache.json scripts/links/arxiv_cache.json
fi

echo "== building site"
python3 -I scripts/links/merge_links.py tac.json scripts/links/arxiv_cache.json scripts/links/github_cache.json scripts/links/links.json
venv/bin/python -I scripts/build.py tac.json . scripts/links/links.json ../cdc2026
venv/bin/python -I scripts/poster.py .
python3 -I scripts/assemble.py .
echo "== done. Preview: python3 -m http.server (in the repo root), then open http://localhost:8000/tac/"
