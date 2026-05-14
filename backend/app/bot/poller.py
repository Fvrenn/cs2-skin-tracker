import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory, PriceSource
from app.services.csfloat import CSFloatError, csfloat_client
from app.services.skinport import SkinportError, SkinportItemStats, skinport_client

logger = logging.getLogger(__name__)

_INTER_SKIN_DELAY = 3.0  # seconds between each skin — 150 skins ≈ 7.5 min < 10 min budget


async def _fetch_csfloat(name: str) -> int | None:
    """Returns the lowest CSFloat buy-now listing price in cents, or None."""
    try:
        return await csfloat_client.get_listings(name)
    except CSFloatError as exc:
        logger.warning("CSFloat fetch failed for %r: %s", name, exc)
        return None


async def poll_skin_prices(
    market_hash_names: list[str],
    db: AsyncSession,
    *,
    with_csfloat: bool = True,
) -> None:
    """
    Polls live prices for the given skins and inserts rows into price_history
    with ON CONFLICT DO NOTHING.

    Skinport's /items endpoint is bulk-fetched once for all skins.
    CSFloat is called per skin only when with_csfloat=True (tier 1).
    """
    if not market_hash_names:
        return

    now = datetime.now(timezone.utc)

    # ── Skinport — bulk fetch once for all skins ──────────────────────────────
    logger.info(
        "Fetching Skinport catalog for %d skin(s) (csfloat=%s)…",
        len(market_hash_names),
        with_csfloat,
    )
    try:
        sp_stats = await skinport_client.get_item_stats(market_hash_names)
    except SkinportError as exc:
        logger.warning("Skinport bulk fetch failed: %s — skipping Skinport data", exc)
        sp_stats = {}

    # ── Per-skin loop ─────────────────────────────────────────────────────────
    for i, name in enumerate(market_hash_names):
        cf_price: int | None = None
        if with_csfloat:
            cf_price = await _fetch_csfloat(name)

        sp_stat: SkinportItemStats | None = sp_stats.get(name)

        rows: list[dict[str, object]] = []

        if cf_price is not None:
            rows.append({
                "market_hash_name": name,
                "source": PriceSource.CSFLOAT,
                "price_median": None,
                "price_min": cf_price,
                "price_max": None,
                "price_mean": None,
                "volume": None,
                "recorded_at": now,
            })

        if sp_stat is not None:
            rows.append({
                "market_hash_name": name,
                "source": PriceSource.SKINPORT,
                "price_median": sp_stat.median_cents,
                "price_min": sp_stat.min_cents,
                "price_max": sp_stat.max_cents,
                "price_mean": None,
                "volume": sp_stat.quantity,
                "recorded_at": now,
            })

        if rows:
            stmt = (
                pg_insert(PriceHistory)
                .values(rows)
                .on_conflict_do_nothing(constraint="idx_price_history_unique")
            )
            await db.execute(stmt)
            await db.commit()

        logger.info(
            "Polled %r — CSFloat: %s | Skinport: %s",
            name,
            f"{cf_price / 100:.2f} €" if cf_price is not None else "—",
            (
                f"{sp_stat.median_cents / 100:.2f} €"
                if sp_stat and sp_stat.median_cents is not None
                else "—"
            ),
        )

        if i < len(market_hash_names) - 1:
            await asyncio.sleep(_INTER_SKIN_DELAY)
