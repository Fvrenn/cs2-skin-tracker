from datetime import date

from pydantic import BaseModel


class PortfolioSummary(BaseModel):
    total_current_value_cents: int
    total_current_value_eur: float
    total_purchase_value_cents: int | None
    total_purchase_value_eur: float | None
    total_pnl_cents: int | None
    total_pnl_eur: float | None
    total_pnl_percent: float | None  # ex: 0.25 = +25%
    skin_count_by_status: dict[str, int]


class PortfolioHistoryPoint(BaseModel):
    day: date
    value_cents: int
    value_eur: float
