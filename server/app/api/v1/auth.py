"""Authentication routes."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.service import AuthService
from app.dependencies import get_auth_service, require_admin_principal, require_principal
from app.schemas.auth import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    Principal,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)

router: APIRouter = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: UserCreateRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return await auth_service.register_user(request)


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await auth_service.authenticate(form.username, form.password)


@router.get("/me", response_model=Principal)
async def get_current_principal(
    principal: Principal = Depends(require_principal),
) -> Principal:
    return principal


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    principal: Principal = Depends(require_admin_principal),
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiKeyCreateResponse:
    return await auth_service.create_api_key(principal, request.name)
