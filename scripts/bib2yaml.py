"""Convert papers.bib into _data/papers.yml for the website.

The site's build runs this automatically (see .github/workflows/pages.yml),
so you only ever edit papers.bib. To run it by hand:

    pip install pybtex
    python scripts/bib2yaml.py

How entries are grouped on the Publications page:
  @misc                         -> Preprints
  @article, @inproceedings      -> Published
  @phdthesis                    -> Doctoral Dissertation
  category = {miscellaneous}    -> Miscellaneous (overrides the above)

The `keywords` field puts a paper under a section of the Research page
(error-estimation, biomolecular, reduced-order, finite-element,
lattice-boltzmann). Papers are listed newest first; within a year they
keep the order they have in papers.bib.
"""

import codecs
import html
import os
import re
import sys

import latexcodec  # noqa: F401  (installed with pybtex; registers the "ulatex" codec)
import yaml
from pybtex.database import parse_file

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB = os.path.join(ROOT, "papers.bib")
OUT = os.path.join(ROOT, "_data", "papers.yml")


def latex_to_html(text):
    """Turn the small amount of LaTeX used in titles into HTML text."""
    text = re.sub(r"\$_\{?(\w+)\}?\$", r"<sub>\1</sub>", text)  # CO$_2$
    text = text.replace("\\&", "&amp;")
    text = codecs.decode(text, "ulatex")  # accents, -- and ---
    text = text.replace("{", "").replace("}", "")
    # escape anything that isn't one of our own tags or entities
    parts = re.split(r"(</?sub>|&amp;)", text)
    return "".join(p if re.fullmatch(r"</?sub>|&amp;", p) else html.escape(p, quote=False) for p in parts)


def person(p):
    names = p.first_names + p.middle_names + p.prelast_names + p.last_names
    return latex_to_html(" ".join(names))


def field(entry, name):
    value = entry.fields.get(name, "")
    return " ".join(str(value).split())


def category(entry):
    if field(entry, "category").lower() == "miscellaneous":
        return "miscellaneous"
    return {
        "misc": "preprint",
        "unpublished": "preprint",
        "article": "published",
        "inproceedings": "published",
        "incollection": "published",
        "phdthesis": "thesis",
    }.get(entry.type.lower(), "published")


def venue(entry):
    kind = entry.type.lower()
    if kind == "article":
        return latex_to_html(field(entry, "journal"))
    if kind in ("inproceedings", "incollection"):
        text = field(entry, "booktitle")
        if field(entry, "series") == "Proceedings of Machine Learning Research":
            text += ", PMLR"
        return latex_to_html(text)
    if kind == "phdthesis":
        return latex_to_html("Ph.D. thesis, " + field(entry, "school"))
    return ""


def links(entry):
    out = []
    url = field(entry, "url")
    eprint = field(entry, "eprint")
    if entry.type.lower() in ("misc", "unpublished"):
        if eprint:
            out.append({"label": "Preprint", "url": "https://arxiv.org/abs/" + eprint})
        elif url:
            out.append({"label": "Preprint", "url": url})
        return out
    if url:
        out.append({"label": "Text", "url": url})
    if eprint:
        out.append({"label": "Preprint", "url": "https://arxiv.org/abs/" + eprint})
    return out


def main():
    db = parse_file(BIB)
    papers = []
    for order, (key, entry) in enumerate(db.entries.items()):
        year = field(entry, "year")
        papers.append({
            "key": key,
            "category": category(entry),
            "authors": ", ".join(person(p) for p in entry.persons.get("author", [])),
            "title": latex_to_html(field(entry, "title")),
            "venue": venue(entry),
            "year": year,
            "links": links(entry),
            "keywords": [k.strip() for k in field(entry, "keywords").split(",") if k.strip()],
            "_order": order,
        })
    papers.sort(key=lambda p: (-int(p["year"] or 0), p["_order"]))
    for p in papers:
        del p["_order"]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# Generated from papers.bib by scripts/bib2yaml.py. Do not edit; edit papers.bib instead.\n")
        yaml.safe_dump(papers, f, allow_unicode=True, sort_keys=False, width=1000)
    print(f"Wrote {len(papers)} papers to {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
