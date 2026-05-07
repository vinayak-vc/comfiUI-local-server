"""Authentication request and response schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class PrincipalType(StrEnum):
    USER = "user"
    API_KEY = "api_key"


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    created_at: datetime


class Principal(BaseModel):
    id: str
    type: PrincipalType
    name: str
    is_admin: bool = False
