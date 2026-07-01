"""Integration tests for account endpoints: change-password and logout.

Runs against a real in-memory SQLite database. Shared ``db``/``client``/
``login`` fixtures live in ``conftest.py``.
"""

import pytest

_EMAIL = "account@account-test.example"
_PASSWORD = "original-secret"
_NEW_PASSWORD = "brand-new-secret"


@pytest.fixture()
def user(client, make_user):
    """A logged-in user. Returns (client, auth)."""
    return client, make_user(_EMAIL, _PASSWORD)


def _login_status(client, email, password) -> int:
    return client.post(
        "/token", data={"username": email, "password": password}
    ).status_code


class TestChangePassword:
    def test_changes_the_password(self, user):
        client, auth = user
        r = client.post(
            "/change-password",
            json={
                "current_password": _PASSWORD,
                "new_password": _NEW_PASSWORD,
            },
            headers=auth,
        )
        assert r.status_code == 200
        assert _login_status(client, _EMAIL, _NEW_PASSWORD) == 200
        assert _login_status(client, _EMAIL, _PASSWORD) == 401

    def test_wrong_current_password_is_rejected(self, user):
        client, auth = user
        r = client.post(
            "/change-password",
            json={
                "current_password": "not-my-password",
                "new_password": _NEW_PASSWORD,
            },
            headers=auth,
        )
        assert r.status_code == 401
        # The password is unchanged.
        assert _login_status(client, _EMAIL, _PASSWORD) == 200

    def test_unauthenticated_request_is_rejected(self, anon_client):
        r = anon_client.post(
            "/change-password",
            json={
                "current_password": _PASSWORD,
                "new_password": _NEW_PASSWORD,
            },
        )
        assert r.status_code == 401


class TestLogout:
    def test_logout_clears_the_auth_cookie(self, user):
        client, _ = user
        assert client.cookies.get("auth_token")
        r = client.post("/logout")
        assert r.status_code == 200
        assert not client.cookies.get("auth_token")
