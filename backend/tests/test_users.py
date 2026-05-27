from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from d3textdb.schema import UserAuth

from ahbackend.users.users import create_access_token, is_valid_credentials

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
        now = datetime(2024, 6, 15, 9, 30, 0, tzinfo=timezone.utc)

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
        now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
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
