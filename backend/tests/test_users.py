import inspect
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from d3textdb.schema import UserAuth

from ahbackend.users import users as users_module
from ahbackend.users.users import (
    create_access_token,
    is_valid_credentials,
    validate_password_policy,
)

_DUMMY_UUID = UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def key_pair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def _decode(token: str, public_key) -> dict:
    return jwt.decode(token, public_key, algorithms=["EdDSA"])


class TestCreateAccessToken:
    def test_deterministic_with_same_inputs(self, key_pair):
        """Same inputs always produce the same token."""
        private_key, _ = key_pair
        now = datetime(2024, 6, 15, 9, 30, 0, tzinfo=UTC)

        token1 = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(hours=1),
            now=now,
            private_key=private_key,
            algorithm="EdDSA",
        )
        token2 = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(hours=1),
            now=now,
            private_key=private_key,
            algorithm="EdDSA",
        )

        assert token1 == token2

    def test_input_data_is_not_mutated(self, key_pair):
        private_key, _ = key_pair
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        data = {"sub": "user@example.com"}

        create_access_token(
            data=data,
            expires_delta=timedelta(minutes=15),
            now=now,
            private_key=private_key,
            algorithm="EdDSA",
        )

        assert data == {"sub": "user@example.com"}


_PLAIN_PASSWORD = "correct-password"


@pytest.fixture
def hashed_password():
    return bcrypt.hashpw(_PLAIN_PASSWORD.encode(), bcrypt.gensalt()).decode()


def _make_user_auth(hashed_password: str, disabled: bool = False) -> UserAuth:
    return UserAuth(
        user_id=_DUMMY_UUID,
        hashed_password=hashed_password,
        disabled=disabled,
    )


class TestIsValidCredentials:
    def test_returns_false_when_user_auth_is_none(self):
        assert not is_valid_credentials(_PLAIN_PASSWORD, None)

    def test_returns_false_when_user_is_disabled(self, hashed_password):
        auth = _make_user_auth(hashed_password, disabled=True)
        assert not is_valid_credentials(_PLAIN_PASSWORD, auth)

    def test_returns_false_with_wrong_password(self, hashed_password):
        auth = _make_user_auth(hashed_password)
        assert not is_valid_credentials("wrong-password", auth)

    def test_returns_true_with_correct_password_and_active_user(
        self, hashed_password
    ):
        auth = _make_user_auth(hashed_password)
        assert is_valid_credentials(_PLAIN_PASSWORD, auth)

    def test_runs_bcrypt_even_for_a_missing_account(self, monkeypatch):
        """A missing auth row must still cost a bcrypt verification (against the
        dummy hash), otherwise the faster reply leaks that the email is
        unregistered — the user-enumeration timing oracle in TICKET-27."""
        seen: list[str] = []
        real_verify = users_module.verify_password

        def spy(password: str, hashed: str) -> bool:
            seen.append(hashed)
            return real_verify(password, hashed)

        monkeypatch.setattr(users_module, "verify_password", spy)
        assert not is_valid_credentials("anything", None)
        assert seen == [users_module._DUMMY_HASH]

    def test_runs_bcrypt_even_for_a_disabled_account(
        self, monkeypatch, hashed_password
    ):
        seen: list[str] = []
        real_verify = users_module.verify_password

        def spy(password: str, hashed: str) -> bool:
            seen.append(hashed)
            return real_verify(password, hashed)

        monkeypatch.setattr(users_module, "verify_password", spy)
        auth = _make_user_auth(hashed_password, disabled=True)
        assert not is_valid_credentials(_PLAIN_PASSWORD, auth)
        assert seen == [hashed_password]


class TestAuthDependenciesStaySync:
    """The auth dependencies must be plain ``def`` so FastAPI runs their
    synchronous SQLite work in a threadpool. Reverting any of them to
    ``async def`` would put the DB reads back on the event loop (TICKET-43),
    which no functional test would catch."""

    @pytest.mark.parametrize(
        "dependency",
        [
            users_module.get_current_user,
            users_module.get_current_user_auth,
            users_module.get_current_active_user,
            users_module.get_current_admin,
            users_module.get_current_superuser,
            users_module.require_manager,
        ],
    )
    def test_dependency_is_not_a_coroutine(self, dependency):
        assert not inspect.iscoroutinefunction(dependency)


class TestAuthRowDeduplication:
    def test_stacked_auth_dependencies_fetch_auth_row_once(
        self, client, make_user, monkeypatch
    ):
        """A request whose dependency chain stacks active-user + admin checks
        should hit ``get_user_auth`` a single time — the shared
        ``get_current_user_auth`` dependency is cached per request rather than
        re-fetched by each layer (TICKET-43)."""
        headers = make_user(
            "admin@example.com", "a-decent-password", can_manage=True
        )
        real_get_user_auth = users_module.get_user_auth
        calls: list = []

        def spy(user_id):
            calls.append(user_id)
            return real_get_user_auth(user_id)

        # Patch after login so only the counted request contributes.
        monkeypatch.setattr(users_module, "get_user_auth", spy)
        response = client.get("/admin/ontologies", headers=headers)

        assert response.status_code == 200, response.text
        assert len(calls) == 1

    def test_route_body_reuses_dependency_auth_row(
        self, client, make_user, monkeypatch
    ):
        """A route whose body needs the auth row (``/me``) reads it from the
        injected, already-cached dependency instead of issuing its own
        ``get_user_auth`` query (TICKET-43)."""
        headers = make_user("member@example.com", "a-decent-password")
        real_get_user_auth = users_module.get_user_auth
        calls: list = []

        def spy(user_id):
            calls.append(user_id)
            return real_get_user_auth(user_id)

        monkeypatch.setattr(users_module, "get_user_auth", spy)
        response = client.get("/me", headers=headers)

        assert response.status_code == 200, response.text
        assert len(calls) == 1


class TestValidatePasswordPolicy:
    def test_accepts_a_reasonable_password(self):
        assert validate_password_policy("a-decent-password") is None

    def test_rejects_a_too_short_password(self):
        assert validate_password_policy("short") is not None

    def test_rejects_an_empty_password(self):
        assert validate_password_policy("") is not None

    def test_rejects_a_password_over_72_bytes(self):
        assert validate_password_policy("a" * 73) is not None

    def test_counts_utf8_bytes_not_characters(self):
        # 40 two-byte characters = 80 bytes > 72, though only 40 code points, so
        # a character-count check would wrongly accept a truncatable password.
        assert validate_password_policy("é" * 40) is not None
