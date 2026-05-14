from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory, PriceSource


async def get_last_prices(
    db: AsyncSession,
    market_hash_names: list[str],
) -> dict[str, int]:
    """
    Returns {market_hash_name: price_cents} using the most recent price from the
    highest-priority source per skin:
      1. skinport → price_median (median des ventes réelles, plus fiable)
      2. csfloat  → price_min   (lowest live buy-now listing, fallback)
      3. steam    → price_median (dernier recours)

    Uses ROW_NUMBER() to pick one row per skin in a single query.
    Skins with no usable price in any source are absent from the result.
    """
    if not market_hash_names:
        return {}

    source_priority = case(
        (PriceHistory.source == PriceSource.SKINPORT, 1),
        (PriceHistory.source == PriceSource.CSFLOAT, 2),
        (PriceHistory.source == PriceSource.STEAM, 3),
        else_=4,
    )

    # Source-aware price: CSFloat stores the sell price in price_min; others use price_median.
    effective_price = case(
        (PriceHistory.source == PriceSource.CSFLOAT, PriceHistory.price_min),
        else_=PriceHistory.price_median,
    ).label("effective_price")

    row_num = func.row_number().over(
        partition_by=PriceHistory.market_hash_name,
        order_by=[source_priority, PriceHistory.recorded_at.desc()],
    ).label("rn")

    subq = (
        select(
            PriceHistory.market_hash_name,
            effective_price,
            row_num,
        )
        .where(PriceHistory.market_hash_name.in_(market_hash_names))
        .subquery()
    )

    result = await db.execute(
        select(subq.c.market_hash_name, subq.c.effective_price)
        .where(subq.c.rn == 1, subq.c.effective_price.is_not(None))
    )

    return {row.market_hash_name: row.effective_price for row in result}
