from fastapi import APIRouter, Depends, HTTPException, status

from chronos_engine.telemetry import record_event as record_product_event
from opentime.api.dependencies import get_current_user, get_user_repository
from opentime.api.errors import domain_error_to_http
from opentime.application.auth.dto import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from opentime.application.auth.use_cases import (
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
    RegisterUseCase,
)
from opentime.domain.exceptions import DomainError
from opentime.infrastructure.repositories.user_repository import SQLAlchemyUserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> AuthResponse:
    use_case = RegisterUseCase(repo)
    try:
        result = await use_case.execute(request)
    except DomainError as e:
        status_code, detail = domain_error_to_http(e)
        raise HTTPException(status_code=status_code, detail=detail) from e
    try:
        await record_product_event(str(result.user.id), "account_created")
    except Exception:  # telemetry must never break the auth flow
        pass
    return result


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> AuthResponse:
    use_case = LoginUseCase(repo)
    try:
        return await use_case.execute(request)
    except DomainError as e:
        status_code, detail = domain_error_to_http(e)
        raise HTTPException(status_code=status_code, detail=detail) from e


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    use_case = RefreshTokenUseCase(repo)
    try:
        return await use_case.execute(request)
    except DomainError as e:
        status_code, detail = domain_error_to_http(e)
        raise HTTPException(status_code=status_code, detail=detail) from e


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshRequest,
    repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> None:
    use_case = LogoutUseCase(repo)
    await use_case.execute(request.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return current_user
