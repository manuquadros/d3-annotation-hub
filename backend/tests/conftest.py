"""Shared fixtures for the backend integration tests.

Every integration test runs against a fresh in-memory SQLite ``D3TextDB`` wired
into the query and operation modules. ``transform_article`` (XML rendering) is
stubbed to a no-op so tests don't depend on well-formed JATS XML fixtures.
"""

import pytest
from d3textdb import D3TextDB
from fastapi.testclient import TestClient

import ahbackend.api.api as api_module
import ahbackend.db.operations as operations_module
import ahbackend.db.queries as queries_module
from ahbackend.api.api import app


@pytest.fixture()
def db(monkeypatch) -> D3TextDB:
    """A fresh in-memory database patched into the query/operation modules."""
    test_db = D3TextDB()
    monkeypatch.setattr(queries_module, "annodb", test_db)
    monkeypatch.setattr(operations_module, "annodb", test_db)
    monkeypatch.setattr(api_module, "transform_article", lambda x: x or "")
    return test_db


@pytest.fixture()
def client(db) -> TestClient:
    """A ``TestClient`` for the app, with the in-memory DB patched in."""
    return TestClient(app)


@pytest.fixture()
def login(client):
    """Return a helper that logs a user in and yields a Bearer-header dict."""

    def _login(email: str, password: str) -> dict[str, str]:
        r = client.post(
            "/token", data={"username": email, "password": password}
        )
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
