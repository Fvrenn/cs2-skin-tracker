import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SkinStatus(str, enum.Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    ALERT = "alert"
    REMINDER = "reminder"
    SOLD = "sold"


class Skin(Base):
    __tablename__ = "skins"
    __table_args__ = (
        UniqueConstraint("user_id", "asset_id", name="uq_skins_user_asset"),
        Index("idx_skins_user_id", "user_id"),
        Index("idx_skins_market_hash_name", "market_hash_name"),
        Index("idx_skins_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    market_hash_name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    float_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 9), nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    purchase_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_price_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[SkinStatus] = mapped_column(
        SAEnum(SkinStatus, name="skin_status", create_type=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default="passive",
    )
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="skins")  # type: ignore[name-defined]
    alert_logs: Mapped[list["AlertLog"]] = relationship(  # type: ignore[name-defined]
        back_populates="skin"
    )
