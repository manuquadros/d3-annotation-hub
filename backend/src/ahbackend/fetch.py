"""Fetch article metadata and full text from NCBI."""

from __future__ import annotations

from apiadapters.ncbi import NCBIAdapter
from d3textdb.schema import Reference
from xmlparser import ArticleMeta, parse_jats_article, parse_pubmed_article


def fetch_reference_from_ncbi(pubmed_id: int) -> Reference | None:
    """Fetch a full Reference from PubMed Central for the given PubMed ID.

    Returns None if the article has no PMC record.
    Raises httpx.HTTPError on network failure.
    """
    adapter = NCBIAdapter()

    ids = adapter.article_ids(str(pubmed_id))
    pmc_str = ids.get("pmc") or ids.get("PMC")

    if pmc_str:
        pmc_str = pmc_str.upper().lstrip("PMC")
        record = parse_jats_article(adapter.pmc_record(pmc_str))
    else:
        record = parse_pubmed_article(adapter.pubmed_record(str(pubmed_id)))

    meta = record.meta or ArticleMeta()

    return Reference(
        pubmed_id=pubmed_id,
        pmc_id=int(pmc_str) if pmc_str else None,
        title=meta.title,
        authors=meta.authors,
        journal=meta.journal,
        volume=meta.volume,
        number=meta.number,
        pages=meta.pages,
        year=meta.year,
        abstract=record.abstract,
        body=record.body,
    )
