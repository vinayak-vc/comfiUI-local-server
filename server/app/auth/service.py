"""Authentication business service."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_keys import ApiKeySecretService
from app.auth.passwords import PasswordHasher
from app.auth.tokens import TokenService
from app.core.config import Settings
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.auth import (
    ApiKeyCreateResponse,
    Principal,
    PrincipalType,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)


class AuthService:
    """Coordinates user auth, JWTs, and API keys."""

    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self._settings: Settings = settings
        self._session: AsyncSession = session
        self._password_hasher: PasswordHasher = PasswordHasher()
        self._token_service: TokenService = TokenService(settings)
        self._api_key_service: ApiKeySecretService = ApiKeySecretService()

    async def register_user(self, request: UserCreateRequest) -> UserResponse:
        if not self._settings.allow_user_registration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User registration is disabled.",
            )

        existing_user: User | None = await self._get_user_by_email(request.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists.",
            )

        user_count: int = await self._count_users()
        user: User = User(
            email=request.email.lower(),
            password_hash=self._password_hasher.hash_password(request.password),
            is_admin=user_count == 0,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_user_response(user)

    async def authenticate(self, email: str, password: str) -> TokenResponse:
        user: User | None = await self._get_user_by_email(email)
        if user is None or not user.is_active:
            raise self._invalid_credentials()

        if not self._password_hasher.verify_password(password, user.password_hash):
            raise self._invalid_credentials()

        token: str
        expires_in: int
        token, expires_in = self._token_service.create_access_token(user.id)
        return TokenResponse(access_token=token, expires_in=expires_in)

    async def get_principal_from_token(self, token: str) -> Principal:
        user_id: str = self._token_service.decode_access_token(token)
        user: User | None = await self._session.get(User, user_id)
        if user is None or not user.is_active:
            raise self._invalid_credentials()

        return Principal(
            id=user.id,
            type=PrincipalType.USER,
            name=user.email,
            is_admin=user.is_admin,
        )

    async def get_principal_from_api_key(self, api_key: str) -> Principal:
        key_hash: str = self._api_key_service.hash_key(api_key)
        result = await self._session.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active.is_(True),
            )
        )
        key: ApiKey | None = result.scalar_one_or_none()
        if key is None:
            raise self._invalid_credentials()

        key.last_used_at = datetime.now(UTC)
        await self._session.commit()
        return Principal(
            id=key.id,
            type=PrincipalType.API_KEY,
            name=key.name,
            is_admin=False,
        )

    async def create_api_key(self, principal: Principal, name: str) -> ApiKeyCreateResponse:
        if not principal.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges are required.",
            )

        raw_key: str = self._api_key_service.create_key()
        api_key: ApiKey = ApiKey(
            name=name,
            key_prefix=self._api_key_service.prefix(raw_key),
            key_hash=self._api_key_service.hash_key(raw_key),
        )
        self._session.add(api_key)
        await self._session.commit()
        await self._session.refresh(api_key)
        return ApiKeyCreateResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            api_key=raw_key,
            created_at=api_key.created_at,
        )

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def _count_users(self) -> int:
        result = await self._session.execute(select(User))
        return len(list(result.scalars().all()))

    def _to_user_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )

    def _invalid_credentials(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
