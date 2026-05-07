"""Password hashing and verification."""

from passlib.context import CryptContext


class PasswordHasher:
    """BCrypt password hashing service."""

    def __init__(self) -> None:
        self._context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self._context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        return self._context.verify(password, password_hash)
