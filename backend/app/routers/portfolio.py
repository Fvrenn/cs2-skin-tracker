from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.price_history import PriceHistory, PriceSource
from app.models.skin import Skin, SkinStatus
from app.models.user import User
from app.schemas.portfolio import PortfolioHistoryPoint, PortfolioSummary
from app.services.prices import get_last_prices

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _to_eur(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


@router.get("/summary", response_model=PortfolioSummary)
async def portfolio_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioSummary:
    result = await db.execute(
        select(Skin).where(Skin.user_id == user.id, Skin.status != SkinStatus.SOLD)
    )
    skins = list(result.scalars().all())

    status_counts: dict[str, int] = {}
    for skin in skins:
        key = skin.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    if not skins:
        return PortfolioSummary(
            total_current_value_cents=0,
            total_current_value_eur=0.0,
            total_purchase_value_cents=None,
            total_purchase_value_eur=None,
            total_pnl_cents=None,
            total_pnl_eur=None,
            total_pnl_percent=None,
            skin_count_by_status=status_counts,
        )

    names = list({s.market_hash_name for s in skins})
    last_prices = await get_last_prices(db, names)

    total_current = sum(last_prices.get(s.market_hash_name, 0) for s in skins)

    skins_with_price = [s for s in skins if s.purchase_price is not None]
    if skins_with_price:
        total_purchase = sum(int(s.purchase_price) for s in skins_with_price)  # type: ignore[arg-type]
        total_pnl = total_current - total_purchase
        pnl_percent = round(total_pnl / total_purchase, 4) if total_purchase > 0 else None
    else:
        total_purchase = None
        total_pnl = None
        pnl_percent = None

    return PortfolioSummary(
        total_current_value_cents=total_current,
        total_current_value_eur=round(total_current / 100, 2),
        total_purchase_value_cents=total_purchase,
        total_purchase_value_eur=_to_eur(total_purchase),
        total_pnl_cents=total_pnl,
        total_pnl_eur=_to_eur(total_pnl),
        total_pnl_percent=pnl_percent,
        skin_count_by_status=status_counts,
    )


@router.get("/history", response_model=list[PortfolioHistoryPoint])
async def portfolio_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioHistoryPoint]:
    day_col = func.date_trunc("day", PriceHistory.recorded_at).label("day")

    result = await db.execute(
        select(day_col, func.sum(PriceHistory.price_median).label("portfolio_value"))
        .select_from(Skin)
        .join(
            PriceHistory,
            (Skin.market_hash_name == PriceHistory.market_hash_name)
            & (PriceHistory.source == PriceSource.CSFLOAT),
        )
        .where(Skin.user_id == user.id, Skin.status != SkinStatus.SOLD)
        .group_by(day_col)
        .order_by(day_col)
    )

    return [
        PortfolioHistoryPoint(
            day=row.day.date(),
            value_cents=int(row.portfolio_value),
            value_eur=round(int(row.portfolio_value) / 100, 2),
        )
        for row in result
        if row.portfolio_value is not None
    ]
