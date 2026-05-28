"""Integration tests for ontology admin endpoints.

Exercises DELETE /admin/ontologies/{id} against a real in-memory SQLite
database via FastAPI's TestClient, focusing on the protection that prevents
deletion when annotations reference the ontology's entities.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import ahbackend.api.api as api_module
import ahbackend.db.operations as operations_module
import ahbackend.db.queries as queries_module
from ahbackend.api.api import app
from d3textdb import D3TextDB
from d3textdb.schema import EntityAnnotation, Pointer, Reference, ReferenceAnnotation
from d3textdb.schema import Relation
from d3textdb.schema import User as DbUser

_ADMIN_EMAIL = "admin@ontology-test.example"
_ADMIN_PASSWORD = "test-secret"
_ANNOTATOR_EMAIL = "annotator@ontology-test.example"
_ANNOTATOR_PASSWORD = "annotator-secret"

_REF = Reference(
    pubmed_id=11111111,
    authors="Test A",
    title="Test Reference",
    journal="Test J.",
    volume="1",
    pages="1-5",
    year=2024,
    abstract="Abstract.",
)
_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.fixture()
def ctx(monkeypatch):
    """Fresh in-memory DB: one admin (can_manage), one annotator, one reference."""
    test_db = D3TextDB()
    monkeypatch.setattr(queries_module, "annodb", test_db)
    monkeypatch.setattr(operations_module, "annodb", test_db)
    monkeypatch.setattr(api_module, "transform_article", lambda x: x or "")

    # get_current_admin checks can_manage, not is_super_user
    test_db.create_user(DbUser(email=_ADMIN_EMAIL), _ADMIN_PASSWORD, can_manage=True)
    annotator_id = test_db.create_user(DbUser(email=_ANNOTATOR_EMAIL), _ANNOTATOR_PASSWORD)
    project_id = test_db.create_project("Ontology Test Project", required_annotators=1)
    test_db.add_project_member(project_id, annotator_id, "annotator")
    ref_id = test_db.store_reference(_REF)
    test_db.add_reference_to_project(project_id, ref_id)

    client = TestClient(app)
    r = client.post("/token", data={"username": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    admin_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    return client, admin_auth, test_db, project_id, annotator_id, ref_id


def _annotate_with_entity(
    test_db: D3TextDB,
    project_id: int,
    annotator_id,
    ref_id: int,
    entity_curie: str,
) -> None:
    """Store an annotation that creates a Pointer referencing entity_curie."""
    user = DbUser(user_id=annotator_id, email=_ANNOTATOR_EMAIL)
    ref = Reference(**{**_REF.model_dump(), "reference_id": ref_id})
    annotation = ReferenceAnnotation(
        user=user,
        reference=ref,
        pointers=[Pointer(entity_id=entity_curie, reference_id=None, offset=0, length=5)],
        relations=[],
        completed=False,
        last_updated=_NOW,
        project_id=project_id,
    )
    test_db.store_annotation(annotation)


class TestDeleteOntology:
    def test_deletes_ontology_with_no_annotations(self, ctx):
        client, admin_auth, test_db, *_ = ctx

        ontology_id = test_db.store_ontology("Empty Ontology", "EMPTY", "http://empty.org/")
        test_db.load_ontology_entities(
            ontology_id,
            [EntityAnnotation(entity_id="EMPTY:1", preferred_name="Thing", kind="d3o:Enzyme", synonyms=[])],
        )

        r = client.delete(f"/admin/ontologies/{ontology_id}", headers=admin_auth)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_delete_blocked_when_pointer_references_entity(self, ctx):
        client, admin_auth, test_db, project_id, annotator_id, ref_id = ctx

        ontology_id = test_db.store_ontology("Used Ontology", "USED", "http://used.org/")
        test_db.load_ontology_entities(
            ontology_id,
            [EntityAnnotation(entity_id="USED:1", preferred_name="Alpha", kind="d3o:Enzyme", synonyms=[])],
        )
        _annotate_with_entity(test_db, project_id, annotator_id, ref_id, "USED:1")

        r = client.delete(f"/admin/ontologies/{ontology_id}", headers=admin_auth)
        assert r.status_code == 409
        assert "annotation" in r.json()["detail"].lower()

    def test_delete_blocked_when_relation_references_entity(self, ctx):
        client, admin_auth, test_db, project_id, annotator_id, ref_id = ctx

        ontology_id = test_db.store_ontology("Rel Ontology", "RLONT", "http://rlont.org/")
        test_db.load_ontology_entities(
            ontology_id,
            [
                EntityAnnotation(entity_id="RLONT:1", preferred_name="Subject", kind="d3o:Enzyme", synonyms=[]),
                EntityAnnotation(entity_id="RLONT:2", preferred_name="Object", kind="d3o:Strain", synonyms=[]),
            ],
        )

        user = DbUser(user_id=annotator_id, email=_ANNOTATOR_EMAIL)
        ref = Reference(**{**_REF.model_dump(), "reference_id": ref_id})
        annotation = ReferenceAnnotation(
            user=user,
            reference=ref,
            pointers=[
                Pointer(entity_id="RLONT:1", reference_id=None, offset=0, length=3),
                Pointer(entity_id="RLONT:2", reference_id=None, offset=10, length=3),
            ],
            relations=[Relation(predicate="d3o:HasEnzyme", subject="RLONT:1", object="RLONT:2")],
            completed=False,
            last_updated=_NOW,
            project_id=project_id,
        )
        test_db.store_annotation(annotation)

        r = client.delete(f"/admin/ontologies/{ontology_id}", headers=admin_auth)
        assert r.status_code == 409
        assert "annotation" in r.json()["detail"].lower()

    def test_ontology_still_exists_after_blocked_delete(self, ctx):
        client, admin_auth, test_db, project_id, annotator_id, ref_id = ctx

        ontology_id = test_db.store_ontology("Persist Ontology", "PERS", "http://pers.org/")
        test_db.load_ontology_entities(
            ontology_id,
            [EntityAnnotation(entity_id="PERS:1", preferred_name="Beta", kind="d3o:Strain", synonyms=[])],
        )
        _annotate_with_entity(test_db, project_id, annotator_id, ref_id, "PERS:1")

        client.delete(f"/admin/ontologies/{ontology_id}", headers=admin_auth)

        r = client.get("/admin/ontologies", headers=admin_auth)
        assert r.status_code == 200
        ids = [o["ontology_id"] for o in r.json()]
        assert ontology_id in ids

    def test_non_admin_cannot_delete_ontology(self, ctx):
        client, _, test_db, *_ = ctx

        ontology_id = test_db.store_ontology("Other Ontology", "OTHER", "http://other.org/")

        r = client.post("/token", data={"username": _ANNOTATOR_EMAIL, "password": _ANNOTATOR_PASSWORD})
        annotator_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.delete(f"/admin/ontologies/{ontology_id}", headers=annotator_auth)
        assert r.status_code == 403
