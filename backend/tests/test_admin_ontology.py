"""Integration tests for ontology admin endpoints.

Exercises DELETE /admin/ontologies/{id} against a real in-memory SQLite
database via FastAPI's TestClient, focusing on the protection that prevents
deletion when annotations reference the ontology's entities.
"""

import json
from datetime import UTC, datetime

import pytest
from d3textdb import D3TextDB
from d3textdb.schema import (
    EntityAnnotation,
    Pointer,
    Reference,
    ReferenceAnnotation,
    Relation,
)
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
_NOW = datetime(2025, 1, 1, tzinfo=UTC)


@pytest.fixture()
def ctx(db, client, login):
    """Fresh in-memory DB: one admin (can_manage), one annotator, one reference."""
    # get_current_admin checks can_manage, not is_super_user
    db.create_user(DbUser(email=_ADMIN_EMAIL), _ADMIN_PASSWORD, can_manage=True)
    annotator_id = db.create_user(
        DbUser(email=_ANNOTATOR_EMAIL), _ANNOTATOR_PASSWORD
    )
    project_id = db.create_project(
        "Ontology Test Project", required_annotators=1
    )
    db.add_project_member(project_id, annotator_id, "annotator")
    ref_id = db.store_reference(_REF)
    db.add_reference_to_project(project_id, ref_id)

    admin_auth = login(_ADMIN_EMAIL, _ADMIN_PASSWORD)
    return client, admin_auth, db, project_id, annotator_id, ref_id


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

    def test_non_admin_cannot_delete_ontology(self, ctx, login):
        client, _, test_db, *_ = ctx

        ontology_id = test_db.store_ontology("Other Ontology", "OTHER", "http://other.org/")

        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.delete(f"/admin/ontologies/{ontology_id}", headers=annotator_auth)
        assert r.status_code == 403


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE stream body into a list of (event, data) pairs."""
    events: list[tuple[str, dict]] = []
    event: str | None = None
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: ") and event is not None:
            events.append((event, json.loads(line[len("data: ") :])))
            event = None
    return events


_RDFXML_ONTOLOGY = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
 xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
 xmlns:owl="http://www.w3.org/2002/07/owl#"
 xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#">
  <owl:Class rdf:about="https://example.org/o/Alpha">
    <rdfs:label>Alpha</rdfs:label>
    <oboInOwl:hasExactSynonym>A</oboInOwl:hasExactSynonym>
  </owl:Class>
  <owl:Class rdf:about="https://example.org/o/Beta">
    <rdfs:label xml:lang="fr">Beta-fr</rdfs:label>
    <rdfs:label xml:lang="en">Beta</rdfs:label>
    <rdfs:subClassOf rdf:resource="https://example.org/o/Alpha"/>
  </owl:Class>
  <owl:ObjectProperty rdf:about="https://example.org/o/relatesTo">
    <rdfs:label>relates to</rdfs:label>
    <rdfs:domain rdf:resource="https://example.org/o/Beta"/>
    <rdfs:range rdf:resource="https://example.org/o/Alpha"/>
  </owl:ObjectProperty>
</rdf:RDF>"""


class TestImportStreaming:
    """POST /admin/ontology/import streams parse+load without materializing."""

    def _import(self, client, admin_auth, content: bytes):
        return client.post(
            "/admin/ontology/import",
            headers=admin_auth,
            data={
                "name": "Example",
                "prefix": "ex",
                "base_iri": "https://example.org/o/",
            },
            files={"file": ("onto.owl", content, "application/rdf+xml")},
        )

    def test_rdfxml_import_loads_entities_triples_properties(self, ctx):
        client, admin_auth, test_db, *_ = ctx

        r = self._import(client, admin_auth, _RDFXML_ONTOLOGY)
        assert r.status_code == 200

        events = _parse_sse(r.text)
        assert not any(ev == "error" for ev, _ in events), events
        complete = [data for ev, data in events if ev == "complete"]
        assert len(complete) == 1
        result = complete[0]
        assert result["entities"] == 2
        assert result["triples"] == 1  # Beta subClassOf Alpha
        assert result["properties"] == 1

        entities, total = test_db.get_ontology_entities(
            result["ontology_id"], 50, 0
        )
        assert total == 2
        by_curie = {e.entity_id: e for e in entities}
        assert set(by_curie) == {"ex:Alpha", "ex:Beta"}
        # English label preferred over the French one.
        assert by_curie["ex:Beta"].preferred_name == "Beta"
        assert by_curie["ex:Beta"].kind == "ex:Alpha"

    def test_unparseable_upload_streams_error_not_500(self, ctx):
        client, admin_auth, *_ = ctx

        r = self._import(client, admin_auth, b"<<<not valid rdf or owl>>>")
        assert r.status_code == 200
        events = _parse_sse(r.text)
        assert any(ev == "error" for ev, _ in events), events

    def test_entity_expansion_bomb_upload_is_rejected(self, ctx):
        # Tiny 2-level declaration (~16 chars expanded): harmless, but the
        # import must refuse it before parsing rather than expand it.
        client, admin_auth, *_ = ctx
        bomb = (
            b'<?xml version="1.0"?>\n'
            b"<!DOCTYPE rdf:RDF [\n"
            b'  <!ENTITY a "AAAA">\n'
            b'  <!ENTITY b "&a;&a;">\n'
            b"]>\n"
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
            b' xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
            b' xmlns:owl="http://www.w3.org/2002/07/owl#">\n'
            b'  <owl:Class rdf:about="https://x/1">'
            b"<rdfs:label>&b;</rdfs:label></owl:Class>\n"
            b"</rdf:RDF>"
        )
        r = self._import(client, admin_auth, bomb)
        assert r.status_code == 200
        events = _parse_sse(r.text)
        errors = [data for ev, data in events if ev == "error"]
        assert errors and "bomb" in errors[0]["detail"].lower(), events


class TestPaginationBounds:
    """Paginated list endpoints must reject out-of-range limit/offset.

    Guards TICKET-20: an unbounded/negative ``limit`` reached ``.limit()`` and,
    because SQLite treats ``LIMIT -1`` as "no limit", returned the whole table.
    """

    @pytest.mark.parametrize(
        "query",
        ["limit=-1", "limit=0", "limit=201", "offset=-1"],
    )
    @pytest.mark.parametrize("resource", ["entities", "triples"])
    def test_out_of_range_pagination_is_rejected(self, ctx, resource, query):
        client, admin_auth, test_db, *_ = ctx
        ontology_id = test_db.store_ontology("Page", "PAGE", "http://page/")

        r = client.get(
            f"/admin/ontologies/{ontology_id}/{resource}?{query}",
            headers=admin_auth,
        )
        assert r.status_code == 422

    def test_in_range_pagination_is_accepted(self, ctx):
        client, admin_auth, test_db, *_ = ctx
        ontology_id = test_db.store_ontology("Page", "PAGE", "http://page/")
        test_db.load_ontology_entities(
            ontology_id,
            [
                EntityAnnotation(
                    entity_id="PAGE:1",
                    preferred_name="Thing",
                    kind="d3o:Enzyme",
                    synonyms=[],
                )
            ],
        )

        r = client.get(
            f"/admin/ontologies/{ontology_id}/entities?limit=200&offset=0",
            headers=admin_auth,
        )
        assert r.status_code == 200
        assert r.json()["total"] == 1
