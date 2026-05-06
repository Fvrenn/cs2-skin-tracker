from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory, PriceSource


async def get_last_prices(
    db: AsyncSession,
    market_hash_names: list[str],
) -> dict[str, int]:
    """
    Returns {market_hash_name: price_median_cents} using the most recent price
    from the highest-priority source available per skin: csfloat > skinport > steam.
    Uses ROW_NUMBER() to pick one row per skin in a single query.
    Names with no price data in any source are absent from the result.
    """
    if not market_hash_names:
        return {}

    source_priority = case(
        (PriceHistory.source == PriceSource.CSFLOAT, 1),
        (PriceHistory.source == PriceSource.SKINPORT, 2),
        (PriceHistory.source == PriceSource.STEAM, 3),
        else_=4,
    )

    row_num = func.row_number().over(
        partition_by=PriceHistory.market_hash_name,
        order_by=[source_priority, PriceHistory.recorded_at.desc()],
    ).label("rn")

    subq = (
        select(
            PriceHistory.market_hash_name,
            PriceHistory.price_median,
            row_num,
        )
        .where(PriceHistory.market_hash_name.in_(market_hash_names))
        .subquery()
    )

    result = await db.execute(
        select(subq.c.market_hash_name, subq.c.price_median)
        .where(subq.c.rn == 1, subq.c.price_median.is_not(None))
    )

    return {row.market_hash_name: row.price_median for row in result}
