from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentime.domain.entities.user import User
from opentime.domain.repositories.user_repository import UserRepository
from opentime.infrastructure.database.models.refresh_token import RefreshTokenModel
from opentime.infrastructure.database.models.user import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        full_name=model.full_name,
        is_active=model.is_active,
        is_verified=model.is_verified,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> User:
        model = UserModel(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_password_hash(self, email: str) -> str | None:
        result = await self._session.execute(
            select(UserModel.password_hash).where(UserModel.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        model = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model.id

    async def get_refresh_token(self, token_hash: str) -> tuple[UUID, UUID, datetime] | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.token_hash == token_hash,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        if model.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            return None
        return model.id, model.user_id, model.expires_at

    async def revoke_refresh_token(self, token_hash: str) -> None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        if model:
            model.revoked_at = datetime.now(UTC)

    async def revoke_all_refresh_tokens(self, user_id: UUID) -> None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        for model in result.scalars():
            model.revoked_at = datetime.now(UTC)
