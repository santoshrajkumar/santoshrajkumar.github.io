#!/usr/bin/env python3
"""Fetch per-author affiliations from OpenAlex for every paper with an arXiv ID.

Looks works up by arXiv DOI (10.48550/arXiv.<id>), 50 per request, and caches each
raw response in raw/openalex/batch_NN.json (skipped if already present).
Writes raw/openalex/by_arxiv.json: {arxiv_id: {title, authorships:[...]}}.
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "raw" / "openalex"
OUT.mkdir(parents=True, exist_ok=True)

papers = json.loads((ROOT / "corl2026_papers.json").read_text())["papers"]
ids = sorted({m.group(1) for p in papers if (m := re.search(r"(\d{4}\.\d{4,5})", p.get("arxiv") or ""))})
print(len(ids), "arXiv IDs")

by = {}
for n in range(0, len(ids), 50):
    chunk = ids[n:n + 50]
    f = OUT / f"batch_{n // 50:02d}.json"
    if not f.exists():
        flt = "doi:" + "|".join("10.48550/arxiv." + a for a in chunk)
        url = ("https://api.openalex.org/works?per-page=50&select=doi,title,authorships&filter="
               + urllib.parse.quote(flt, safe=":|/"))
        req = urllib.request.Request(url, headers={"User-Agent": "paper-metadata-script"})
        with urllib.request.urlopen(req, timeout=60) as r:
            f.write_text(r.read().decode())
        time.sleep(1)
    for w in json.loads(f.read_text())["results"]:
        a = re.search(r"arxiv\.(\d{4}\.\d{4,5})", (w.get("doi") or "").lower())
        if a:
            by[a.group(1)] = {
                "title": w.get("title"),
                "authorships": [{
                    "name": x["author"]["display_name"],
                    "institutions": [i["display_name"] for i in x.get("institutions") or []],
                    "countries": x.get("countries") or [],
                    "raw": x.get("raw_affiliation_strings") or [],
                } for x in w["authorships"]],
            }
(OUT / "by_arxiv.json").write_text(json.dumps(by, ensure_ascii=False, indent=1))
print("found", len(by), "with any institution",
      sum(1 for v in by.values() if any(x["institutions"] for x in v["authorships"])))
