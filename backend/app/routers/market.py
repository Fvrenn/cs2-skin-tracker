from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user
from app.models.user import User
from app.schemas.market import MarketSearchResult
from app.services.csfloat import CSFloatError, csfloat_client
from app.services.skinport import SkinportError, skinport_client

router = APIRouter(prefix="/market", tags=["market"])


def _to_eur(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


@router.get("/search", response_model=MarketSearchResult)
async def market_search(
    q: str = Query(..., min_length=1, description="Nom exact du skin (market_hash_name)"),
    _user: User = Depends(get_current_user),
) -> MarketSearchResult:
    # Skinport valide l'existence du nom et fournit les stats de marché
    try:
        skinport_stats = await skinport_client.get_item_stats([q])
    except SkinportError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    if q not in skinport_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skin non trouvé sur Skinport — vérifie le market_hash_name exact",
        )

    stats = skinport_stats[q]

    # CSFloat fournit le prix live (listing buy-now le moins cher)
    csfloat_price: int | None = None
    try:
        csfloat_price = await csfloat_client.get_listings(q)
    except CSFloatError as exc:
        # Non bloquant : on retourne quand même les stats Skinport
        pass

    return MarketSearchResult(
        market_hash_name=q,
        csfloat_price_cents=csfloat_price,
        csfloat_price_eur=_to_eur(csfloat_price),
        skinport_median_cents=stats.median_cents,
        skinport_median_eur=_to_eur(stats.median_cents),
        skinport_min_cents=stats.min_cents,
        skinport_min_eur=_to_eur(stats.min_cents),
        skinport_max_cents=stats.max_cents,
        skinport_max_eur=_to_eur(stats.max_cents),
        skinport_quantity=stats.quantity,
    )
