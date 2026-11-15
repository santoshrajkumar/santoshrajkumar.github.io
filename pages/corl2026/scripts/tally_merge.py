#!/usr/bin/env python3
"""Tally CoRL 2026 accepted papers on corl.org against third-party metadata
sources, then merge them into one record per paper.

Sources (all in raw/):
  corl_accepted_papers.html         official program (titles, OpenReview IDs, sessions)
  corl_explorer_2026.json           operatic-ai/corl-explorer paper list
  corl_explorer_enrichment.json     its authors/abstract/keywords/arXiv per paper
  gisbi_corl2026_data.json          gisbi-kim/conference-explorers (affiliations, institutions)
  jaywu109_papers.yaml              jaywu109/corl-2026-papers

Outputs (work/ and the folder root):
  work/tally_report.txt             count + ID + title agreement per source
  corl2026_papers.json              merged records
  corl2026_papers.csv               flat table
"""
import csv, html, json, re, sys, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW, WORK = ROOT / "raw", ROOT / "work"


def norm(s):
    s = unicodedata.normalize("NFKC", html.unescape(s or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


# ---------- official site ----------
def parse_site():
    u = html.unescape((RAW / "corl_accepted_papers.html").read_text())
    papers, declared, sessions = {}, {}, []
    m = re.search(r"(\d+) accepted papers", u)
    declared["total"] = int(m.group(1)) if m else None
    # Sections: <section class="session" ...><h3 ...>...</h3><p class="meta">...</p> ... </section>
    for sec in re.finditer(r'<section class="session[^"]*"[^>]*>(.*?)</section>', u, re.S):
        body = sec.group(1)
        h3 = re.search(r"<h3[^>]*>(.*?)</h3>", body, re.S)
        head = strip_tags(h3.group(1))
        meta = re.search(r'<p class="meta">(.*?)</p>', body, re.S)
        meta_t = strip_tags(meta.group(1)) if meta else ""
        nm = re.search(r"(\d+) papers", meta_t)
        declared[head] = int(nm.group(1)) if nm else None
        when = meta_t.split("·")[0].strip()
        is_poster = head.startswith("Poster")
        meta_nl = strip_tags(re.sub(r"<br\s*/?>", "\n", meta.group(1))) if meta else ""
        parts = [x.strip() for x in re.split(r"·|\n", meta_nl) if x.strip()]
        rooms = [(int(a), int(b), room.strip()) for room, a, b in
                 re.findall(r"([^·\n]+?):\s*posters\s*(\d+)\s*[–-]\s*(\d+)", meta_nl)]
        tag = re.search(r'<span class="tag">(.*?)</span>', h3.group(1))
        sessions.append({
            "name": head.replace("Poster ", "", 1) if is_poster else head,
            "code": (re.sub(r"Poster Session (\d+)", r"P\1", head.replace("Poster ", "", 1)) if is_poster
                     else strip_tags(tag.group(1)) if tag else head),
            "kind": "poster" if is_poster else "oral" if head.startswith("Oral") else "spotlight",
            "when": when, "venue": parts[1] if len(parts) > 1 else "", "rooms": rooms,
        })
        rows = re.findall(r'<(?:li|tr) class="paper">(.*?)</(?:li|tr)>', body, re.S)
        for r in rows:
            a = re.search(r'forum\?id=([A-Za-z0-9_-]+)"[^>]*>(.*?)</a>', r, re.S)
            pid, title = a.group(1), strip_tags(a.group(2))
            p = papers.setdefault(pid, {"id": pid, "title": title, "orals": [], "spotlights": []})
            if is_poster:
                num = re.search(r'<td class="num">(\d+)</td>', r)
                p["poster_session"] = head.replace("Poster ", "", 1)
                p["poster_time"] = when
                p["poster_number"] = int(num.group(1)) if num else None
                p.setdefault("_poster_rows", 0)
                p["_poster_rows"] += 1
                for b in re.findall(r'class="badge (oral|spotlight)"[^>]*>(.*?)</a>', r):
                    p.setdefault("_badges", set()).add(b[1])
            else:
                kind = "orals" if head.startswith("Oral") else "spotlights"
                p[kind].append({"session": head, "time": when})
                if p["title"] != title:
                    p.setdefault("_alt_titles", set()).add(title)
    return papers, declared, sessions


def main():
    site, declared, SESSIONS = parse_site()
    out = []
    say = out.append
    say("CoRL 2026 tally  (source: https://www.corl.org/program/accepted-papers)")
    say("=" * 72)
    say(f"Site header says: {declared['total']} accepted papers")
    say(f"Unique OpenReview IDs parsed from site: {len(site)}")
    post = Counter(p.get("poster_session") for p in site.values())
    for k, v in sorted(declared.items()):
        if k == "total":
            continue
        if k.startswith("Poster"):
            got = post.get(k.replace("Poster ", "", 1), 0)
        else:
            got = sum(1 for p in site.values() for s in p["orals"] + p["spotlights"] if s["session"] == k)
        flag = "" if got == v else "   <-- MISMATCH"
        say(f"  {k:<62} declared {v:>4}  parsed {got:>4}{flag}")
    no_poster = [i for i, p in site.items() if not p.get("poster_session")]
    dup_poster = [i for i, p in site.items() if p.get("_poster_rows", 0) > 1]
    n_oral = sum(1 for p in site.values() if p["orals"])
    n_spot = sum(1 for p in site.values() if p["spotlights"])
    say(f"Orals: {n_oral}   Spotlights: {n_spot}   Poster-only: {sum(1 for p in site.values() if not p['orals'] and not p['spotlights'])}")
    say(f"Papers with no poster slot: {len(no_poster)} {no_poster[:5]}")
    say(f"Papers in >1 poster session: {len(dup_poster)} {dup_poster[:5]}")
    badge_bad = [i for i, p in site.items()
                 if p.get("_badges", set()) != {s["session"].split(" ")[0] + " " + s["session"].split(" ")[1]
                                                for s in p["orals"] + p["spotlights"]}]
    say(f"Poster 'also presented as' badges inconsistent with oral/spotlight lists: {len(badge_bad)}")

    # ---------- third-party sources ----------
    ce = {p["id"]: p for p in json.loads((RAW / "corl_explorer_2026.json").read_text())["papers"]}
    enr = json.loads((RAW / "corl_explorer_enrichment.json").read_text())
    gis = {p["id"]: p for p in json.loads((RAW / "gisbi_corl2026_data.json").read_text())["papers"]}
    jay = {p["id"]: p for p in yaml.safe_load((RAW / "jaywu109_papers.yaml").read_text())}
    sources = {"operatic-ai/corl-explorer": ce, "gisbi-kim/conference-explorers": gis, "jaywu109/corl-2026-papers": jay}

    say("")
    say("Agreement of third-party sources with the CoRL site")
    say("-" * 72)
    S = set(site)
    for name, d in sources.items():
        ids = set(d)
        tmis = [i for i in S & ids if norm(d[i]["title"]) != norm(site[i]["title"])]
        say(f"{name}: {len(ids)} papers | missing from source {len(S - ids)} | extra (not on site) {len(ids - S)} | title differs {len(tmis)}")
        for i in sorted(S - ids)[:10]:
            say(f"    missing {i}  {site[i]['title'][:80]}")
        for i in sorted(ids - S)[:10]:
            say(f"    extra   {i}  {d[i]['title'][:80]}")
        for i in tmis[:10]:
            say(f"    title   {i}  site: {site[i]['title'][:70]}")
            say(f"                 src : {d[i]['title'][:70]}")

    # author-list agreement corl-explorer vs gisbi vs jaywu
    def an(lst):
        return [norm(a) for a in (lst or [])]
    dis_ce_g = [i for i in S if an(enr.get(i, {}).get("authors")) != an(gis.get(i, {}).get("authors"))]
    dis_j_g = [i for i in S if an(jay.get(i, {}).get("authors")) != an(gis.get(i, {}).get("authors"))]
    say(f"Author lists differ: corl-explorer vs gisbi {len(dis_ce_g)}; jaywu109 vs gisbi {len(dis_j_g)}")

    # ---------- code / project links ----------
    links = json.loads((RAW / "corl_explorer_paper-code-links.json").read_text())

    def url_key(u):
        return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/").removesuffix(".git")

    def collect(pid, kind):
        urls = []
        ce_l = links.get(pid, {}).get("code" if kind == "code" else "projects") or []
        urls += [x["url"] for x in ce_l if x.get("url")]
        gv = gis.get(pid, {}).get(kind)
        urls += gv if isinstance(gv, list) else [gv] if gv else []
        jv = (jay.get(pid, {}).get("links") or {}).get(kind)
        urls += jv if isinstance(jv, list) else [jv] if jv else []
        seen, outl = set(), []
        for u in urls:
            if u and url_key(u) not in seen:
                seen.add(url_key(u))
                outl.append(u)
        return outl

    # ---------- OpenAlex per-author affiliations ----------
    oa_path = RAW / "openalex" / "by_arxiv.json"
    oa = json.loads(oa_path.read_text()) if oa_path.exists() else {}

    def name_keys(n):
        t = norm(n).split()
        return (" ".join(t), (t[-1], t[0][:1]) if t else None, " ".join(sorted(t)))

    def match_authors(authors, ships):
        """Return per-author OpenAlex authorship (or None), plus how many matched by name."""
        res, by_name = [None] * len(authors), 0
        used = set()
        for k in range(3):  # exact, last+first-initial, token-set
            for ai, a in enumerate(authors):
                if res[ai] is not None:
                    continue
                ak = name_keys(a)[k]
                for si, s in enumerate(ships):
                    if si not in used and name_keys(s["name"])[k] == ak:
                        res[ai], used = s, used | {si}
                        by_name += 1
                        break
        if len(authors) == len(ships):  # positional fallback only when lists line up
            for ai in range(len(authors)):
                if res[ai] is None and ai not in used:
                    res[ai] = ships[ai]
        return res, by_name

    oa_stats = Counter()
    oa_rejects = []

    # ---------- arXiv-document affiliations (work/affil_labels/*.json, from the author-block mapping pass) ----------
    AX_OK = {"explicit", "group", "single"}   # bases that tie a specific author to an institution
    axl = {}
    for f in sorted((WORK / "affil_labels").glob("*.json")) if (WORK / "affil_labels").exists() else []:
        for rec in json.loads(f.read_text()):
            axl[rec["id"]] = {norm(a["name"]): a for a in rec.get("authors", [])}
    ax_stats = Counter()

    # ---------- merge ----------
    merged = []
    for pid, p in site.items():
        e, g, j = enr.get(pid, {}), gis.get(pid, {}), jay.get(pid, {})
        authors = e.get("authors") or g.get("authors") or j.get("authors") or []
        arxiv = e.get("arxivUrl") or (("https://arxiv.org/abs/" + g["arxiv"]) if g.get("arxiv") and not g["arxiv"].startswith("http") else g.get("arxiv")) or ""
        per_author = [{"name": a, "institutions": [], "countries": []} for a in authors]
        oa_ok = False
        m = re.search(r"(\d{4}\.\d{4,5})", arxiv)
        rec = oa.get(m.group(1)) if m else None
        if rec:
            oa_stats["found"] += 1
            tsim = max(SequenceMatcher(None, norm(rec["title"]), norm(t)).ratio()
                       for t in [p["title"], g.get("title") or "", e.get("metadataTitle") or ""] if t)
            matched, by_name = match_authors(authors, rec["authorships"])
            name_frac = by_name / max(1, len(authors))
            if tsim >= 0.6 or name_frac >= 0.5:
                oa_ok = True
                oa_stats["accepted"] += 1
                for pa, s in zip(per_author, matched):
                    if s and s["institutions"]:
                        pa["institutions"], pa["countries"], pa["source"] = s["institutions"], s["countries"], "openalex"
            else:
                oa_rejects.append((pid, round(tsim, 2), round(name_frac, 2), p["title"][:60], (rec["title"] or "")[:60]))
        oa_inst = sorted({i for pa in per_author for i in pa["institutions"]})
        for pa in per_author:   # fill authors OpenAlex left blank from the arXiv author block
            lab = axl.get(pid, {}).get(norm(pa["name"]))
            if pa["institutions"] or not lab:
                continue
            ax_stats["labelled"] += 1
            if lab.get("basis") in AX_OK and lab.get("institutions"):
                pa["institutions"], pa["source"] = lab["institutions"], "arxiv"
                ax_stats["filled"] += 1
            else:
                ax_stats["not_" + str(lab.get("basis"))] += 1
        all_inst = sorted({i for pa in per_author for i in pa["institutions"]})
        if oa_inst:
            oa_stats["with_institutions"] += 1
            if g.get("institutions"):
                oa_stats["both"] += 1
                if {norm(x) for x in oa_inst} & {norm(x) for x in g["institutions"]}:
                    oa_stats["both_overlap"] += 1
        if all_inst:
            inst = all_inst
            inst_src = "+".join(sorted({pa.get("source") for pa in per_author if pa.get("source")}))
        elif g.get("institutions"):
            inst, inst_src = g["institutions"], "gisbi-kim (paper-level)"
        else:
            inst, inst_src = [], ""
        code, project = collect(pid, "code"), collect(pid, "project")
        merged.append({
            "id": pid,
            "title": p["title"],
            "authors": authors,
            "author_affiliations": per_author if all_inst else [],
            "institutions": inst,
            "institutions_source": inst_src,
            "institutions_gisbi": g.get("institutions") or [],
            "countries": sorted({c for pa in per_author for c in pa["countries"]}),
            "affiliation_text": g.get("affiliations") or g.get("affiliation_byline") or "",
            "code": code,
            "github": [u for u in code if "github.com" in u.lower()],
            "project": project,
            "abstract": e.get("abstract") or g.get("abstract") or j.get("abstract") or "",
            "keywords": e.get("keywords") or g.get("keywords") or [],
            "field": j.get("field") or "",
            "presentation": "Oral" if p["orals"] else "Spotlight" if p["spotlights"] else "Poster",
            "oral_session": "; ".join(s["session"] for s in p["orals"]),
            "spotlight_session": "; ".join(s["session"] for s in p["spotlights"]),
            "poster_session": p.get("poster_session", ""),
            "poster_time": p.get("poster_time", ""),
            "poster_number": p.get("poster_number"),
            "openreview": f"https://openreview.net/forum?id={pid}",
            "pdf": f"https://openreview.net/pdf?id={pid}",
            "arxiv": arxiv,
        })
    merged.sort(key=lambda r: (r["poster_session"], r["poster_number"] or 0))

    cov = lambda k: sum(1 for r in merged if r[k])
    say("")
    say("Merged coverage (of %d)" % len(merged))
    say("-" * 72)
    for k in ["authors", "abstract", "keywords", "institutions", "author_affiliations", "institutions_gisbi",
              "countries", "arxiv", "code", "github", "project", "field"]:
        say(f"  {k:<20} {cov(k):>4}  ({100 * cov(k) / len(merged):.0f}%)")
    say(f"  institutions by source: {dict(Counter(r['institutions_source'] or 'none' for r in merged))}")
    na = sum(len(r["authors"]) for r in merged)
    na_aff = sum(1 for r in merged for a in r["author_affiliations"] if a["institutions"])
    say(f"  total authors listed: {na}; authors with an individual affiliation: {na_aff} ({100 * na_aff / na:.0f}%)")
    say("")
    say(f"OpenAlex: {dict(oa_stats)}")
    say(f"arXiv author-block labels: {dict(ax_stats)} (papers labelled: {len(axl)})")
    say("  ('both_overlap' = papers where OpenAlex and gisbi-kim share at least one institution)")
    for r in oa_rejects:
        say(f"  rejected (title sim {r[1]}, names {r[2]}): {r[0]} {r[3]} | OA: {r[4]}")

    (WORK / "tally_report.txt").write_text("\n".join(out) + "\n")
    (ROOT / "corl2026_papers.json").write_text(json.dumps({
        "source": "https://www.corl.org/program/accepted-papers",
        "note": "Paper list and sessions from corl.org. Authors/abstract/keywords from operatic-ai/corl-explorer "
                "(which mirrors OpenReview via gisbi-kim/conference-explorers). author_affiliations are per-author "
                "from OpenAlex (looked up by arXiv ID); when OpenAlex has none, institutions falls back to gisbi-kim's "
                "paper-level set scraped from PDF/arXiv bylines (see institutions_source). Code/project links are the "
                "union of corl-explorer, gisbi-kim and jaywu109/corl-2026-papers.",
        "sessions": SESSIONS,
        "papers": merged}, ensure_ascii=False, indent=1))
    with open(ROOT / "corl2026_papers.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        w.writeheader()
        for r in merged:
            row = dict(r)
            row["author_affiliations"] = "; ".join(
                f"{a['name']} ({' / '.join(a['institutions'])})" if a["institutions"] else a["name"]
                for a in r["author_affiliations"])
            w.writerow({k: "; ".join(v) if isinstance(v, list) else v for k, v in row.items()})
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())
