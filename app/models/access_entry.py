from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime

if TYPE_CHECKING:
    from app.models.access_key import AccessKey


class AccessEntry(Base):
    __tablename__ = "access_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now()
    )
    keys: Mapped[list["AccessKey"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="AccessKey.sort_order",
        lazy="selectin",
    )
