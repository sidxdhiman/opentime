from datetime import datetime
from uuid import UUID as PyUUID
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[PyUUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )
