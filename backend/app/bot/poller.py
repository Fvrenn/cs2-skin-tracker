import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import PriceHistory, PriceSource
from app.services.csfloat import CSFloatError, csfloat_client
from app.services.skinport import SkinportError, SkinportItemStats, skinport_client

logger = logging.getLogger(__name__)

_INTER_SKIN_DELAY = 1.0  # seconds between each skin


async def _fetch_csfloat(name: str) -> int | None:
    """Returns the lowest CSFloat buy-now listing price in cents, or None."""
    try:
        return await csfloat_client.get_listings(name)
    except CSFloatError as exc:
        logger.warning("CSFloat fetch failed for %r: %s", name, exc)
        return None


async def _lookup_skinport(
    sp_stats: dict[str, SkinportItemStats], name: str
) -> SkinportItemStats | None:
    # Skinport data was bulk-fetched upfront; this coroutine is a dict lookup.
    # Kept as a coroutine so asyncio.gather stays symmetric with CSFloat.
    return sp_stats.get(name)


async def poll_skin_prices(
    market_hash_names: list[str], db: AsyncSession
) -> None:
    """
    Polls live prices for every skin in market_hash_names and inserts them into
    price_history with ON CONFLICT DO NOTHING.

    Skinport's /items endpoint returns the full catalog in one call — it is
    fetched once upfront to stay within the 8 req/5 min rate limit.
    CSFloat is called per skin. 1 second delay between skins.
    """
    if not market_hash_names:
        return

    now = datetime.now(timezone.utc)

    # ── Skinport — bulk fetch once for all skins ──────────────────────────────
    logger.info("Fetching Skinport catalog for %d skin(s)…", len(market_hash_names))
    try:
        sp_stats = await skinport_client.get_item_stats(market_hash_names)
    except SkinportError as exc:
        logger.warning("Skinport bulk fetch failed: %s — skipping Skinport data", exc)
        sp_stats = {}

    # ── Per-skin: CSFloat (real async I/O) + Skinport (dict lookup) ──────────
    for i, name in enumerate(market_hash_names):
        cf_price, sp_stat = await asyncio.gather(
            _fetch_csfloat(name),
            _lookup_skinport(sp_stats, name),
        )

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
