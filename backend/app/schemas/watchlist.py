from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WatchlistItem(BaseModel):
    id: UUID
    market_hash_name: str
    alert_on_drop: bool
    drop_threshold: float | None
    alert_on_rise: bool
    rise_threshold: float | None
    last_price_cents: int | None
    last_price_eur: float | None
    created_at: datetime


class WatchlistCreate(BaseModel):
    market_hash_name: str
    alert_on_drop: bool = False
    drop_threshold: float | None = None
    alert_on_rise: bool = False
    rise_threshold: float | None = None
