"""API key generation and hashing."""

import hashlib
import secrets


class ApiKeySecretService:
    """Creates opaque API keys and stores only hashes."""

    def create_key(self) -> str:
        return f"cui_{secrets.token_urlsafe(32)}"

    def hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def prefix(self, api_key: str) -> str:
        return api_key[:12]
