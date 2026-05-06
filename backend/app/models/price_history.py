import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceSource(str, enum.Enum):
    CSFLOAT = "csfloat"
    SKINPORT = "skinport"
    STEAM = "steam"


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        Index("idx_price_history_lookup", "market_hash_name", "source", "recorded_at"),
        UniqueConstraint(
            "market_hash_name", "source", "recorded_at", name="idx_price_history_unique"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_hash_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[PriceSource] = mapped_column(
        SAEnum(PriceSource, name="price_source", create_type=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    price_median: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_mean: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
