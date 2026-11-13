#!/bin/bash
# arXiv -> GitHub -> merge -> rebuild, for the DSC papers. Logs to work/links.log
set -e
D=/home/santosh/Downloads/fameqp/santoshrajkumar.github.io/pages/neurips2026_dsc
cd "$D"
echo "== arXiv start $(date)"
python3 -I scripts/links/arxiv_match.py neurips.json work/arxiv_cache.json work/dsc_ids.txt
echo "== GitHub start $(date)"
python3 -I scripts/links/github_match.py neurips.json work/github_cache.json work/dsc_ids.txt work/arxiv_cache.json
echo "== merge + rebuild $(date)"
python3 -I scripts/links/merge_links.py neurips.json work/arxiv_cache.json work/github_cache.json work/links.json
venv/bin/python -I scripts/build.py neurips.json work . work/links.json | head -2
venv/bin/python -I scripts/poster.py .
python3 -I scripts/assemble.py . neurips.json
echo "== done $(date)"
