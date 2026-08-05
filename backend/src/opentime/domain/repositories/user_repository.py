from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from opentime.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def get_password_hash(self, email: str) -> str | None:
        ...

    @abstractmethod
    async def create_refresh_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        ...

    @abstractmethod
    async def get_refresh_token(self, token_hash: str) -> tuple[UUID, UUID, datetime] | None:
        """Returns (token_id, user_id, expires_at) if valid and not revoked."""
        ...

    @abstractmethod
    async def revoke_refresh_token(self, token_hash: str) -> None:
        ...

    @abstractmethod
    async def revoke_all_refresh_tokens(self, user_id: UUID) -> None:
        ...
