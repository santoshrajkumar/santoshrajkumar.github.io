# Author → institution mapping from arXiv author blocks

Input: `work/affil_batches/batch_NN.json`, a list of papers. Each has:

- `authors`: the full author list (OpenReview order and spelling);
- `missing_authors`: the authors to label (OpenAlex had no affiliation for them);
- `known`: affiliations already known for the other authors (context only, do not relabel);
- `html_front_matter`: text of the arXiv HTML page from the title to the abstract. `^{...}` marks superscripts; `Affiliation:` lines belong to the author block just before them;
- `pdf_page1`: text of the PDF's first page up to the abstract, plus the bottom of the page (footnotes).

Output: `work/affil_labels/batch_NN.json`, a JSON list with one object per input paper:

```json
{"id": "<paper id>", "authors": [
  {"name": "<exactly as in missing_authors>", "institutions": ["Tsinghua University", "Galbot"], "basis": "explicit"}
]}
```

One entry for **every** name in `missing_authors`, in that order.

## basis (pick one)

- `explicit`: the document ties this author to these institutions: superscript numbers or symbols next to the name that match numbered affiliations, an `Affiliation:` line directly under this author, or an e-mail/footnote that names the institution for this author.
- `group`: the paper lists several authors and then one affiliation block for all of them (common CoRL/IEEE layout: names on a line, institution on the next line), and this author is inside that group.
- `single`: the paper lists exactly one institution and no sign of others, so every author has it.
- `ambiguous`: institutions are listed but you cannot tell which belong to this author (e.g. numbered affiliations with superscripts lost in both HTML and PDF text). Put the candidate institutions in `institutions` anyway.
- `none`: no affiliation information for this author (the author is not found, or the paper has no affiliations).

**Name matching.** OpenReview names can differ from the paper's byline: English nicknames ("Yanpei Shi" on OpenReview is "Lights Shi" in the paper), reversed order, initials, accents or hyphens. Match by position in `authors` when the byline has the same number of authors in the same order; otherwise by surname. If you cannot locate the author in the byline at all, use `none`.

Never guess from the other authors' known affiliations, the author's fame, or e-mail domains you would have to look up. Use only the text given. If HTML and PDF disagree, prefer the PDF's superscripts.

## Institution names

- Return the institution, not the department, lab, city or address: "MARS Lab, Nanyang Technological University" → "Nanyang Technological University"; "Robotics Institute, Carnegie Mellon University, Pittsburgh, PA" → "Carnegie Mellon University"; "Google DeepMind" stays "Google DeepMind".
- Use the common English name: "Tsinghua University", "UC Berkeley" or "University of California, Berkeley" (either is fine), "ETH Zurich", "NVIDIA", "Shanghai AI Laboratory".
- A company or institute that is the affiliation (e.g. "X Square Robot", "Galbot", "TeleAI") is an institution. "Work done during an internship at X" is **not** an affiliation; ignore it. "Equal contribution", "corresponding author" and project URLs are not institutions.
- Multiple institutions per author are fine. Keep each as a separate string.
- Unicode is fine; do not translate names you cannot resolve. If text is garbled, return what you can read confidently and lower the basis to `ambiguous`.
