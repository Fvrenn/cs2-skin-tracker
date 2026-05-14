import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.backfill import backfill_skins
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

# Items filtrés par défaut : cosmétiques sans valeur de revente significative
_LOW_VALUE_KEYWORDS: list[str] = [
    "Graffiti",
    "Sealed Graffiti",
    "Medal",
    "Coin",
    "Badge",
    "Pin",
    "Trophy",
    "Music Kit",
]


def _to_eur(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


def _skin_to_summary(skin: Skin, last_price: int | None) -> SkinSummary:
    return SkinSummary(
        id=skin.id,
        market_hash_name=skin.market_hash_name,
        asset_id=skin.asset_id,
        icon_url=skin.icon_url,
        float_value=float(skin.float_value) if skin.float_value is not None else None,
        rarity=skin.rarity,
        status=skin.status,
        purchase_price_cents=skin.purchase_price,
        purchase_price_eur=_to_eur(skin.purchase_price),
        last_price_cents=last_price,
        last_price_eur=_to_eur(last_price),
        peak_price_cents=skin.peak_price,
        peak_price_eur=_to_eur(skin.peak_price),
        peak_price_at=skin.peak_price_at,
        created_at=skin.created_at,
    )


@router.get("", response_model=list[SkinSummary])
async def list_skins(
    filter_low_value: bool = True,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SkinSummary]:
    where_clauses = [Skin.user_id == user.id, Skin.status != SkinStatus.SOLD]

    if filter_low_value:
        where_clauses.append(
            ~or_(*(Skin.market_hash_name.ilike(f"%{kw}%") for kw in _LOW_VALUE_KEYWORDS))
        )

    result = await db.execute(
        select(Skin).where(*where_clauses).order_by(Skin.created_at.desc())
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

    trunc_unit = "hour" if days <= 30 else "day"
    bucket_expr = func.date_trunc(trunc_unit, PriceHistory.recorded_at)

    where_clauses = [PriceHistory.market_hash_name == skin.market_hash_name]
    if days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        where_clauses.append(PriceHistory.recorded_at > cutoff)

    # Step 1 — avg per (bucket, source) — hourly ≤ 30j, daily > 30j
    per_source_subq = (
        select(
            bucket_expr.label("bucket"),
            PriceHistory.source,
            func.avg(PriceHistory.price_median).label("avg_price"),
        )
        .where(*where_clauses)
        .group_by(bucket_expr, PriceHistory.source)
        .subquery()
    )

    # Step 2 — rank sources within each bucket: csfloat=1 > skinport=2 > steam=3
    source_rank = case(
        (per_source_subq.c.source == PriceSource.CSFLOAT, 1),
        (per_source_subq.c.source == PriceSource.SKINPORT, 2),
        else_=3,
    )
    ranked_subq = (
        select(
            per_source_subq.c.bucket.label("hour"),
            per_source_subq.c.avg_price,
            func.row_number()
            .over(
                partition_by=per_source_subq.c.bucket,
                order_by=source_rank,
            )
            .label("rn"),
        )
        .subquery()
    )

    # Step 3 — keep best source per bucket
    history_result = await db.execute(
        select(ranked_subq.c.hour, ranked_subq.c.avg_price)
        .where(ranked_subq.c.rn == 1)
        .order_by(ranked_subq.c.hour)
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
    existing_by_asset: dict[str, Skin] = {}
    if asset_ids:
        existing_result = await db.execute(
            select(Skin).where(
                Skin.user_id == user.id,
                Skin.asset_id.in_(asset_ids),
            )
        )
        existing_by_asset = {
            s.asset_id: s for s in existing_result.scalars().all() if s.asset_id
        }

    imported = 0
    new_names: list[str] = []
    for item in items:
        icon = item.icon_url or None
        if item.asset_id in existing_by_asset:
            skin = existing_by_asset[item.asset_id]
            skin.icon_url = icon
            skin.float_value = item.float_value
            skin.rarity = item.rarity
        else:
            db.add(Skin(
                user_id=user.id,
                market_hash_name=item.market_hash_name,
                asset_id=item.asset_id,
                icon_url=icon,
                float_value=item.float_value,
                rarity=item.rarity,
            ))
            new_names.append(item.market_hash_name)
            imported += 1

    await db.commit()

    names_to_backfill: list[str] = []
    if new_names:
        # Parmi les nouveaux skins, garder uniquement ceux sans aucun point Steam en BDD
        distinct_new = list(dict.fromkeys(new_names))  # dédoublonner, ordre stable
        existing_steam = await db.execute(
            select(PriceHistory.market_hash_name)
            .where(
                PriceHistory.market_hash_name.in_(distinct_new),
                PriceHistory.source == PriceSource.STEAM,
            )
            .distinct()
        )
        names_with_history: set[str] = set(existing_steam.scalars().all())
        names_to_backfill = [n for n in distinct_new if n not in names_with_history]
        if names_to_backfill:
            asyncio.create_task(backfill_skins(names_to_backfill))

    return SyncResult(
        synced=len(items),
        new_skins=imported,
        backfill_started=bool(names_to_backfill),
        backfill_count=len(names_to_backfill),
    )
