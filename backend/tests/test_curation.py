"""Integration tests for the curation pipeline.

Covers the curator-facing flow against a real in-memory SQLite database:
queue → claims → verdict → annotator snapshots → save curated annotation.

A reference becomes curation-ready once enough annotators have completed it
(``required_annotators``); completing an annotation snapshots the annotator's
saved state, which is what the curation views read. Shared ``db``/``client``/
``login`` fixtures live in ``conftest.py``.
"""

import pytest
from d3textdb.schema import Entity, Pointer, Reference, Relation
from d3textdb.schema import User as DbUser
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from ahbackend.api.api import PointerOut, RelationOut

_PMID = 30000001
_ANNOTATOR_EMAIL = "annotator@curation-test.example"
_ANNOTATOR_PASSWORD = "annot-secret"
_CURATOR_EMAIL = "curator@curation-test.example"
_CURATOR_PASSWORD = "curate-secret"

_SUBJECT = "TEST:bacterium"
_OBJECT = "TEST:enzyme"
_PREDICATE = "produces"

_DEFAULT_POINTERS = [
    {"entity_id": _SUBJECT, "offset": 5, "length": 7},
    {"entity_id": _OBJECT, "offset": 20, "length": 8},
]

# Every field distinct from every other, so a response built by copying the
# wrong attribute across cannot still match.
_RICH_POINTERS = [
    {
        "entity_id": _SUBJECT,
        "offset": 11,
        "length": 7,
        "field": "abstract",
        "exact_text": "E. coli",
        "prefix_text": "grown by ",
        "suffix_text": " in broth",
    },
    {
        "entity_id": _OBJECT,
        "offset": 40,
        "length": 8,
        "field": "body",
        "exact_text": "xylanase",
        "prefix_text": "secretes ",
        "suffix_text": " into the",
    },
]


@pytest.fixture()
def project(db, make_project):
    """Project (required_annotators=1): one annotator, one curator, one ref."""
    annotator_id = db.create_user(
        DbUser(email=_ANNOTATOR_EMAIL), _ANNOTATOR_PASSWORD
    )
    curator_id = db.create_user(DbUser(email=_CURATOR_EMAIL), _CURATOR_PASSWORD)
    project_id = make_project("Curation Project", required_annotators=1)
    db.add_project_member(project_id, annotator_id, "annotator")
    db.add_project_member(project_id, curator_id, "curator")

    ref = Reference(
        pubmed_id=_PMID,
        authors="Doe J",
        title="Curation article",
        journal="Test Journal",
        volume="1",
        pages="1-10",
        year=2024,
        abstract="Short abstract.",
    )
    ref_id = db.store_reference(ref)
    db.add_reference_to_project(project_id, ref_id)
    return project_id, ref_id


def _seed_completed_annotation(
    client: TestClient,
    auth: dict,
    project_id: int,
    pointers: list[dict] | None = None,
) -> int:
    """Annotator saves an annotation with one relation and marks it complete.

    ``pointers`` are merged with the reference id and default to
    ``_DEFAULT_POINTERS``. Returns the reference_id. After this, the reference
    is curation-ready.
    """
    r = client.get(
        f"/reference/?ref_identifier={_PMID}&project_id={project_id}",
        headers=auth,
    )
    assert r.status_code == 200, r.text
    ann = r.json()
    ref_id = ann["reference"]["reference_id"]

    ann["entities"] = [
        {
            "entity_id": _SUBJECT,
            "preferred_name": "E. coli",
            "kind": "Bacterium",
            "confirmed": True,
        },
        {
            "entity_id": _OBJECT,
            "preferred_name": "Xylanase",
            "kind": "Enzyme",
            "confirmed": True,
        },
    ]
    ann["pointers"] = [
        {"reference_id": ref_id, **p}
        for p in (pointers if pointers is not None else _DEFAULT_POINTERS)
    ]
    ann["relations"] = [
        {
            "relation_id": None,
            "predicate": _PREDICATE,
            "subject": _SUBJECT,
            "object": _OBJECT,
        }
    ]
    # store_reference upserts on (pubmed_id, doi), so the PK must be absent.
    payload = {
        **ann,
        "reference": {
            k: v for k, v in ann["reference"].items() if k != "reference_id"
        },
    }
    r = client.post("/save/", json=payload, headers=auth)
    assert r.status_code == 200, r.text

    r = client.post(
        f"/projects/{project_id}/queue/complete?ref={_PMID}", headers=auth
    )
    assert r.status_code == 204, r.text
    return ref_id


@pytest.fixture()
def seeded(project, client, login):
    """A curation-ready project: the annotator has completed one annotation.

    Returns (client, curator_auth, project_id, reference_id).
    """
    project_id, ref_id = project
    annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
    _seed_completed_annotation(client, annotator_auth, project_id)
    curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
    return client, curator_auth, project_id, ref_id


@pytest.fixture()
def seeded_rich(project, client, login):
    """Like ``seeded``, but with every pointer field filled in distinctly.

    The default seed leaves ``field`` and the three TextQuoteSelector strings
    at their defaults, so a response that dropped or transposed one of them
    would still compare equal.
    """
    project_id, ref_id = project
    annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
    _seed_completed_annotation(
        client, annotator_auth, project_id, pointers=_RICH_POINTERS
    )
    curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
    return client, curator_auth, project_id, ref_id


def _stored_pointers(db) -> dict[str, dict]:
    """Stored pointers by CURIE, projected onto the ``PointerOut`` fields."""
    with Session(db.engine) as session:
        return {
            row.entity_id: {
                name: getattr(row, name) for name in PointerOut.model_fields
            }
            for row in session.exec(select(Pointer)).all()
        }


def _stored_relations(db) -> dict[str, dict]:
    """Stored relations by predicate, projected onto ``RelationOut``."""
    with Session(db.engine) as session:
        return {
            row.predicate: {
                name: getattr(row, name) for name in RelationOut.model_fields
            }
            for row in session.exec(select(Relation)).all()
        }


class TestCurationQueue:
    def test_completed_reference_appears_in_queue(self, seeded):
        client, curator_auth, project_id, _ = seeded
        r = client.get(
            f"/projects/{project_id}/curation/queue", headers=curator_auth
        )
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["pubmed_id"] == _PMID

    def test_queue_empty_before_any_completion(self, project, client, login):
        project_id, _ = project
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
        r = client.get(
            f"/projects/{project_id}/curation/queue", headers=curator_auth
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_annotator_cannot_access_queue(self, project, client, login):
        project_id, _ = project
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.get(
            f"/projects/{project_id}/curation/queue", headers=annotator_auth
        )
        assert r.status_code == 403

    def test_unauthenticated_queue_request_is_rejected(
        self, project, anon_client
    ):
        project_id, _ = project
        r = anon_client.get(f"/projects/{project_id}/curation/queue")
        assert r.status_code == 401


class TestCurationClaims:
    def test_lists_the_saved_relation_as_a_claim(self, seeded):
        client, curator_auth, project_id, _ = seeded
        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["claims"]) == 1
        claim = body["claims"][0]
        assert claim["subject"] == _SUBJECT
        assert claim["predicate"] == _PREDICATE
        assert claim["object"] == _OBJECT

    def test_claim_has_no_verdict_initially(self, seeded):
        client, curator_auth, project_id, _ = seeded
        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        assert r.json()["claims"][0]["verdict"] is None

    def test_claim_evidence_carries_subject_and_object_pointers(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        evidence = r.json()["claims"][0]["evidence"]
        assert len(evidence) == 1
        assert evidence[0]["reference_id"] == ref_id
        assert evidence[0]["subject_pointers"] == [{"offset": 5, "length": 7}]
        assert evidence[0]["object_pointers"] == [{"offset": 20, "length": 8}]

    def test_entities_map_includes_claim_curies(self, seeded):
        client, curator_auth, project_id, _ = seeded
        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        entities = r.json()["entities"]
        assert entities[_SUBJECT]["preferred_name"] == "E. coli"
        assert entities[_OBJECT]["preferred_name"] == "Xylanase"

    def test_annotator_cannot_access_claims(self, project, client, login):
        project_id, _ = project
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=annotator_auth
        )
        assert r.status_code == 403


def _relation_id(client: TestClient, auth: dict, project_id: int) -> int:
    r = client.get(f"/projects/{project_id}/curation/claims", headers=auth)
    return r.json()["claims"][0]["relation_id"]


class TestSetVerdict:
    def test_recorded_verdict_appears_on_the_claim(self, seeded):
        client, curator_auth, project_id, _ = seeded
        relation_id = _relation_id(client, curator_auth, project_id)

        r = client.post(
            f"/projects/{project_id}/curation/claims/{relation_id}/verdict",
            json={"verdict": "accepted"},
            headers=curator_auth,
        )
        assert r.status_code == 204

        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        assert r.json()["claims"][0]["verdict"] == "accepted"

    def test_verdict_can_be_changed(self, seeded):
        client, curator_auth, project_id, _ = seeded
        relation_id = _relation_id(client, curator_auth, project_id)
        url = f"/projects/{project_id}/curation/claims/{relation_id}/verdict"

        client.post(url, json={"verdict": "accepted"}, headers=curator_auth)
        r = client.post(url, json={"verdict": "rejected"}, headers=curator_auth)
        assert r.status_code == 204

        r = client.get(
            f"/projects/{project_id}/curation/claims", headers=curator_auth
        )
        assert r.json()["claims"][0]["verdict"] == "rejected"

    def test_invalid_verdict_value_is_rejected(self, seeded):
        client, curator_auth, project_id, _ = seeded
        relation_id = _relation_id(client, curator_auth, project_id)
        r = client.post(
            f"/projects/{project_id}/curation/claims/{relation_id}/verdict",
            json={"verdict": "maybe"},
            headers=curator_auth,
        )
        assert r.status_code == 422

    def test_annotator_cannot_set_verdict(self, seeded, login):
        # Resolve a real relation so the 403 can't be masked by a bad id.
        client, curator_auth, project_id, _ = seeded
        relation_id = _relation_id(client, curator_auth, project_id)
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.post(
            f"/projects/{project_id}/curation/claims/{relation_id}/verdict",
            json={"verdict": "accepted"},
            headers=annotator_auth,
        )
        assert r.status_code == 403


class TestAnnotatorSnapshots:
    def test_returns_the_annotator_pointers_and_relation(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["snapshots"]) == 1
        snap = body["snapshots"][0]
        assert snap["email"] == _ANNOTATOR_EMAIL
        assert len(snap["pointers"]) == 2
        assert len(snap["relations"]) == 1
        assert snap["relations"][0]["predicate"] == _PREDICATE

    def test_includes_reference_and_entity_metadata(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        body = r.json()
        assert body["reference"]["title"] == "Curation article"
        assert body["entities"][_SUBJECT]["kind"] == "Bacterium"

    def test_curated_annotation_is_empty_before_save(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        body = r.json()
        assert body["curated_pointers"] == []
        assert body["curated_relations"] == []

    def test_unknown_reference_returns_404(self, seeded):
        client, curator_auth, project_id, _ = seeded
        r = client.get(
            f"/projects/{project_id}/curation/99999/snapshots",
            headers=curator_auth,
        )
        assert r.status_code == 404

    def test_annotator_cannot_access_snapshots(self, seeded, login):
        client, _, project_id, ref_id = seeded
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=annotator_auth,
        )
        assert r.status_code == 403


class TestSaveCuratedAnnotation:
    def _curated_payload(self, ref_id: int) -> dict:
        # Pointer must match one the annotator created, or it is dropped.
        return {
            "pointers": [
                {
                    "reference_id": ref_id,
                    "entity_id": _SUBJECT,
                    "offset": 5,
                    "length": 7,
                }
            ],
            "relations": [
                {
                    "relation_id": None,
                    "predicate": _PREDICATE,
                    "subject": _SUBJECT,
                    "object": _OBJECT,
                }
            ],
        }

    def test_saved_curation_round_trips_in_snapshots(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        r = client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json=self._curated_payload(ref_id),
            headers=curator_auth,
        )
        assert r.status_code == 204

        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        body = r.json()
        assert len(body["curated_pointers"]) == 1
        assert body["curated_pointers"][0]["entity_id"] == _SUBJECT
        assert len(body["curated_relations"]) == 1
        assert body["curated_relations"][0]["predicate"] == _PREDICATE

    def test_second_save_replaces_the_first(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json=self._curated_payload(ref_id),
            headers=curator_auth,
        )
        # Save again with no pointers and no relations.
        r = client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json={"pointers": [], "relations": []},
            headers=curator_auth,
        )
        assert r.status_code == 204

        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        body = r.json()
        assert body["curated_pointers"] == []
        assert body["curated_relations"] == []

    def test_pointer_not_in_db_is_dropped(self, seeded):
        client, curator_auth, project_id, ref_id = seeded
        payload = {
            "pointers": [
                {
                    "reference_id": ref_id,
                    "entity_id": _SUBJECT,
                    "offset": 999,
                    "length": 3,
                }
            ],
            "relations": [],
        }
        r = client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json=payload,
            headers=curator_auth,
        )
        assert r.status_code == 204

        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        assert r.json()["curated_pointers"] == []

    def test_annotator_cannot_save_curated(self, seeded, login):
        client, _, project_id, ref_id = seeded
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json=self._curated_payload(ref_id),
            headers=annotator_auth,
        )
        assert r.status_code == 403


class TestSnapshotResponseFieldMapping:
    """Pointers and relations reach the client with every stored field.

    The assertions are driven off ``model_fields``, so a field added to
    ``PointerOut`` or ``RelationOut`` is covered here without editing them.
    """

    def _snapshots(self, seeded_rich) -> dict:
        client, curator_auth, project_id, ref_id = seeded_rich
        r = client.get(
            f"/projects/{project_id}/curation/{ref_id}/snapshots",
            headers=curator_auth,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def _save_curated(self, seeded_rich) -> None:
        client, curator_auth, project_id, ref_id = seeded_rich
        r = client.post(
            f"/projects/{project_id}/curation/{ref_id}",
            json={
                "pointers": [
                    {"reference_id": ref_id, **p} for p in _RICH_POINTERS
                ],
                "relations": [
                    {
                        "relation_id": None,
                        "predicate": _PREDICATE,
                        "subject": _SUBJECT,
                        "object": _OBJECT,
                    }
                ],
            },
            headers=curator_auth,
        )
        assert r.status_code == 204, r.text

    def test_snapshot_pointers_match_the_stored_rows(self, db, seeded_rich):
        stored = _stored_pointers(db)
        returned = self._snapshots(seeded_rich)["snapshots"][0]["pointers"]
        assert len(returned) == len(_RICH_POINTERS)
        for pointer in returned:
            assert pointer == stored[pointer["entity_id"]]

    def test_snapshot_relations_match_the_stored_rows(self, db, seeded_rich):
        stored = _stored_relations(db)
        returned = self._snapshots(seeded_rich)["snapshots"][0]["relations"]
        assert len(returned) == 1
        assert returned[0] == stored[_PREDICATE]

    def test_curated_pointers_match_the_stored_rows(self, db, seeded_rich):
        self._save_curated(seeded_rich)
        stored = _stored_pointers(db)
        returned = self._snapshots(seeded_rich)["curated_pointers"]
        assert len(returned) == len(_RICH_POINTERS)
        for pointer in returned:
            assert pointer == stored[pointer["entity_id"]]

    def test_curated_relations_match_the_stored_rows(self, db, seeded_rich):
        self._save_curated(seeded_rich)
        stored = _stored_relations(db)
        returned = self._snapshots(seeded_rich)["curated_relations"]
        assert len(returned) == 1
        assert returned[0] == stored[_PREDICATE]


_OLD_CURIE = "PROP:0001"
_NEW_CURIE = "CHEBI:12345"


class TestRenameEntityCurie:
    """PATCH /projects/{id}/curation/entity-curie — confirm a proposed CURIE."""

    def test_curator_renames_a_proposed_entity(
        self, project, db, client, login
    ):
        project_id, _ = project
        db.store_proposed_entity(
            project_id, "Beta strain", _OLD_CURIE, "Strain"
        )
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)

        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 204

        assert db.get_entities_by_curies([_OLD_CURIE]) == []
        renamed = db.get_entities_by_curies([_NEW_CURIE])
        assert len(renamed) == 1
        assert renamed[0].entity_id == _NEW_CURIE
        assert renamed[0].confirmed is False

    def test_annotator_cannot_rename_curie(self, project, client, login):
        project_id, _ = project
        annotator_auth = login(_ANNOTATOR_EMAIL, _ANNOTATOR_PASSWORD)
        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=annotator_auth,
        )
        assert r.status_code == 403

    def test_unauthenticated_rename_is_rejected(self, project, anon_client):
        project_id, _ = project
        r = anon_client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
        )
        assert r.status_code == 401

    def test_cannot_rename_a_confirmed_entity(self, project, db, client, login):
        project_id, _ = project
        db.store_proposed_entity(
            project_id, "Beta strain", _OLD_CURIE, "Strain"
        )
        db.confirm_entity(_OLD_CURIE)
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)

        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 409
        # The CURIE is unchanged.
        assert (
            db.get_entities_by_curies([_OLD_CURIE])[0].entity_id == _OLD_CURIE
        )

    def test_renaming_unknown_entity_returns_404(self, project, client, login):
        project_id, _ = project
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie=NOPE:9999",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 404

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_empty_new_curie_is_rejected(
        self, project, db, client, login, blank
    ):
        project_id, _ = project
        db.store_proposed_entity(
            project_id, "Beta strain", _OLD_CURIE, "Strain"
        )
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)

        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": blank},
            headers=curator_auth,
        )
        assert r.status_code == 422
        # The entity was not renamed to an empty CURIE.
        assert (
            db.get_entities_by_curies([_OLD_CURIE])[0].entity_id == _OLD_CURIE
        )

    def test_cannot_rename_another_projects_proposed_entity(
        self, project, db, client, login, make_project
    ):
        # A curator of project A must not be able to rename a proposed entity
        # that belongs to project B (the lookup/rename are global by CURIE).
        project_a, _ = project
        project_b = make_project("Other Project", required_annotators=1)
        db.store_proposed_entity(project_b, "Beta strain", _OLD_CURIE, "Strain")
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)

        r = client.patch(
            f"/projects/{project_a}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 404
        # Project B's entity is untouched.
        assert (
            db.get_entities_by_curies([_OLD_CURIE])[0].entity_id == _OLD_CURIE
        )
        assert db.get_entities_by_curies([_NEW_CURIE]) == []

    def test_rename_to_existing_curie_returns_409(
        self, project, db, client, login
    ):
        project_id, _ = project
        db.store_proposed_entity(
            project_id, "Beta strain", _OLD_CURIE, "Strain"
        )
        db.store_proposed_entity(
            project_id, "Gamma strain", _NEW_CURIE, "Strain"
        )
        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)

        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 409
        # Both entities remain intact.
        assert (
            db.get_entities_by_curies([_OLD_CURIE])[0].entity_id == _OLD_CURIE
        )
        assert (
            db.get_entities_by_curies([_NEW_CURIE])[0].entity_id == _NEW_CURIE
        )

    def test_rename_backfills_legacy_null_project_entity(
        self, project, db, client, login
    ):
        # A proposed entity predating the project_id column carries a NULL
        # project_id. Renaming it adopts it into the current project (backfill)
        # rather than 404ing it into being permanently un-renamable.
        project_id, _ = project
        db.store_proposed_entity(
            project_id, "Beta strain", _OLD_CURIE, "Strain"
        )
        with Session(db.engine) as session:
            row = session.exec(
                select(Entity).where(Entity.curie == _OLD_CURIE)
            ).one()
            row.project_id = None
            session.add(row)
            session.commit()

        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
        r = client.patch(
            f"/projects/{project_id}/curation/entity-curie?curie={_OLD_CURIE}",
            json={"new_curie": _NEW_CURIE},
            headers=curator_auth,
        )
        assert r.status_code == 204
        renamed = db.get_entities_by_curies([_NEW_CURIE])
        assert len(renamed) == 1
        assert renamed[0].entity_id == _NEW_CURIE
        assert db.get_entity_project_id(_NEW_CURIE) == project_id
