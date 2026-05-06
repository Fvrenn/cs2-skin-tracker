import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "market_hash_name", name="uq_watchlist_user_skin"),
        Index("idx_watchlist_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    market_hash_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alert_on_drop: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    drop_threshold: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    alert_on_rise: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    rise_threshold: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="watchlist_items")  # type: ignore[name-defined]
    alert_logs: Mapped[list["AlertLog"]] = relationship(  # type: ignore[name-defined]
        back_populates="watchlist_item"
    )
