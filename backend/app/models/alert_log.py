import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, enum.Enum):
    RISE = "rise"
    PEAK_DROP = "peak_drop"
    REMINDER = "reminder"
    WATCHLIST_DROP = "watchlist_drop"
    WATCHLIST_RISE = "watchlist_rise"


class AlertLog(Base):
    __tablename__ = "alert_logs"
    __table_args__ = (
        Index("idx_alert_logs_user_id", "user_id"),
        Index("idx_alert_logs_skin_id", "skin_id"),
        Index("idx_alert_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    skin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skins.id", ondelete="SET NULL"), nullable=True
    )
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("watchlist.id", ondelete="SET NULL"), nullable=True
    )
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(AlertType, name="alert_type", create_type=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    price_at_alert: Mapped[int] = mapped_column(Integer, nullable=False)
    peak_price_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purchase_price_ref: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discord_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    discord_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="alert_logs")  # type: ignore[name-defined]
    skin: Mapped["Skin | None"] = relationship(back_populates="alert_logs")  # type: ignore[name-defined]
    watchlist_item: Mapped["Watchlist | None"] = relationship(back_populates="alert_logs")  # type: ignore[name-defined]
