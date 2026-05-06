from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.skin import SkinStatus


class PriceHistoryPoint(BaseModel):
    hour: datetime
    avg_price_cents: int
    avg_price_eur: float


class SkinSummary(BaseModel):
    id: UUID
    market_hash_name: str
    asset_id: str | None
    status: SkinStatus
    purchase_price_cents: int | None
    purchase_price_eur: float | None
    last_price_cents: int | None
    last_price_eur: float | None
    peak_price_cents: int | None
    peak_price_eur: float | None
    created_at: datetime


class SkinDetail(SkinSummary):
    price_history: list[PriceHistoryPoint]


class PurchasePriceRequest(BaseModel):
    purchase_price: int  # en centimes


class SyncResult(BaseModel):
    imported: int
    message: str
