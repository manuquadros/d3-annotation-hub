from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ahbackend.users.users import create_access_token


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
