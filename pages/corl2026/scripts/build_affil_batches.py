#!/usr/bin/env python3
"""Build per-paper evidence (arXiv HTML front matter + PDF page-1 header/footnotes)
for authors that OpenAlex left without an affiliation. Writes
work/affil_batches/batch_NN.json (N papers each) for the author->institution mapping pass.
"""
import html, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AX = ROOT / "raw" / "arxiv"
OUT = ROOT / "work" / "affil_batches"
OUT.mkdir(parents=True, exist_ok=True)
PER = int(sys.argv[1]) if len(sys.argv) > 1 else 46


def squash(s):
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def html_front(aid):
    f = AX / f"{aid}.html"
    if not f.exists():
        return ""
    t = f.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", t, flags=re.S | re.I)
    i = t.find("<article")
    if i < 0:
        i = t.find('class="ltx_title ltx_title_document"')
    i = max(i, 0)
    j = t.find('class="ltx_abstract"', i)
    j = t.rfind("<", i, j) if j > 0 else i + 20000
    seg = t[i:j]
    seg = re.sub(r"<sup[^>]*>(.*?)</sup>", lambda m: "^{" + re.sub(r"<[^>]+>", "", m.group(1)) + "}", seg, flags=re.S)
    seg = re.sub(r'<span class="ltx_personname">', "\n[AUTHOR-BLOCK] ", seg)
    seg = re.sub(r'<span class="ltx_contact_name">Affiliation: </span>', "[AFFIL] ", seg)
    seg = re.sub(r"<math[^>]*alttext=\"([^\"]*)\".*?</math>", lambda m: m.group(1), seg, flags=re.S)
    seg = re.sub(r"<[^>]+>", " ", seg)
    return squash(html.unescape(seg))[:3000]


def pdf_page1(aid):
    f = AX / f"{aid}.pdf"
    if not f.exists():
        return ""
    try:
        txt = subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(f), "-"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:  # noqa: BLE001
        return ""
    txt = squash(txt)
    k = re.search(r"\n\s*(Abstract|ABSTRACT|Abstract[:.—-])", txt)
    head = txt[: k.start()] if k and k.start() < 4000 else txt[:2500]
    tail = txt[-1200:] if len(txt) > 3000 else ""
    return head[:3000] + ("\n[...PAGE-1 BOTTOM (footnotes)...]\n" + tail if tail else "")


papers = json.loads((ROOT / "corl2026_papers.json").read_text())["papers"]
items = []
for p in papers:
    m = re.search(r"(\d{4}\.\d{4,5})", p.get("arxiv") or "")
    if not m:
        continue
    aff = p["author_affiliations"] or [{"name": a, "institutions": []} for a in p["authors"]]
    missing = [a["name"] for a in aff if not a["institutions"]]
    if not missing:
        continue
    aid = m.group(1)
    h, pdf = html_front(aid), pdf_page1(aid)
    items.append({
        "id": p["id"], "arxiv": aid, "title": p["title"],
        "authors": p["authors"],
        "missing_authors": missing,
        "known": {a["name"]: a["institutions"] for a in aff if a["institutions"]},
        "html_front_matter": h,
        "pdf_page1": pdf,
    })

for f in OUT.glob("batch_*.json"):
    f.unlink()
for n in range(0, len(items), PER):
    (OUT / f"batch_{n // PER:02d}.json").write_text(json.dumps(items[n:n + PER], ensure_ascii=False, indent=1))
print(len(items), "papers;", sum(len(i["missing_authors"]) for i in items), "authors;",
      "no evidence:", sum(1 for i in items if not i["html_front_matter"] and not i["pdf_page1"]),
      "; batches:", len(list(OUT.glob("batch_*.json"))))
