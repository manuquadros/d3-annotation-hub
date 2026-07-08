"""Shared fixtures for the backend integration tests.

Every integration test runs against a fresh in-memory SQLite ``D3TextDB`` wired
into the query and operation modules. ``transform_article`` (XML rendering) is
stubbed to a no-op so tests don't depend on well-formed JATS XML fixtures.
"""

import bcrypt
import pytest
from d3textdb import D3TextDB
from d3textdb.schema import User as DbUser
from fastapi.testclient import TestClient

import ahbackend.api.api as api_module
import ahbackend.db.operations as operations_module
import ahbackend.db.queries as queries_module
from ahbackend.api.api import app


@pytest.fixture(autouse=True)
def _fast_bcrypt(monkeypatch):
    """Hash at bcrypt's minimum cost factor in tests.

    ``d3textdb`` hashes with the default cost 12 (~250ms per call), which
    dominates the suite runtime through ``make_user``/``login`` setup. Cost 4
    is ~256x cheaper and equally valid against non-adversarial fixture data.
    ``checkpw`` derives its cost from the stored hash, so patching salt
    generation speeds up verification too.
    """
    real_gensalt = bcrypt.gensalt
    monkeypatch.setattr(
        bcrypt,
        "gensalt",
        lambda rounds=4, prefix=b"2b": real_gensalt(rounds, prefix),
    )


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


@pytest.fixture()
def make_user(db, login):
    """Factory: create a user and log in, returning a Bearer-header dict.

    Extra keyword args (``can_manage=True``, ``is_super_user=True``) are
    forwarded to ``create_user``.
    """

    def _make(email: str, password: str, **flags) -> dict[str, str]:
        db.create_user(DbUser(email=email), password, **flags)
        return login(email, password)

    return _make


@pytest.fixture()
def make_project(db):
    """Factory: create a project and return its id."""

    def _make(name: str = "Test Project", required_annotators: int = 2) -> int:
        return db.create_project(name, required_annotators=required_annotators)

    return _make


@pytest.fixture()
def anon_client() -> TestClient:
    """An unauthenticated ``TestClient`` (empty cookie jar) for 401 checks."""
    return TestClient(app)
