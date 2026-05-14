"""
One-shot Skinport historical backfill.
Run via: python -m app.bot.backfill_skinport

For each active skin in the DB, fetches /v1/sales/history, groups into 4
cumulative time windows (24h / 7d / 30d / 90d), computes median / min / max /
volume per window, and inserts one price_history row per window.
ON CONFLICT DO NOTHING — safe to re-run.
"""
import asyncio
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.price_history import PriceHistory, PriceSource
from app.models.skin import Skin, SkinStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_SKINPORT_BASE = "https://api.skinport.com/v1"
_INTER_SKIN_DELAY = 2.0  # seconds between skins — Skinport allows 8 req / 5 min on authenticated endpoints

# (label, window cutoff, recorded_at offset)
# recorded_at = now - offset places the point at the start of the window.
_WINDOWS: list[tuple[str, timedelta]] = [
    ("24h", timedelta(hours=24)),
    ("7d",  timedelta(days=7)),
    ("30d", timedelta(days=30)),
    ("90d", timedelta(days=90)),
]


def _to_cents(value: float) -> int:
    return round(value * 100)


def _window_stats(
    sales: list[dict[str, Any]], since: datetime
) -> tuple[int | None, int | None, int | None, int]:
    """Returns (median_cents, min_cents, max_cents, volume) for sales >= since."""
    prices = [
        float(s["price"])
        for s in sales
        if s.get("price") is not None
        and datetime.fromtimestamp(s["created_at"], tz=timezone.utc) >= since
    ]
    if not prices:
        return None, None, None, 0
    return (
        _to_cents(statistics.median(prices)),
        _to_cents(min(prices)),
        _to_cents(max(prices)),
        len(prices),
    )


async def _fetch_sales(client: httpx.AsyncClient, market_hash_name: str) -> list[dict[str, Any]]:
    try:
        response = await client.get(
            "/sales/history",
            params={"app_id": 730, "currency": "EUR", "market_hash_name": market_hash_name},
        )
    except httpx.RequestError as exc:
        logger.warning("Network error for %r: %s", market_hash_name, exc)
        return []

    if response.status_code == 404:
        return []

    if response.status_code == 429:
        logger.warning("Skinport rate limit hit for %r — skipping", market_hash_name)
        return []

    if not response.is_success:
        logger.warning("Skinport status %d for %r", response.status_code, market_hash_name)
        return []

    raw = response.json()
    if not isinstance(raw, list):
        logger.warning("Unexpected /sales/history format for %r: %s", market_hash_name, type(raw).__name__)
        return []

    return raw  # type: ignore[return-value]


async def _backfill_skin(
    client: httpx.AsyncClient,
    name: str,
    now: datetime,
) -> int:
    sales = await _fetch_sales(client, name)
    if not sales:
        return 0

    rows: list[dict[str, object]] = []

    for label, offset in _WINDOWS:
        since = now - offset
        recorded_at = now - offset
        median, price_min, price_max, volume = _window_stats(sales, since)

        if median is None:
            logger.debug("No sales in %s window for %r — skipping point", label, name)
            continue

        rows.append({
            "market_hash_name": name,
            "source": PriceSource.SKINPORT,
            "price_median": median,
            "price_min": price_min,
            "price_max": price_max,
            "price_mean": None,
            "volume": volume,
            "recorded_at": recorded_at,
        })

    if not rows:
        return 0

    async with AsyncSessionLocal() as db:
        stmt = (
            pg_insert(PriceHistory)
            .values(rows)
            .on_conflict_do_nothing(constraint="idx_price_history_unique")
        )
        await db.execute(stmt)
        await db.commit()

    return len(rows)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Skin.market_hash_name)
            .distinct()
            .where(Skin.status != SkinStatus.SOLD)
        )
        names: list[str] = list(result.scalars().all())

    if not names:
        logger.info("Aucun skin actif — rien à backfiller")
        return

    logger.info("Backfill Skinport démarré — %d skin(s)", len(names))

    async with httpx.AsyncClient(
        base_url=_SKINPORT_BASE,
        auth=(settings.SKINPORT_CLIENT_ID, settings.SKINPORT_CLIENT_SECRET),
        headers={"Accept-Encoding": "br"},
        timeout=httpx.Timeout(30.0),
    ) as client:
        now = datetime.now(timezone.utc)
        total = 0

        for i, name in enumerate(names):
            try:
                inserted = await _backfill_skin(client, name, now)
                total += inserted
                logger.info("[%d/%d] %r — %d point(s) insérés", i + 1, len(names), name, inserted)
            except Exception:
                logger.exception("Erreur pour %r — skin ignoré", name)

            if i < len(names) - 1:
                await asyncio.sleep(_INTER_SKIN_DELAY)

    logger.info("Backfill Skinport terminé — %d point(s) total insérés", total)


if __name__ == "__main__":
    asyncio.run(main())
