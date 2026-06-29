"""Force-refetch references from PubMed Central and update the database.

Run from backend/:
    pdm run python scripts/refetch_pmc.py 36828727 37001221
"""

import argparse
import sys

from ahbackend.db._annodb import annodb
from ahbackend.fetch import fetch_reference_from_ncbi
from d3textdb.schema import Reference
from sqlmodel import Session, select


def refetch(pubmed_id: int) -> str:
    fetched = fetch_reference_from_ncbi(pubmed_id)
    if fetched is None:
        return f"PMID:{pubmed_id}  no PMC record found"

    with Session(annodb.engine) as session:
        existing = session.scalar(
            select(Reference).where(Reference.pubmed_id == pubmed_id)
        )
        if existing is None:
            session.add(fetched)
            session.commit()
            return f"PMID:{pubmed_id}  inserted (was not in database)"

        existing.pmc_id = fetched.pmc_id
        existing.title = fetched.title
        existing.authors = fetched.authors
        existing.journal = fetched.journal
        existing.volume = fetched.volume
        existing.number = fetched.number
        existing.pages = fetched.pages
        existing.year = fetched.year
        existing.abstract = fetched.abstract
        existing.body = fetched.body
        session.add(existing)
        session.commit()
        return (
            f"PMID:{pubmed_id}  updated (reference_id={existing.reference_id})"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Force-refetch references from PubMed Central."
    )
    parser.add_argument("pubmed_ids", nargs="+", metavar="PMID", type=int)
    args = parser.parse_args()

    errors = 0
    for pmid in args.pubmed_ids:
        try:
            print(refetch(pmid))
        except Exception as exc:
            print(f"PMID:{pmid}  ERROR: {exc}", file=sys.stderr)
            errors += 1

    sys.exit(errors)


if __name__ == "__main__":
    main()
