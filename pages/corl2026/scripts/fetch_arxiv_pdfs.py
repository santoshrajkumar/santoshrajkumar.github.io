#!/usr/bin/env python3
"""Download arXiv PDFs (raw/arxiv/<id>.pdf) for the same papers fetch_arxiv_docs.py
targets, so author superscripts can be read from page 1. Cached; ~1 request / 3 s."""
import json, re, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "raw" / "arxiv"
papers = json.loads((ROOT / "corl2026_papers.json").read_text())["papers"]
todo = []
for p in papers:
    m = re.search(r"(\d{4}\.\d{4,5})", p.get("arxiv") or "")
    aff = p["author_affiliations"] or [{"institutions": []} for _ in p["authors"]]
    if m and any(not a["institutions"] for a in aff):
        todo.append(m.group(1))
print(len(todo), "papers", flush=True)
for n, aid in enumerate(todo, 1):
    f = OUT / f"{aid}.pdf"
    if f.exists():
        continue
    try:
        req = urllib.request.Request(f"https://arxiv.org/pdf/{aid}", headers={"User-Agent": "Mozilla/5.0 (paper-metadata-script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
        status = "pdf" if body[:4] == b"%PDF" else "not-pdf"
        if status == "pdf":
            f.write_bytes(body)
    except Exception as e:  # noqa: BLE001
        status = f"fail:{e}"
    print(n, aid, status, flush=True)
    time.sleep(3)
print("done", flush=True)
