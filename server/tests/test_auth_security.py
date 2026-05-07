"""Authentication and security tests."""

import pytest

from app.auth.api_keys import ApiKeySecretService
from app.auth.passwords import PasswordHasher
from app.auth.tokens import TokenService
from app.core.config import Settings


def test_password_hasher_verifies_password() -> None:
    hasher: PasswordHasher = PasswordHasher()
    password_hash: str = hasher.hash_password("very-secure-password")

    assert hasher.verify_password("very-secure-password", password_hash)
    assert not hasher.verify_password("wrong-password", password_hash)


def test_token_service_requires_secret() -> None:
    token_service: TokenService = TokenService(Settings(jwt_secret_key=None))

    with pytest.raises(RuntimeError):
        token_service.create_access_token("user-id")


def test_token_service_round_trips_subject() -> None:
    token_service: TokenService = TokenService(Settings(jwt_secret_key="test-secret"))

    token: str
    token, _ = token_service.create_access_token("user-id")

    assert token_service.decode_access_token(token) == "user-id"


def test_api_key_hashing_is_stable_without_storing_secret() -> None:
    service: ApiKeySecretService = ApiKeySecretService()
    api_key: str = service.create_key()

    assert api_key.startswith("cui_")
    assert service.hash_key(api_key) == service.hash_key(api_key)
    assert service.prefix(api_key) == api_key[:12]
