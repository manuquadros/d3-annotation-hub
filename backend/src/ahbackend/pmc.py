"""Fetch article metadata and full text from NCBI PubMed Central."""

from __future__ import annotations

from apiadapters.ncbi import NCBIAdapter
from d3textdb.schema import Reference
from xmlparser import JatsFrontMeta, parse_jats_article


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
    article = parse_jats_article(adapter.pmc_record(str(pmc_num)))
    meta = article.meta or JatsFrontMeta()

    return Reference(
        pubmed_id=pubmed_id,
        pmc_id=pmc_num,
        title=meta.title,
        authors=meta.authors,
        journal=meta.journal,
        volume=meta.volume,
        number=meta.number,
        pages=meta.pages,
        year=meta.year,
        abstract=article.abstract,
        body=article.body,
    )
