from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from opentime.application.auth.dto import UserResponse
from opentime.application.auth.use_cases import GetCurrentUserUseCase
from opentime.domain.exceptions import NotFoundError
from opentime.infrastructure.database.session import get_db_session
from opentime.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from opentime.infrastructure.security.jwt import decode_access_token

security = HTTPBearer()


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> UserResponse:
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from None

    use_case = GetCurrentUserUseCase(repo)
    try:
        return await use_case.execute(user_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        ) from None
