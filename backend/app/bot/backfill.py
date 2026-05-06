import asyncio
import logging
from datetime import date, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.price_history import PriceHistory, PriceSource
from app.models.skin import Skin
from app.services.steam import SteamAuthError, SteamError, steam_client

logger = logging.getLogger(__name__)

_RATE_LIMIT_DELAY = 3.0  # secondes entre chaque appel Steam (rate limit strict)
_BATCH_SIZE = 200  # 200 lignes × 8 colonnes = 1 600 params, bien sous la limite asyncpg (32 767)


async def backfill_skin(market_hash_name: str, db: AsyncSession) -> int:
    """
    Fetches Steam price history for one skin and bulk-inserts into price_history.
    Duplicates are silently skipped via ON CONFLICT DO NOTHING on the unique index
    (market_hash_name, source, recorded_at).
    Returns the number of rows actually inserted (0 if all were duplicates or on error).
    """
    if not settings.STEAM_LOGIN_SECURE:
        logger.warning(
            "Cookie Steam non configuré, backfill ignoré pour %r", market_hash_name
        )
        return 0

    try:
        points = await steam_client.get_price_history(market_hash_name)
    except SteamAuthError:
        logger.error(
            "Backfill ignoré pour %r — STEAM_LOGIN_SECURE absent ou expiré",
            market_hash_name,
        )
        return 0
    except SteamError as exc:
        logger.error("Backfill échoué pour %r : %s", market_hash_name, exc)
        return 0

    if not points:
        logger.debug("Aucun historique Steam pour %r", market_hash_name)
        return 0

    raw_count = len(points)
    seen_dates: set[date] = set()
    filtered = []
    for point in points:
        day = point.recorded_at.date()
        if day not in seen_dates:
            seen_dates.add(day)
            filtered.append(point)
    points = filtered
    logger.info(
        "Backfill %r — filtre journalier : %d → %d points",
        market_hash_name,
        raw_count,
        len(points),
    )

    rows = [
        {
            "market_hash_name": market_hash_name,
            "source": PriceSource.STEAM,
            "price_median": point.price_median,
            "price_min": None,
            "price_max": None,
            "price_mean": None,
            "volume": point.volume,
            # parse_steam_date retourne un datetime naif (UTC) — on rend explicite
            "recorded_at": point.recorded_at.replace(tzinfo=timezone.utc),
        }
        for point in points
    ]

    inserted = 0
    for i in range(0, len(rows), _BATCH_SIZE):
        batch = rows[i : i + _BATCH_SIZE]
        stmt = (
            pg_insert(PriceHistory)
            .values(batch)
            .on_conflict_do_nothing(constraint="idx_price_history_unique")
        )
        result = await db.execute(stmt)
        inserted += result.rowcount
    await db.commit()

    logger.info(
        "Backfill %r — %d/%d points insérés (%d batch(es))",
        market_hash_name,
        inserted,
        len(rows),
        -(-len(rows) // _BATCH_SIZE),  # ceil division
    )
    return inserted


async def backfill_all_skins(db: AsyncSession) -> None:
    """
    Backfills Steam price history for every distinct market_hash_name in the skins table.
    Waits 3 seconds between calls to respect Steam's strict rate limit.
    """
    result = await db.execute(select(Skin.market_hash_name).distinct())
    names: list[str] = list(result.scalars().all())

    if not names:
        logger.info("Aucun skin en BDD — backfill ignoré")
        return

    logger.info("Démarrage du backfill pour %d skin(s) distinct(s)", len(names))
    total_inserted = 0

    for i, name in enumerate(names):
        total_inserted += await backfill_skin(name, db)
        if i < len(names) - 1:
            await asyncio.sleep(_RATE_LIMIT_DELAY)

    logger.info(
        "Backfill terminé — %d points insérés au total sur %d skin(s)",
        total_inserted,
        len(names),
    )


async def run_backfill() -> None:
    """
    Standalone async entry point. Creates its own DB session.
    Usage : python -m app.bot.backfill
    """
    async with AsyncSessionLocal() as db:
        await backfill_all_skins(db)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(run_backfill())
