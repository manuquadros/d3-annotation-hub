#!/usr/bin/env python3
"""Initialize a d3textdb SQLite database.

Creates the database with an admin user. Optionally imports references from a
TinyDB document database when tinydb_path is supplied.
"""

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

import tqdm
from d3textdb.d3textdb import D3TextDB
from d3textdb.schema import Reference, User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a d3textdb SQLite database with an admin user. "
            "Pass tinydb_path to also import references from a TinyDB database."
        )
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Path for the output SQLite database.",
    )
    parser.add_argument(
        "tinydb_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to a TinyDB JSON database to import references from (optional).",
    )
    parser.add_argument(
        "--admin-email",
        required=True,
        metavar="EMAIL",
        help="Email address for the initial admin user.",
    )
    parser.add_argument(
        "--admin-password",
        required=True,
        metavar="PASSWORD",
        help="Password for the initial admin user.",
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

    if args.tinydb_path is not None and not args.tinydb_path.exists():
        print(
            f"Error: TinyDB database not found: {args.tinydb_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Creating SQLite database: {args.output_path}")
    db = D3TextDB(path=args.output_path)
    try:
        admin = User(email=args.admin_email, user_id=uuid4())
        db.create_user(admin, password=args.admin_password, is_super_user=True, can_manage=True)
        print(f"Created admin user: {args.admin_email}")

        if args.tinydb_path is not None:
            print(f"Reading TinyDB database: {args.tinydb_path}")
            all_docs = load_documents(args.tinydb_path)
            eligible = [doc for doc in all_docs if is_eligible(doc)]
            print(
                f"Found {len(all_docs)} documents, {len(eligible)} eligible for import."
            )
            for doc in tqdm.tqdm(eligible):
                db.store_reference(to_reference(doc))
            print(f"Done. Imported {len(eligible)} references.")
    finally:
        db.engine.dispose()


if __name__ == "__main__":
    main()
