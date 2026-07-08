#!/usr/bin/env python3
import itertools
import json
from pathlib import Path
from uuid import UUID

from d3textdb.d3textdb import D3TextDB
from d3textdb.schema import Entity, Pointer, Reference, Relation, User


def main() -> None:
    # Load test JSON data
    json_path = Path("tests/15117974_test.json")
    data = json.loads(json_path.read_text())

    db = D3TextDB(path=Path("test.db"), echo=True)
    try:
        test_user = User(
            email="test@dsmz.de",
            user_id=UUID("f47f7e7b-3913-457e-911c-6da6275de3ec"),
        )
        entities = []

        user_id = (
            db.create_user(test_user, password="test") or test_user.user_id
        )
        for ent in data["entities"]:
            entities.append(Entity.model_validate(ent))

        db.store_items(itertools.chain([test_user], entities))

        for ref in data["references"].values():
            ref_id: int = db.store_reference(Reference.model_validate(ref))
            pointers = (
                Pointer.model_validate(
                    pointer
                    | {
                        "user_id": user_id,
                        "reference_id": ref_id,
                    }
                )
                for pointer in ref["pointers"]
            )
            db.store_items(pointers)

            for predicate, rels in ref["relations"].items():
                db.store_relations(
                    user=user_id,
                    reference=ref_id,
                    relations=[
                        Relation.model_validate(rel | {"predicate": predicate})
                        for rel in rels
                    ],
                )
    finally:
        # Properly close database connections even if an error occurs
        db.engine.dispose()


if __name__ == "__main__":
    main()
