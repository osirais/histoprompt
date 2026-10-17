#!/usr/bin/env python3
"""Fetch PubMed records once and freeze their abstracts into a local JSONL corpus.

Runtime retrieval never calls PubMed; this script is only for corpus preparation.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def fetch(pmids: list[str]) -> list[dict[str, str]]:
    query = urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
    )
    request = urllib.request.Request(
        f"{EUTILS}?{query}", headers={"User-Agent": "histoprompt-prototype/0.1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        root = ET.fromstring(response.read())
    records: list[dict[str, str]] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = text_content(article.find(".//PMID"))
        title = text_content(article.find(".//ArticleTitle"))
        abstract = " ".join(
            text_content(part) for part in article.findall(".//Abstract/AbstractText")
        ).strip()
        year = text_content(article.find(".//PubDate/Year"))
        if pmid and title and abstract:
            records.append(
                {
                    "source_id": f"PMID:{pmid}",
                    "title": title,
                    "year": year,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "text": abstract,
                }
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pmids", nargs="+", help="PubMed identifiers")
    parser.add_argument("--output", type=Path, default=Path("data/corpus.local.jsonl"))
    args = parser.parse_args()
    records = fetch(args.pmids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()

