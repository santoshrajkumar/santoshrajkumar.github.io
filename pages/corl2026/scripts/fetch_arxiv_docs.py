#!/usr/bin/env python3
"""Download arXiv HTML (or PDF when no HTML exists) for papers that still have
authors without an affiliation after OpenAlex. Cached in raw/arxiv/<id>.html|.pdf;
already-downloaded files are skipped. ~1 request / 3 s to respect arXiv limits.
"""
import json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "raw" / "arxiv"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (paper-metadata-script)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, r.geturl(), r.read()


papers = json.loads((ROOT / "corl2026_papers.json").read_text())["papers"]
todo = []
for p in papers:
    m = re.search(r"(\d{4}\.\d{4,5})", p.get("arxiv") or "")
    if not m:
        continue
    aff = p["author_affiliations"] or [{"institutions": []} for _ in p["authors"]]
    if any(not a["institutions"] for a in aff):
        todo.append(m.group(1))
print(len(todo), "papers to fetch", flush=True)

log = []
for n, aid in enumerate(todo, 1):
    if (OUT / f"{aid}.html").exists() or (OUT / f"{aid}.pdf").exists():
        continue
    status = ""
    try:
        code, final, body = get(f"https://arxiv.org/html/{aid}")
        # arXiv serves a "no HTML for this paper" page or redirects to /abs when conversion failed
        if b"ltx_document" in body or b"ltx_authors" in body:
            (OUT / f"{aid}.html").write_bytes(body)
            status = "html"
        else:
            raise urllib.error.HTTPError(final, 404, "no html", None, None)
    except urllib.error.HTTPError:
        time.sleep(3)
        try:
            code, final, body = get(f"https://arxiv.org/pdf/{aid}")
            if body[:4] == b"%PDF":
                (OUT / f"{aid}.pdf").write_bytes(body)
                status = "pdf"
            else:
                status = "fail:not-pdf"
        except Exception as e:  # noqa: BLE001
            status = f"fail:{e}"
    except Exception as e:  # noqa: BLE001
        status = f"fail:{e}"
    log.append(f"{aid}\t{status}")
    print(n, aid, status, flush=True)
    time.sleep(3)

with open(ROOT / "work" / "arxiv_fetch.log", "a") as f:
    f.write("\n".join(log) + "\n")
print("done", flush=True)
