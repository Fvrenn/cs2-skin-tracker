import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistCreate, WatchlistItem
from app.services.prices import get_last_prices

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _to_eur(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


def _item_to_schema(item: Watchlist, last_price: int | None) -> WatchlistItem:
    return WatchlistItem(
        id=item.id,
        market_hash_name=item.market_hash_name,
        alert_on_drop=item.alert_on_drop,
        drop_threshold=float(item.drop_threshold) if item.drop_threshold is not None else None,
        alert_on_rise=item.alert_on_rise,
        rise_threshold=float(item.rise_threshold) if item.rise_threshold is not None else None,
        last_price_cents=last_price,
        last_price_eur=_to_eur(last_price),
        created_at=item.created_at,
    )


@router.get("", response_model=list[WatchlistItem])
async def list_watchlist(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WatchlistItem]:
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == user.id)
        .order_by(Watchlist.created_at.desc())
    )
    items = list(result.scalars().all())
    if not items:
        return []

    names = [item.market_hash_name for item in items]
    last_prices = await get_last_prices(db, names)

    return [_item_to_schema(item, last_prices.get(item.market_hash_name)) for item in items]


@router.post("", response_model=WatchlistItem, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: WatchlistCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchlistItem:
    existing = await db.scalar(
        select(Watchlist).where(
            Watchlist.user_id == user.id,
            Watchlist.market_hash_name == body.market_hash_name,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce skin est déjà dans ta watchlist",
        )

    item = Watchlist(
        user_id=user.id,
        market_hash_name=body.market_hash_name,
        alert_on_drop=body.alert_on_drop,
        drop_threshold=body.drop_threshold,
        alert_on_rise=body.alert_on_rise,
        rise_threshold=body.rise_threshold,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    last_prices = await get_last_prices(db, [item.market_hash_name])
    return _item_to_schema(item, last_prices.get(item.market_hash_name))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    item_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    item = await db.get(Watchlist, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item watchlist introuvable",
        )
    await db.delete(item)
    await db.commit()
