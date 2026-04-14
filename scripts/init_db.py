#!/usr/bin/env python3
"""Initialize a d3textdb SQLite database from a TinyDB document database.

Reads the 'documents' table from a TinyDB JSON database and imports references
that have bacteria entries but no strain entries into the SQLite database.
"""

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

import tqdm
from d3textdb.d3textdb import D3TextDB
from d3textdb.schema import Reference, User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a d3textdb SQLite database and populate it with "
            "references from a TinyDB document database."
        )
    )
    parser.add_argument(
        "tinydb_path",
        type=Path,
        help="Path to the TinyDB JSON database.",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Path for the output SQLite database.",
    )
    return parser.parse_args()


def load_documents(tinydb_path: Path) -> list[dict]:
    """Load records from the 'documents' table of a TinyDB JSON database."""
    data = json.loads(tinydb_path.read_text())
    table = data.get("documents", {})
    return list(table.values())


def is_eligible(doc: dict) -> bool:
    """Return True if the document has bacteria entries but no strain entries."""
    fulltext = bool(doc.get("fulltext", ""))
    bacteria = doc.get("bacteria", {})
    strains = doc.get("strains", [])
    return fulltext and bool(bacteria) and not strains


def to_reference(doc: dict) -> Reference:
    return Reference(
        pubmed_id=int(pubmed_id)
        if (pubmed_id := doc.get("pubmed_id"))
        else None,
        pmc_id=int(pmc_id) if (pmc_id := doc.get("pmc_id")) else None,
        pmc_open=doc.get("pmc_open"),
        doi=doc.get("doi"),
        authors=doc["authors"],
        title=doc["title"],
        journal=doc["journal"],
        volume=str(doc["volume"]),
        pages=doc["pages"],
        year=int(doc["year"]),
        abstract=doc.get("abstract"),
        body=doc.get("fulltext"),
    )


def main() -> None:
    args = parse_args()

    if not args.tinydb_path.exists():
        print(
            f"Error: TinyDB database not found: {args.tinydb_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Reading TinyDB database: {args.tinydb_path}")
    all_docs = load_documents(args.tinydb_path)
    eligible = [doc for doc in all_docs if is_eligible(doc)]
    print(
        f"Found {len(all_docs)} documents, {len(eligible)} eligible for import."
    )

    print(f"Creating SQLite database: {args.output_path}")
    db = D3TextDB(path=args.output_path)
    test_user = User(
        email="test@dsmz.de",
        user_id=UUID("f47f7e7b-3913-457e-911c-6da6275de3ec"),
    )
    db.create_user(test_user, password="test")
    admin = User(email="admin@dsmz.de", user_id=uuid4())
    db.create_user(admin, password="admin", role="super_user")
    manager1 = User(email="manager@dsmz.de", user_id=uuid4())
    db.create_user(manager1, password="manager", role="project_manager")
    try:
        for doc in tqdm.tqdm(eligible):
            db.store_reference(to_reference(doc))
        print(f"Done. Imported {len(eligible)} references.")
    finally:
        db.engine.dispose()


if __name__ == "__main__":
    main()
