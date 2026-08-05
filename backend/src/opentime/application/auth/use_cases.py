from uuid import UUID

from opentime.application.auth.dto import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from opentime.domain.entities.user import User
from opentime.domain.exceptions import AuthenticationError, ConflictError, NotFoundError
from opentime.domain.repositories.user_repository import UserRepository
from opentime.infrastructure.security.jwt import create_access_token, get_refresh_token_expiry
from opentime.infrastructure.security.password import (
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def _issue_tokens(user: User, repo: UserRepository) -> TokenResponse:
    access_token = create_access_token(user.id, user.email)
    refresh_token = generate_refresh_token()
    refresh_hash = hash_token(refresh_token)
    await repo.create_refresh_token(user.id, refresh_hash, get_refresh_token_expiry())
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


class RegisterUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, request: RegisterRequest) -> AuthResponse:
        existing = await self._repo.get_by_email(request.email)
        if existing:
            raise ConflictError("An account with this email already exists")

        user = await self._repo.create(
            email=request.email,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
        )
        tokens = await _issue_tokens(user, self._repo)
        return AuthResponse(user=_user_to_response(user), tokens=tokens)


class LoginUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, request: LoginRequest) -> AuthResponse:
        password_hash = await self._repo.get_password_hash(request.email)
        if not password_hash or not verify_password(request.password, password_hash):
            raise AuthenticationError("Invalid email or password")

        user = await self._repo.get_by_email(request.email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid email or password")

        tokens = await _issue_tokens(user, self._repo)
        return AuthResponse(user=_user_to_response(user), tokens=tokens)


class RefreshTokenUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, request: RefreshRequest) -> TokenResponse:
        token_hash = hash_token(request.refresh_token)
        token_data = await self._repo.get_refresh_token(token_hash)
        if not token_data:
            raise AuthenticationError("Invalid or expired refresh token")

        _, user_id, _ = token_data
        await self._repo.revoke_refresh_token(token_hash)

        user = await self._repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account is inactive")

        return await _issue_tokens(user, self._repo)


class LogoutUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        await self._repo.revoke_refresh_token(token_hash)


class GetCurrentUserUseCase:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: UUID) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return _user_to_response(user)
