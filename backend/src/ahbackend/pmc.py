"""Fetch article metadata and full text from NCBI PubMed Central."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apiadapters.ncbi import NCBIAdapter, stringify
from d3textdb.schema import Reference

if TYPE_CHECKING:
    from lxml import etree


def _text(root: etree._Element, xpath: str) -> str:
    results = root.xpath(xpath)
    return results[0].strip() if results else ""


def _parse_front(front: etree._Element) -> dict:
    """Extract bibliographic metadata from a JATS <front> element."""
    title = _text(front, "//*[name()='article-title']//text()")

    surnames = front.xpath(
        "//*[name()='contrib' and @contrib-type='author']//*[name()='surname']/text()"
    )
    given_names = front.xpath(
        "//*[name()='contrib' and @contrib-type='author']"
        "//*[name()='given-names']/text()"
    )
    initials = [g.split() for g in given_names]
    authors = ", ".join(
        f"{s} {i[0]}" if i else s
        for s, i in zip(surnames, initials + [[]] * len(surnames))
    )

    journal = _text(front, "//*[name()='journal-title']/text()")
    volume = _text(front, "//*[name()='volume']/text()")
    number = _text(front, "//*[name()='issue']/text()") or None

    fpage = _text(front, "//*[name()='fpage']/text()")
    lpage = _text(front, "//*[name()='lpage']/text()")
    pages = f"{fpage}–{lpage}" if fpage and lpage else fpage

    year_str = _text(
        front,
        "//*[name()='pub-date' and ("
        "@pub-type='ppub' or @pub-type='epub' or @date-type='pub'"
        ")]/*[name()='year']/text()",
    )
    if not year_str:
        year_str = _text(front, "//*[name()='pub-date']/*[name()='year']/text()")
    year = int(year_str) if year_str.isdigit() else 0

    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "volume": volume,
        "number": number,
        "pages": pages,
        "year": year,
    }


def fetch_reference_from_pmc(pubmed_id: int) -> Reference | None:
    """Fetch a full Reference from PubMed Central for the given PubMed ID.

    Returns None if the article has no PMC record.
    Raises httpx.HTTPError on network failure.
    """
    adapter = NCBIAdapter()

    ids = adapter.article_ids(str(pubmed_id))
    pmc_str = ids.get("pmc") or ids.get("PMC")
    if not pmc_str:
        return None

    pmc_num = int(pmc_str.upper().lstrip("PMC"))
    record = adapter.pmc_record(str(pmc_num))

    fronts = record.xpath("//*[name()='front']")
    meta = _parse_front(fronts[0]) if fronts else {}

    abstract_els = record.xpath("//*[name()='abstract']")
    body_els = record.xpath("//*[name()='body']")
    abstract = stringify(abstract_els[0]) if abstract_els else None
    body = stringify(body_els[0]) if body_els else None

    return Reference(
        pubmed_id=pubmed_id,
        pmc_id=pmc_num,
        title=meta.get("title") or "Untitled",
        authors=meta.get("authors") or "",
        journal=meta.get("journal") or "",
        volume=meta.get("volume") or "",
        number=meta.get("number"),
        pages=meta.get("pages") or "",
        year=meta.get("year") or 0,
        abstract=abstract,
        body=body,
    )
