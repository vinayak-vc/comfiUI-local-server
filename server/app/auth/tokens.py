"""JWT token creation and validation."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import Settings


class TokenService:
    """Creates and validates access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._settings: Settings = settings

    def create_access_token(self, subject: str) -> tuple[str, int]:
        secret: str = self._get_secret()
        expires_delta: timedelta = timedelta(minutes=self._settings.jwt_access_token_expire_minutes)
        expires_at: datetime = datetime.now(UTC) + expires_delta
        payload: dict[str, Any] = {
            "sub": subject,
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(UTC),
        }
        token: str = jwt.encode(payload, secret, algorithm=self._settings.jwt_algorithm)
        return token, int(expires_delta.total_seconds())

    def decode_access_token(self, token: str) -> str:
        secret: str = self._get_secret()
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[self._settings.jwt_algorithm],
        )
        token_type: Any = payload.get("type")
        subject: Any = payload.get("sub")
        if token_type != "access" or not isinstance(subject, str):
            raise jwt.InvalidTokenError("Invalid access token.")
        return subject

    def _get_secret(self) -> str:
        if self._settings.jwt_secret_key is None:
            raise RuntimeError("JWT_SECRET_KEY must be configured before issuing or validating tokens.")
        secret: str = self._settings.jwt_secret_key.get_secret_value()
        if not secret.strip():
            raise RuntimeError("JWT_SECRET_KEY must be configured before issuing or validating tokens.")
        return secret
