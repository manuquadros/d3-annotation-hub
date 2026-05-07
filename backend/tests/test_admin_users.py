"""Integration tests for admin user management endpoints.

Exercises POST /admin/users and GET /admin/passphrase-suggestion against a
real in-memory SQLite database via FastAPI's TestClient.
"""

import pytest
from fastapi.testclient import TestClient

import ahbackend.api.api as api_module
import ahbackend.db.db as db_impl
from ahbackend.api.api import app
from d3textdb import D3TextDB
from d3textdb.schema import User as DbUser

_ADMIN_EMAIL = "admin@test.example"
_ADMIN_PASSWORD = "admin-secret"
_NEW_USER_EMAIL = "newuser@test.example"
_NEW_USER_PASSWORD = "initial-passphrase"


@pytest.fixture()
def ctx(monkeypatch):
    """Fresh in-memory DB with one superuser. Returns (client, auth_headers)."""
    test_db = D3TextDB()
    monkeypatch.setattr(db_impl, "annodb", test_db)
    monkeypatch.setattr(api_module, "transform_article", lambda x: x or "")

    test_db.create_user(DbUser(email=_ADMIN_EMAIL), _ADMIN_PASSWORD, is_super_user=True)

    client = TestClient(app)
    r = client.post("/token", data={"username": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
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
            "/token", data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD}
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
            "/token", data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD}
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

    def test_non_superuser_is_rejected(self, ctx):
        client, auth = ctx
        client.post(
            "/admin/users",
            json={"email": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD},
            headers=auth,
        )
        r = client.post(
            "/token", data={"username": _NEW_USER_EMAIL, "password": _NEW_USER_PASSWORD}
        )
        plain_auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = client.get("/admin/passphrase-suggestion", headers=plain_auth)
        assert r.status_code == 403
