"""Integration tests for admin user management endpoints.

Exercises POST /admin/users, DELETE /admin/users/{username}, and
GET /admin/passphrase-suggestion against a real in-memory SQLite database
via FastAPI's TestClient.
"""

import pytest
from d3textdb.schema import Reference
from d3textdb.schema import User as DbUser
from fastapi.testclient import TestClient

from ahbackend.api.api import app

_ADMIN_EMAIL = "admin@test.example"
_ADMIN_PASSWORD = "admin-secret"
_NEW_USER_EMAIL = "newuser@test.example"
_NEW_USER_PASSWORD = "initial-passphrase"


@pytest.fixture()
def ctx(db, client, login):
    """Fresh in-memory DB with one superuser. Returns (client, auth_headers)."""
    db.create_user(
        DbUser(email=_ADMIN_EMAIL), _ADMIN_PASSWORD, is_super_user=True
    )
    auth = login(_ADMIN_EMAIL, _ADMIN_PASSWORD)
    return client, auth


class TestCreateUser:
    def test_creates_user_and_returns_201(self, ctx):
        client, auth = ctx
        r = client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["email"] == _NEW_USER_EMAIL
        assert body["is_super_user"] is False
        assert body["can_manage"] is False

    def test_newly_created_user_can_log_in(self, ctx):
        client, auth = ctx
        client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        r = client.post(
            "/token",
            data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_generated_password_is_returned_when_none_provided(self, ctx):
        client, auth = ctx
        r = client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL},
            headers=auth,
        )
        assert r.status_code == 201
        generated = r.json().get("generated_password")
        assert generated and len(generated) > 0

    def test_user_can_log_in_with_generated_password(self, ctx):
        client, auth = ctx
        r = client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL},
            headers=auth,
        )
        generated = r.json()["generated_password"]
        r = client.post(
            "/token", data={"username": _NEW_USER_EMAIL, "password": generated}
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_duplicate_email_returns_409(self, ctx):
        client, auth = ctx
        payload = {"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD}
        client.post("/admin/users", json=payload, headers=auth)
        r = client.post("/admin/users", json=payload, headers=auth)
        assert r.status_code == 409

    def test_non_superuser_is_rejected(self, ctx):
        client, auth = ctx
        client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        r = client.post(
            "/token",
            data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        plain_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = client.post(
            "/admin/users",
            json={"email": "another@test.example", "password": "pass"},
            headers=plain_auth,
        )
        assert r.status_code == 403

    def test_unauthenticated_request_is_rejected(self, ctx):
        # Use a fresh client with no cookie jar so the auth_token cookie from
        # the fixture's login doesn't silently authenticate the request.
        fresh_client = TestClient(app)
        r = fresh_client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        assert r.status_code == 401


@pytest.fixture()
def ctx_with_member(ctx, db):
    """Extends ctx with a regular user who is a member of a project."""
    client, auth = ctx
    user_id = db.create_user(DbUser(email=_NEW_USER_EMAIL), _NEW_USER_PASSWORD)
    project_id = db.create_project("Test Project", required_annotators=1)
    db.add_project_member(project_id, user_id, "annotator")
    return client, auth, db, project_id


class TestRemoveUser:
    def _create_new_user(self, client, auth):
        r = client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        assert r.status_code == 201
        return r.json()

    def test_deletes_user_with_no_references(self, ctx):
        client, auth = ctx
        self._create_new_user(client, auth)
        r = client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        assert r.status_code == 200
        assert r.json()["action"] == "deleted"

    def test_deleted_user_no_longer_appears_in_list(self, ctx):
        client, auth = ctx
        self._create_new_user(client, auth)
        client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        r = client.get("/admin/users", headers=auth)
        emails = [u["email"] for u in r.json()]
        assert _NEW_USER_EMAIL not in emails

    def test_deleted_user_cannot_log_in(self, ctx):
        client, auth = ctx
        self._create_new_user(client, auth)
        client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        r = client.post(
            "/token",
            data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        assert r.status_code == 401

    def test_disables_user_that_has_project_membership(self, ctx_with_member):
        client, auth, _, __ = ctx_with_member
        r = client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        assert r.status_code == 200
        assert r.json()["action"] == "disabled"

    def test_disabled_user_cannot_log_in(self, ctx_with_member):
        client, auth, _, __ = ctx_with_member
        client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        r = client.post(
            "/token",
            data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        assert r.status_code == 401

    def test_disabled_user_appears_in_list_with_disabled_flag(
        self, ctx_with_member
    ):
        client, auth, _, __ = ctx_with_member
        client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        r = client.get("/admin/users", headers=auth)
        user = next(u for u in r.json() if u["email"] == _NEW_USER_EMAIL)
        assert user["disabled"] is True

    def test_cannot_remove_own_account(self, ctx):
        client, auth = ctx
        r = client.delete(f"/admin/users/{_ADMIN_EMAIL}", headers=auth)
        assert r.status_code == 400

    def test_removing_nonexistent_user_returns_404(self, ctx):
        client, auth = ctx
        r = client.delete("/admin/users/nobody@test.example", headers=auth)
        assert r.status_code == 404

    def test_disables_user_with_annotation_state(self, ctx_with_member):
        client, auth, test_db, project_id = ctx_with_member
        ref_id = test_db.store_reference(
            Reference(
                pubmed_id=12345678,
                authors="Doe J",
                title="Test",
                journal="J",
                volume="1",
                pages="1",
                year=2024,
                abstract="",
            )
        )
        test_db.add_reference_to_project(project_id, ref_id)
        r = client.delete(f"/admin/users/{_NEW_USER_EMAIL}", headers=auth)
        assert r.json()["action"] == "disabled"


@pytest.fixture()
def ctx_with_plain_user(ctx, login):
    """Extends ctx with a plain user (no can_manage, no is_super_user).

    Returns (client, admin_auth, user_auth) where user_auth is a Bearer
    header dict for the plain user.
    """
    client, admin_auth = ctx
    client.post(
        "/admin/users",
        json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        headers=admin_auth,
    )
    user_auth = login(_NEW_USER_EMAIL, _NEW_USER_PASSWORD)
    return client, admin_auth, user_auth


class TestPermissions:
    def _set_permissions(self, client, admin_auth, *, can_manage: bool):
        r = client.put(
            f"/admin/users/{_NEW_USER_EMAIL}/permissions",
            json={"can_manage": can_manage, "is_super_user": False},
            headers=admin_auth,
        )
        assert r.status_code == 204

    def test_new_user_has_can_manage_false(self, ctx_with_plain_user):
        client, admin_auth, _ = ctx_with_plain_user
        r = client.get("/admin/users", headers=admin_auth)
        user = next(u for u in r.json() if u["email"] == _NEW_USER_EMAIL)
        assert user["can_manage"] is False
        assert user["is_super_user"] is False

    def test_plain_user_cannot_create_project(self, ctx_with_plain_user):
        client, _, user_auth = ctx_with_plain_user
        r = client.post(
            "/projects", json={"name": "My Project"}, headers=user_auth
        )
        assert r.status_code == 403

    def test_make_project_manager_updates_user_list(self, ctx_with_plain_user):
        client, admin_auth, _ = ctx_with_plain_user
        self._set_permissions(client, admin_auth, can_manage=True)
        r = client.get("/admin/users", headers=admin_auth)
        user = next(u for u in r.json() if u["email"] == _NEW_USER_EMAIL)
        assert user["can_manage"] is True

    def test_project_manager_can_create_project(self, ctx_with_plain_user):
        client, admin_auth, user_auth = ctx_with_plain_user
        self._set_permissions(client, admin_auth, can_manage=True)
        r = client.post(
            "/projects", json={"name": "My Project"}, headers=user_auth
        )
        assert r.status_code == 201
        assert r.json()["name"] == "My Project"

    def test_remove_project_manager_updates_user_list(
        self, ctx_with_plain_user
    ):
        client, admin_auth, _ = ctx_with_plain_user
        self._set_permissions(client, admin_auth, can_manage=True)
        self._set_permissions(client, admin_auth, can_manage=False)
        r = client.get("/admin/users", headers=admin_auth)
        user = next(u for u in r.json() if u["email"] == _NEW_USER_EMAIL)
        assert user["can_manage"] is False

    def test_removing_can_manage_revokes_project_creation(
        self, ctx_with_plain_user
    ):
        client, admin_auth, user_auth = ctx_with_plain_user
        self._set_permissions(client, admin_auth, can_manage=True)
        self._set_permissions(client, admin_auth, can_manage=False)
        r = client.post(
            "/projects", json={"name": "My Project"}, headers=user_auth
        )
        assert r.status_code == 403


class TestPassphraseSuggestion:
    def test_returns_a_non_empty_string(self, ctx):
        client, auth = ctx
        r = client.get("/admin/passphrase-suggestion", headers=auth)
        assert r.status_code == 200
        phrase = r.json()
        assert isinstance(phrase, str) and len(phrase) > 0

    def test_uses_hyphen_separated_words(self, ctx):
        client, auth = ctx
        r = client.get("/admin/passphrase-suggestion", headers=auth)
        parts = r.json().split("-")
        assert len(parts) == 4

    def test_any_authenticated_user_can_request(self, ctx):
        client, auth = ctx
        client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        r = client.post(
            "/token",
            data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
        )
        plain_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.get("/admin/passphrase-suggestion", headers=plain_auth)
        assert r.status_code == 200

    def test_unauthenticated_request_is_rejected(self, ctx):
        fresh_client = TestClient(app)
        r = fresh_client.get("/admin/passphrase-suggestion")
        assert r.status_code == 401
