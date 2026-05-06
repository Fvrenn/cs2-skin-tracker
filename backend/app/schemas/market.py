from pydantic import BaseModel


class MarketSearchResult(BaseModel):
    market_hash_name: str
    # Prix live CSFloat (listing buy-now le moins cher)
    csfloat_price_cents: int | None
    csfloat_price_eur: float | None
    # Stats marché Skinport (médiane / min / max)
    skinport_median_cents: int | None
    skinport_median_eur: float | None
    skinport_min_cents: int | None
    skinport_min_eur: float | None
    skinport_max_cents: int | None
    skinport_max_eur: float | None
    skinport_quantity: int
