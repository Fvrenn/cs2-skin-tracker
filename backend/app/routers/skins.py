import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.price_history import PriceHistory, PriceSource
from app.models.skin import Skin, SkinStatus
from app.models.user import User
from app.schemas.skin import (
    PriceHistoryPoint,
    PurchasePriceRequest,
    SkinDetail,
    SkinSummary,
    SyncResult,
)
from app.services.prices import get_last_prices
from app.services.steam import SteamError, SteamPrivateInventoryError, steam_client

router = APIRouter(prefix="/skins", tags=["skins"])


def _to_eur(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


def _skin_to_summary(skin: Skin, last_price: int | None) -> SkinSummary:
    return SkinSummary(
        id=skin.id,
        market_hash_name=skin.market_hash_name,
        asset_id=skin.asset_id,
        status=skin.status,
        purchase_price_cents=skin.purchase_price,
        purchase_price_eur=_to_eur(skin.purchase_price),
        last_price_cents=last_price,
        last_price_eur=_to_eur(last_price),
        peak_price_cents=skin.peak_price,
        peak_price_eur=_to_eur(skin.peak_price),
        created_at=skin.created_at,
    )


@router.get("", response_model=list[SkinSummary])
async def list_skins(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkinSummary]:
    result = await db.execute(
        select(Skin)
        .where(Skin.user_id == user.id, Skin.status != SkinStatus.SOLD)
        .order_by(Skin.created_at.desc())
    )
    skins = list(result.scalars().all())
    if not skins:
        return []

    names = list({s.market_hash_name for s in skins})
    last_prices = await get_last_prices(db, names)

    return [_skin_to_summary(s, last_prices.get(s.market_hash_name)) for s in skins]


@router.get("/{skin_id}", response_model=SkinDetail)
async def get_skin(
    skin_id: uuid.UUID,
    days: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkinDetail:
    skin = await db.get(Skin, skin_id)
    if skin is None or skin.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skin introuvable")

    last_prices = await get_last_prices(db, [skin.market_hash_name])
    last_price = last_prices.get(skin.market_hash_name)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    hour_col = func.date_trunc("hour", PriceHistory.recorded_at).label("hour")

    history_result = await db.execute(
        select(hour_col, func.avg(PriceHistory.price_median).label("avg_price"))
        .where(
            PriceHistory.market_hash_name == skin.market_hash_name,
            PriceHistory.source == PriceSource.CSFLOAT,
            PriceHistory.recorded_at > cutoff,
        )
        .group_by(hour_col)
        .order_by(hour_col)
    )

    history = [
        PriceHistoryPoint(
            hour=row.hour,
            avg_price_cents=round(float(row.avg_price)),
            avg_price_eur=round(float(row.avg_price) / 100, 2),
        )
        for row in history_result
        if row.avg_price is not None
    ]

    return SkinDetail(**_skin_to_summary(skin, last_price).model_dump(), price_history=history)


@router.post("/{skin_id}/purchase-price", response_model=SkinSummary)
async def set_purchase_price(
    skin_id: uuid.UUID,
    body: PurchasePriceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SkinSummary:
    skin = await db.get(Skin, skin_id)
    if skin is None or skin.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skin introuvable")

    skin.purchase_price = body.purchase_price
    await db.commit()
    await db.refresh(skin)

    last_prices = await get_last_prices(db, [skin.market_hash_name])
    return _skin_to_summary(skin, last_prices.get(skin.market_hash_name))


@router.post("/sync", response_model=SyncResult)
async def sync_inventory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResult:
    if not user.steam_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Steam ID non configuré — mets-le à jour dans /settings",
        )

    try:
        items = await steam_client.get_inventory(user.steam_id)
    except SteamPrivateInventoryError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventaire Steam privé — rends-le public sur ton profil Steam",
        )
    except SteamError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    asset_ids = [item.asset_id for item in items if item.asset_id]
    existing_ids: set[str] = set()
    if asset_ids:
        existing_result = await db.execute(
            select(Skin.asset_id).where(
                Skin.user_id == user.id,
                Skin.asset_id.in_(asset_ids),
            )
        )
        existing_ids = set(existing_result.scalars().all())

    imported = 0
    for item in items:
        if item.asset_id in existing_ids:
            continue
        db.add(Skin(
            user_id=user.id,
            market_hash_name=item.market_hash_name,
            asset_id=item.asset_id,
        ))
        imported += 1

    await db.commit()
    return SyncResult(imported=imported, message=f"{imported} skin(s) importé(s) depuis Steam")
