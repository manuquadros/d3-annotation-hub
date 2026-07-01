"""Integration tests for project management and membership endpoints.

Covers project create/list/get/archive and member list/lookup/search/add/remove
against a real in-memory SQLite database. ``get_current_admin`` requires the
``can_manage`` flag; ``require_manager`` accepts ``can_manage`` or a project
``manager`` role. Shared ``db``/``client``/``login`` fixtures live in
``conftest.py``.
"""

import pytest
from d3textdb.schema import User as DbUser

_MANAGER_EMAIL = "manager@projects-test.example"
_MANAGER_PASSWORD = "manager-secret"
_PLAIN_EMAIL = "plain@projects-test.example"
_PLAIN_PASSWORD = "plain-secret"
_MEMBER_EMAIL = "member@projects-test.example"
_MEMBER_PASSWORD = "member-secret"
_NEW_MEMBER_EMAIL = "newmember@projects-test.example"


@pytest.fixture()
def manager(client, make_user):
    """A user with the can_manage flag, logged in. Returns (client, auth)."""
    return client, make_user(
        _MANAGER_EMAIL, _MANAGER_PASSWORD, can_manage=True
    )


@pytest.fixture()
def plain_auth(make_user):
    """A plain user (no can_manage, no roles). Returns a Bearer-header dict."""
    return make_user(_PLAIN_EMAIL, _PLAIN_PASSWORD)


def _create_project(client, auth, name="Test Project", **kwargs) -> int:
    r = client.post("/projects", json={"name": name, **kwargs}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["project_id"]


def _members(client, auth, project_id) -> list[dict]:
    r = client.get(f"/projects/{project_id}/members", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def _member(members: list[dict], email: str) -> dict | None:
    return next((m for m in members if m["email"] == email), None)


class TestCreateProject:
    def test_creates_project_and_returns_201(self, manager):
        client, auth = manager
        r = client.post(
            "/projects",
            json={"name": "My Project", "description": "desc"},
            headers=auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "My Project"
        assert body["description"] == "desc"

    def test_default_required_annotators_is_two(self, manager):
        client, auth = manager
        pid = _create_project(client, auth, name="Defaults")
        r = client.get(f"/projects/{pid}", headers=auth)
        assert r.json()["required_annotators"] == 2

    def test_creator_is_added_as_manager(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        member = _member(_members(client, auth, pid), _MANAGER_EMAIL)
        assert member is not None
        assert member["roles"] == ["manager"]

    def test_plain_user_cannot_create_project(self, plain_auth, client):
        r = client.post("/projects", json={"name": "Nope"}, headers=plain_auth)
        assert r.status_code == 403

    def test_unauthenticated_request_is_rejected(self, anon_client):
        r = anon_client.post("/projects", json={"name": "Nope"})
        assert r.status_code == 401


class TestArchiveProject:
    def test_archives_existing_project(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.delete(f"/projects/{pid}", headers=auth)
        assert r.status_code == 204

    def test_archiving_twice_returns_404(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        client.delete(f"/projects/{pid}", headers=auth)
        r = client.delete(f"/projects/{pid}", headers=auth)
        assert r.status_code == 404

    def test_archiving_unknown_project_returns_404(self, manager):
        client, auth = manager
        r = client.delete("/projects/99999", headers=auth)
        assert r.status_code == 404

    def test_plain_user_cannot_archive(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.delete(f"/projects/{pid}", headers=plain_auth)
        assert r.status_code == 403


class TestListProjects:
    def test_manager_sees_all_projects(self, manager):
        client, auth = manager
        _create_project(client, auth, name="Project A")
        _create_project(client, auth, name="Project B")
        r = client.get("/projects", headers=auth)
        assert r.status_code == 200
        names = {p["name"] for p in r.json()}
        assert {"Project A", "Project B"} <= names

    def test_plain_user_sees_only_their_projects(self, manager, plain_auth):
        client, auth = manager
        a = _create_project(client, auth, name="Project A")
        _create_project(client, auth, name="Project B")
        r = client.post(
            f"/projects/{a}/members",
            json={"email": _PLAIN_EMAIL, "role": "annotator"},
            headers=auth,
        )
        assert r.status_code == 201, r.text

        r = client.get("/projects", headers=plain_auth)
        assert r.status_code == 200
        assert [p["name"] for p in r.json()] == ["Project A"]

    def test_unauthenticated_request_is_rejected(self, anon_client):
        r = anon_client.get("/projects")
        assert r.status_code == 401


class TestGetProject:
    def test_manager_can_get_any_project(self, manager):
        client, auth = manager
        pid = _create_project(client, auth, name="Visible")
        r = client.get(f"/projects/{pid}", headers=auth)
        assert r.status_code == 200
        assert r.json()["name"] == "Visible"

    def test_member_can_get_project(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        client.post(
            f"/projects/{pid}/members",
            json={"email": _PLAIN_EMAIL, "role": "annotator"},
            headers=auth,
        )
        r = client.get(f"/projects/{pid}", headers=plain_auth)
        assert r.status_code == 200

    def test_non_member_gets_403(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.get(f"/projects/{pid}", headers=plain_auth)
        assert r.status_code == 403

    def test_unknown_project_returns_404(self, manager):
        client, auth = manager
        r = client.get("/projects/99999", headers=auth)
        assert r.status_code == 404


class TestListMembers:
    def test_lists_members_with_roles(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        members = _members(client, auth, pid)
        emails = {m["email"] for m in members}
        assert {_MANAGER_EMAIL, _MEMBER_EMAIL} <= emails
        assert _member(members, _MEMBER_EMAIL)["roles"] == ["annotator"]

    def test_non_manager_cannot_list_members(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.get(f"/projects/{pid}/members", headers=plain_auth)
        assert r.status_code == 403


class TestLookupAndSearch:
    def test_lookup_finds_existing_user(self, manager, db):
        client, auth = manager
        db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        r = client.get(
            f"/projects/{pid}/members/lookup?email={_MEMBER_EMAIL}",
            headers=auth,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["exists"] is True
        assert body["email"] == _MEMBER_EMAIL

    def test_lookup_reports_unknown_user(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.get(
            f"/projects/{pid}/members/lookup?email=ghost@projects-test.example",
            headers=auth,
        )
        assert r.status_code == 200
        assert r.json()["exists"] is False

    def test_search_returns_matching_users(self, manager, db):
        client, auth = manager
        db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        r = client.get(f"/projects/{pid}/users/search?q=member", headers=auth)
        assert r.status_code == 200
        emails = {u["email"] for u in r.json()}
        assert _MEMBER_EMAIL in emails

    def test_search_requires_manager(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.get(
            f"/projects/{pid}/users/search?q=member", headers=plain_auth
        )
        assert r.status_code == 403


class TestAddMember:
    def test_adds_existing_user_as_annotator(self, manager, db):
        client, auth = manager
        db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        r = client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == _MEMBER_EMAIL
        assert body["roles"] == ["annotator"]
        assert body["generated_password"] is None

    def test_creates_new_user_with_generated_password(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.post(
            f"/projects/{pid}/members",
            json={"email": _NEW_MEMBER_EMAIL, "role": "curator"},
            headers=auth,
        )
        assert r.status_code == 201
        generated = r.json()["generated_password"]
        assert generated
        # The new user can log in with the generated password.
        r = client.post(
            "/token",
            data={"username": _NEW_MEMBER_EMAIL, "password": generated},
        )
        assert r.status_code == 200

    def test_creates_new_user_with_provided_password(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.post(
            f"/projects/{pid}/members",
            json={
                "email": _NEW_MEMBER_EMAIL,
                "role": "annotator",
                "password": "chosen-secret",
            },
            headers=auth,
        )
        assert r.status_code == 201
        assert r.json()["generated_password"] is None
        r = client.post(
            "/token",
            data={"username": _NEW_MEMBER_EMAIL, "password": "chosen-secret"},
        )
        assert r.status_code == 200

    def test_invalid_role_returns_422(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "spectator"},
            headers=auth,
        )
        assert r.status_code == 422

    def test_adding_to_unknown_project_returns_404(self, manager):
        client, auth = manager
        r = client.post(
            "/projects/99999/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        assert r.status_code == 404

    def test_non_manager_cannot_add_member(self, manager, plain_auth):
        client, auth = manager
        pid = _create_project(client, auth)
        r = client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=plain_auth,
        )
        assert r.status_code == 403

    def test_annotator_and_curator_are_mutually_exclusive(self, manager, db):
        client, auth = manager
        db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        # Assigning curator replaces the annotator role rather than adding it.
        r = client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "curator"},
            headers=auth,
        )
        assert r.status_code == 201
        assert r.json()["roles"] == ["curator"]


class TestRemoveMember:
    def test_remove_all_roles_drops_the_member(self, manager, db):
        client, auth = manager
        db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        client.post(
            f"/projects/{pid}/members",
            json={"email": _MEMBER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        user_id = _member(_members(client, auth, pid), _MEMBER_EMAIL)["user_id"]

        r = client.delete(f"/projects/{pid}/members/{user_id}", headers=auth)
        assert r.status_code == 204
        assert _member(_members(client, auth, pid), _MEMBER_EMAIL) is None

    def test_remove_specific_role_keeps_other_roles(self, manager):
        client, auth = manager
        pid = _create_project(client, auth)
        # The creator is a manager; also give them the annotator role.
        client.post(
            f"/projects/{pid}/members",
            json={"email": _MANAGER_EMAIL, "role": "annotator"},
            headers=auth,
        )
        user_id = _member(_members(client, auth, pid), _MANAGER_EMAIL)[
            "user_id"
        ]

        r = client.delete(
            f"/projects/{pid}/members/{user_id}/annotator", headers=auth
        )
        assert r.status_code == 204
        roles = _member(_members(client, auth, pid), _MANAGER_EMAIL)["roles"]
        assert roles == ["manager"]

    def test_non_manager_cannot_remove_member(self, manager, plain_auth, db):
        client, auth = manager
        user_id = db.create_user(DbUser(email=_MEMBER_EMAIL), _MEMBER_PASSWORD)
        pid = _create_project(client, auth)
        r = client.delete(
            f"/projects/{pid}/members/{user_id}", headers=plain_auth
        )
        assert r.status_code == 403
