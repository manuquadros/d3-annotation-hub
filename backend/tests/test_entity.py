"""Integration tests for entity endpoints: /entity/types and /entity/search.

``/entity/types`` returns OWL classes (for the class picker); ``/entity/search``
returns individuals matching a name/synonym query. Runs against a real in-memory
SQLite database. Shared fixtures live in ``conftest.py``.
"""

import pytest
from d3textdb.schema import EntityAnnotation

_EMAIL = "user@entity-test.example"
_PASSWORD = "user-secret"

_CLASS_CURIE = "d3o:Enzyme"
_OTHER_CLASS_CURIE = "d3o:Strain"
_INDIVIDUAL_CURIE = "TEST:xyl"


@pytest.fixture()
def user_auth(make_user):
    return make_user(_EMAIL, _PASSWORD)


@pytest.fixture()
def seeded_entities(db):
    """An ontology with two OWL classes and one named individual."""
    ontology_id = db.store_ontology("Test Ontology", "TEST", "http://test.org/")
    db.load_ontology_entities(
        ontology_id,
        [
            EntityAnnotation(
                entity_id=_CLASS_CURIE,
                preferred_name="Enzyme",
                kind="owl:Class",
                synonyms=[],
                is_class=True,
            ),
            EntityAnnotation(
                entity_id=_OTHER_CLASS_CURIE,
                preferred_name="Strain",
                kind="owl:Class",
                synonyms=[],
                is_class=True,
            ),
            EntityAnnotation(
                entity_id=_INDIVIDUAL_CURIE,
                preferred_name="Xylanase",
                kind="d3o:Enzyme",
                synonyms=[],
            ),
        ],
    )


class TestEntityTypes:
    def test_lists_class_entities(self, user_auth, seeded_entities, client):
        r = client.get("/entity/types", headers=user_auth)
        assert r.status_code == 200
        curies = {e["entity_id"] for e in r.json()}
        assert _CLASS_CURIE in curies
        # Individuals are not classes and must not appear.
        assert _INDIVIDUAL_CURIE not in curies

    def test_filters_by_query(self, user_auth, seeded_entities, client):
        r = client.get("/entity/types?q=Enz", headers=user_auth)
        assert r.status_code == 200
        curies = {e["entity_id"] for e in r.json()}
        assert _CLASS_CURIE in curies
        # A class whose name doesn't match the query is filtered out.
        assert _OTHER_CLASS_CURIE not in curies

    def test_requires_authentication(self, seeded_entities, anon_client):
        r = anon_client.get("/entity/types")
        assert r.status_code == 401


class TestEntitySearch:
    def test_finds_individual_by_name_prefix(
        self, user_auth, seeded_entities, client
    ):
        r = client.get("/entity/search?q=Xyl", headers=user_auth)
        assert r.status_code == 200
        assert _INDIVIDUAL_CURIE in {e["entity_id"] for e in r.json()}

    def test_missing_query_param_is_rejected(self, user_auth, client):
        r = client.get("/entity/search", headers=user_auth)
        assert r.status_code == 422

    @pytest.mark.parametrize("limit", [-1, 0, 201])
    def test_out_of_range_limit_is_rejected(self, user_auth, client, limit):
        # TICKET-20: an unbounded/negative limit must not reach the DB, where
        # SQLite's `LIMIT -1` would return every matching entity.
        r = client.get(f"/entity/search?q=Xyl&limit={limit}", headers=user_auth)
        assert r.status_code == 422

    def test_in_range_limit_is_accepted(
        self, user_auth, seeded_entities, client
    ):
        r = client.get("/entity/search?q=Xyl&limit=200", headers=user_auth)
        assert r.status_code == 200

    def test_requires_authentication(self, seeded_entities, anon_client):
        r = anon_client.get("/entity/search?q=Xyl")
        assert r.status_code == 401
