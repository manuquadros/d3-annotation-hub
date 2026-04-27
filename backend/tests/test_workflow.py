"""Integration tests for the core annotator workflow.

Exercises the full request path against a real in-memory SQLite database.
``transform_article`` (XML rendering) is replaced with a no-op so the tests
don't depend on well-formed JATS XML fixture data.
"""

import json

import pytest
from fastapi.testclient import TestClient

import ahbackend.api.api as api_module
import ahbackend.db.db as db_impl
from ahbackend.api.api import app
from d3textdb import D3TextDB
from d3textdb.schema import Reference
from d3textdb.schema import User as DbUser

_EMAIL = "alice@test.example"
_PASSWORD = "hunter2-test"
_PMID = 99999999


@pytest.fixture()
def ctx(monkeypatch):
    """Fresh in-memory DB: one annotator, one project, one reference."""
    test_db = D3TextDB()
    monkeypatch.setattr(db_impl, "annodb", test_db)
    monkeypatch.setattr(api_module, "transform_article", lambda x: x or "")

    user_id = test_db.create_user(DbUser(email=_EMAIL), _PASSWORD)
    project_id = test_db.create_project("Test Project", required_annotators=1)
    test_db.add_project_member(project_id, user_id, "annotator")

    ref = Reference(
        pubmed_id=_PMID,
        authors="Doe J",
        title="Test article",
        journal="Test Journal",
        volume="1",
        pages="1-10",
        year=2024,
        abstract="Short abstract.",
    )
    ref_id = test_db.store_reference(ref)
    test_db.add_reference_to_project(project_id, ref_id)

    return TestClient(app), project_id


def _login(client: TestClient) -> dict:
    r = client.post("/token", data={"username": _EMAIL, "password": _PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _fetch_annotation(client: TestClient, auth: dict, project_id: int) -> dict:
    r = client.get(
        f"/reference/?ref_identifier={_PMID}&project_id={project_id}",
        headers=auth,
    )
    assert r.status_code == 200, r.text
    # FastAPI serialises the str return value as a JSON string; unwrap it.
    return json.loads(r.json())


def _save_annotation(
    client: TestClient, auth: dict, annotation: dict
) -> None:
    # store_reference does INSERT … ON CONFLICT(pubmed_id, doi) so the PK must
    # be absent; otherwise SQLite raises a UNIQUE violation on reference_id.
    payload = {**annotation, "reference": {k: v for k, v in annotation["reference"].items() if k != "reference_id"}}
    r = client.post(
        "/save/", json={"json_data": json.dumps(payload)}, headers=auth
    )
    assert r.status_code == 200, r.text


class TestLogin:
    def test_valid_credentials_return_token(self, ctx):
        client, _ = ctx
        r = client.post("/token", data={"username": _EMAIL, "password": _PASSWORD})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_wrong_password_is_rejected(self, ctx):
        client, _ = ctx
        r = client.post("/token", data={"username": _EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_unauthenticated_request_is_rejected(self, ctx):
        client, project_id = ctx
        r = client.get(f"/projects/{project_id}/queue")
        assert r.status_code == 401


class TestAnnotationQueue:
    def test_shows_reference_as_not_completed(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        r = client.get(f"/projects/{project_id}/queue", headers=auth)
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 1
        assert items[0]["ref"] == str(_PMID)
        assert items[0]["completed"] is False

    def test_mark_complete_updates_status(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        r = client.post(
            f"/projects/{project_id}/queue/complete?ref={_PMID}", headers=auth
        )
        assert r.status_code == 204

        r = client.get(f"/projects/{project_id}/queue", headers=auth)
        assert r.json()[0]["completed"] is True

    def test_unmark_complete_reverts_status(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        client.post(
            f"/projects/{project_id}/queue/complete?ref={_PMID}", headers=auth
        )
        r = client.delete(
            f"/projects/{project_id}/queue/complete?ref={_PMID}", headers=auth
        )
        assert r.status_code == 204

        r = client.get(f"/projects/{project_id}/queue", headers=auth)
        assert r.json()[0]["completed"] is False


class TestFetchAndSave:
    def test_fresh_reference_has_no_annotations(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        ann = _fetch_annotation(client, auth, project_id)
        assert ann["reference"]["pubmed_id"] == _PMID
        assert ann["pointers"] == []
        assert ann["relations"] == []
        assert ann["completed"] is False

    def test_saved_pointer_round_trips(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        ann = _fetch_annotation(client, auth, project_id)
        ref_id = ann["reference"]["reference_id"]

        ann["entities"] = [
            {
                "entity_id": "TEST:001",
                "preferred_name": "E. coli",
                "kind": "Bacterium",
                "confirmed": True,
            }
        ]
        ann["pointers"] = [
            {
                "reference_id": ref_id,
                "entity_id": "TEST:001",
                "offset": 10,
                "length": 7,
            }
        ]
        _save_annotation(client, auth, ann)

        fetched = _fetch_annotation(client, auth, project_id)
        assert len(fetched["pointers"]) == 1
        assert fetched["pointers"][0]["entity_id"] == "TEST:001"
        assert fetched["pointers"][0]["offset"] == 10

    def test_saved_relation_round_trips(self, ctx):
        client, project_id = ctx
        auth = _login(client)
        ann = _fetch_annotation(client, auth, project_id)
        ref_id = ann["reference"]["reference_id"]

        ann["entities"] = [
            {
                "entity_id": "TEST:001",
                "preferred_name": "E. coli",
                "kind": "Bacterium",
                "confirmed": True,
            },
            {
                "entity_id": "TEST:002",
                "preferred_name": "Xylanase",
                "kind": "Enzyme",
                "confirmed": True,
            },
        ]
        ann["pointers"] = [
            {"reference_id": ref_id, "entity_id": "TEST:001", "offset": 5, "length": 7},
            {"reference_id": ref_id, "entity_id": "TEST:002", "offset": 20, "length": 8},
        ]
        ann["relations"] = [
            {
                "relation_id": None,
                "predicate": "produces",
                "subject": "TEST:001",
                "object": "TEST:002",
            }
        ]
        _save_annotation(client, auth, ann)

        fetched = _fetch_annotation(client, auth, project_id)
        assert len(fetched["relations"]) == 1
        assert fetched["relations"][0]["predicate"] == "produces"
        assert fetched["relations"][0]["subject"] == "TEST:001"

    def test_second_save_replaces_first(self, ctx):
        """Saving twice with different content keeps only the latest state."""
        client, project_id = ctx
        auth = _login(client)
        ann = _fetch_annotation(client, auth, project_id)
        ref_id = ann["reference"]["reference_id"]

        ann["entities"] = [
            {
                "entity_id": "TEST:001",
                "preferred_name": "E. coli",
                "kind": "Bacterium",
                "confirmed": True,
            }
        ]
        ann["pointers"] = [
            {"reference_id": ref_id, "entity_id": "TEST:001", "offset": 5, "length": 7}
        ]
        _save_annotation(client, auth, ann)

        # Re-fetch, clear the pointer, save again.
        ann2 = _fetch_annotation(client, auth, project_id)
        ann2["pointers"] = []
        ann2["entities"] = []
        _save_annotation(client, auth, ann2)

        fetched = _fetch_annotation(client, auth, project_id)
        assert fetched["pointers"] == []


class TestFullWorkflow:
    def test_annotate_save_complete_golden_path(self, ctx):
        """Login → fetch → annotate → save → mark complete → verify queue."""
        client, project_id = ctx
        auth = _login(client)

        # Fetch empty annotation
        ann = _fetch_annotation(client, auth, project_id)
        ref_id = ann["reference"]["reference_id"]
        assert ann["pointers"] == []

        # Add two entities, two pointers, one relation
        ann["entities"] = [
            {
                "entity_id": "TEST:001",
                "preferred_name": "E. coli",
                "kind": "Bacterium",
                "confirmed": True,
            },
            {
                "entity_id": "TEST:002",
                "preferred_name": "Xylanase",
                "kind": "Enzyme",
                "confirmed": True,
            },
        ]
        ann["pointers"] = [
            {"reference_id": ref_id, "entity_id": "TEST:001", "offset": 5, "length": 7},
            {"reference_id": ref_id, "entity_id": "TEST:002", "offset": 20, "length": 8},
        ]
        ann["relations"] = [
            {
                "relation_id": None,
                "predicate": "produces",
                "subject": "TEST:001",
                "object": "TEST:002",
            }
        ]
        _save_annotation(client, auth, ann)

        # Mark the reference complete
        r = client.post(
            f"/projects/{project_id}/queue/complete?ref={_PMID}", headers=auth
        )
        assert r.status_code == 204

        # Queue shows the item as completed
        r = client.get(f"/projects/{project_id}/queue", headers=auth)
        assert r.json()[0]["completed"] is True

        # Annotations are still intact
        final = _fetch_annotation(client, auth, project_id)
        assert len(final["pointers"]) == 2
        assert len(final["relations"]) == 1
        assert final["relations"][0]["predicate"] == "produces"
