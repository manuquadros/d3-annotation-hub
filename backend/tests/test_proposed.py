"""Integration tests for proposed-entity and proposed-property endpoints.

Annotators (any authenticated user) propose entities/properties for a project;
admins (``can_manage``) list, confirm, delete, and rename them. Runs against a
real in-memory SQLite database. Shared ``db``/``client``/``login`` fixtures live
in ``conftest.py``.
"""

import pytest
from d3textdb.schema import User as DbUser
from fastapi.testclient import TestClient

from ahbackend.api.api import app

_ADMIN_EMAIL = "admin@proposed-test.example"
_ADMIN_PASSWORD = "admin-secret"
_USER_EMAIL = "user@proposed-test.example"
_USER_PASSWORD = "user-secret"

_LABEL = "Novel Bacterium"
_CURIE = "PROP:ENT1"
_KIND = "Bacterium"
_PROP_LABEL = "degrades"
_PROP_CURIE = "PROP:REL1"


@pytest.fixture()
def admin(db, client, login):
    """A user with the can_manage flag, logged in. Returns (client, auth)."""
    db.create_user(DbUser(email=_ADMIN_EMAIL), _ADMIN_PASSWORD, can_manage=True)
    return client, login(_ADMIN_EMAIL, _ADMIN_PASSWORD)


@pytest.fixture()
def user_auth(db, client, login):
    """A plain authenticated user (an annotator who proposes)."""
    db.create_user(DbUser(email=_USER_EMAIL), _USER_PASSWORD)
    return login(_USER_EMAIL, _USER_PASSWORD)


@pytest.fixture()
def project_id(db) -> int:
    return db.create_project("Proposed Test Project", required_annotators=1)


def _proposed_curies(client, auth, project_id) -> set[str]:
    r = client.get(f"/projects/{project_id}/proposed-entities", headers=auth)
    assert r.status_code == 200, r.text
    return {e["curie"] for e in r.json()["entities"]}


class TestProposeEntity:
    def test_proposes_and_records_proposer(self, user_auth, project_id, client):
        r = client.post(
            f"/projects/{project_id}/proposed-entities",
            json={"label": _LABEL, "curie": _CURIE, "kind": _KIND},
            headers=user_auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["curie"] == _CURIE
        assert body["proposed_by"] == _USER_EMAIL

    def test_unauthenticated_cannot_propose(self, project_id):
        fresh_client = TestClient(app)
        r = fresh_client.post(
            f"/projects/{project_id}/proposed-entities",
            json={"label": _LABEL, "curie": _CURIE, "kind": _KIND},
        )
        assert r.status_code == 401


class TestProposeProperty:
    def test_proposes_and_records_proposer(self, user_auth, project_id, client):
        r = client.post(
            f"/projects/{project_id}/proposed-properties",
            json={"label": _PROP_LABEL, "curie": _PROP_CURIE},
            headers=user_auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["label"] == _PROP_LABEL
        assert body["proposed_by"] == _USER_EMAIL

    def test_unauthenticated_cannot_propose_property(self, project_id):
        fresh_client = TestClient(app)
        r = fresh_client.post(
            f"/projects/{project_id}/proposed-properties",
            json={"label": _PROP_LABEL},
        )
        assert r.status_code == 401


class TestListProposed:
    def test_admin_lists_proposed_entity(self, admin, db, project_id):
        client, auth = admin
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        r = client.get(
            f"/projects/{project_id}/proposed-entities", headers=auth
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert _CURIE in {e["curie"] for e in body["entities"]}

    def test_admin_entities_proposed_query_endpoint(
        self, admin, db, project_id
    ):
        client, auth = admin
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        r = client.get(
            f"/admin/entities/proposed?project_id={project_id}", headers=auth
        )
        assert r.status_code == 200
        assert _CURIE in {e["curie"] for e in r.json()["entities"]}

    def test_admin_lists_proposed_property(self, admin, db, project_id):
        client, auth = admin
        db.store_proposed_property(project_id, _PROP_LABEL, _PROP_CURIE)
        r = client.get(
            f"/projects/{project_id}/proposed-properties", headers=auth
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert _PROP_LABEL in {p["label"] for p in body["properties"]}

    def test_listing_requires_can_manage(self, user_auth, project_id, client):
        r = client.get(
            f"/projects/{project_id}/proposed-entities", headers=user_auth
        )
        assert r.status_code == 403


class TestConfirmEntity:
    def test_confirm_marks_entity_confirmed(self, admin, db, project_id):
        client, auth = admin
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)

        r = client.post(f"/admin/entities/{_CURIE}/confirm", headers=auth)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        assert db.get_entities_by_curies([_CURIE])[0].confirmed is True
        # A confirmed entity drops out of the proposed list.
        assert _CURIE not in _proposed_curies(client, auth, project_id)

    def test_confirm_requires_can_manage(
        self, user_auth, db, project_id, client
    ):
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        r = client.post(f"/admin/entities/{_CURIE}/confirm", headers=user_auth)
        assert r.status_code == 403


class TestDeleteEntity:
    def test_delete_removes_entity(self, admin, db, project_id):
        client, auth = admin
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)

        r = client.delete(f"/admin/entities/{_CURIE}", headers=auth)
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert db.get_entities_by_curies([_CURIE]) == []

    def test_delete_requires_can_manage(
        self, user_auth, db, project_id, client
    ):
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        r = client.delete(f"/admin/entities/{_CURIE}", headers=user_auth)
        assert r.status_code == 403


class TestAdminRenameCurie:
    def test_admin_renames_a_confirmed_entity(self, admin, db, project_id):
        client, auth = admin
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        db.confirm_entity(_CURIE)

        new_curie = "CHEBI:99999"
        r = client.patch(
            f"/admin/entities/{_CURIE}/curie",
            json={"new_curie": new_curie},
            headers=auth,
        )
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        assert db.get_entities_by_curies([_CURIE]) == []
        assert db.get_entities_by_curies([new_curie])[0].entity_id == new_curie

    def test_admin_rename_requires_can_manage(
        self, user_auth, db, project_id, client
    ):
        db.store_proposed_entity(project_id, _LABEL, _CURIE, _KIND)
        r = client.patch(
            f"/admin/entities/{_CURIE}/curie",
            json={"new_curie": "CHEBI:99999"},
            headers=user_auth,
        )
        assert r.status_code == 403
