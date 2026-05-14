"""
Standalone APScheduler process — run via: python -m app.bot.scheduler

Jobs:
  - poll_tier1    : every 5 min  — CSFloat + Skinport, skins with last Skinport price > 10 €
  - poll_tier2    : every 30 min — Skinport only, skins 1 € – 10 €
  - poll_tier3    : every 6h     — Skinport only, skins < 1 € or no price yet
  - backfill_steam: daily at 3 AM — Steam long-term history backfill
"""
import asyncio
import logging
import signal
import time
from typing import Literal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.backfill import backfill_all_skins
from app.bot.poller import poll_skin_prices
from app.database import AsyncSessionLocal
from app.models.price_history import PriceHistory, PriceSource
from app.models.skin import Skin, SkinStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_BACKFILL_HOUR = 3

# Price thresholds (cents) that define tier boundaries
_TIER1_MIN = 1000   # > 10 €  → CSFloat + Skinport every 5 min
_TIER2_MIN = 100    # 1–10 €  → Skinport every 30 min
                    # < 1 € or None → Skinport every 6h


# ── Tier classification ───────────────────────────────────────────────────────

async def _classify_skins(
    db: AsyncSession,
) -> tuple[list[str], list[str], list[str]]:
    """
    Returns (tier1, tier2, tier3) based on each skin's latest Skinport price_median.
    Skins with no Skinport history fall into tier3.
    """
    all_names_result = await db.execute(
        select(Skin.market_hash_name)
        .distinct()
        .where(Skin.status != SkinStatus.SOLD)
    )
    all_names: list[str] = list(all_names_result.scalars().all())

    if not all_names:
        return [], [], []

    # Latest Skinport price_median per name, using row_number to avoid DISTINCT ON
    sp_latest_subq = (
        select(
            PriceHistory.market_hash_name,
            PriceHistory.price_median,
            func.row_number()
            .over(
                partition_by=PriceHistory.market_hash_name,
                order_by=PriceHistory.recorded_at.desc(),
            )
            .label("rn"),
        )
        .where(
            PriceHistory.source == PriceSource.SKINPORT,
            PriceHistory.market_hash_name.in_(all_names),
        )
        .subquery()
    )
    sp_result = await db.execute(
        select(sp_latest_subq.c.market_hash_name, sp_latest_subq.c.price_median)
        .where(sp_latest_subq.c.rn == 1)
    )
    sp_prices: dict[str, int | None] = {
        row.market_hash_name: row.price_median
        for row in sp_result
    }

    tier1: list[str] = []
    tier2: list[str] = []
    tier3: list[str] = []
    for name in all_names:
        price = sp_prices.get(name)
        if price is not None and price > _TIER1_MIN:
            tier1.append(name)
        elif price is not None and price >= _TIER2_MIN:
            tier2.append(name)
        else:
            tier3.append(name)

    return tier1, tier2, tier3


# ── Shared poll runner ────────────────────────────────────────────────────────

async def _poll_tier(*, tier: Literal[1, 2, 3], with_csfloat: bool) -> None:
    t0 = time.monotonic()
    try:
        async with AsyncSessionLocal() as db:
            tier1, tier2, tier3 = await _classify_skins(db)

        names = (tier1, tier2, tier3)[tier - 1]

        if not names:
            logger.info("Poll tier%d — aucun skin dans ce tier", tier)
            return

        logger.info("Poll tier%d démarré — %d skin(s)", tier, len(names))

        async with AsyncSessionLocal() as db:
            await poll_skin_prices(names, db, with_csfloat=with_csfloat)

        elapsed = time.monotonic() - t0
        logger.info("Poll tier%d terminé — %d skin(s) en %.1fs", tier, len(names), elapsed)

    except Exception:
        logger.exception("Erreur non gérée dans poll_tier%d", tier)
        raise


# ── Job wrappers ──────────────────────────────────────────────────────────────

async def _poll_tier1_job() -> None:
    await _poll_tier(tier=1, with_csfloat=True)


async def _poll_tier2_job() -> None:
    await _poll_tier(tier=2, with_csfloat=False)


async def _poll_tier3_job() -> None:
    await _poll_tier(tier=3, with_csfloat=False)


async def _backfill_job() -> None:
    logger.info("Backfill Steam démarré (tâche 3h)")
    try:
        async with AsyncSessionLocal() as db:
            await backfill_all_skins(db)
        logger.info("Backfill Steam terminé")
    except Exception:
        logger.exception("Erreur non gérée dans backfill_steam")
        raise


# ── Startup info ──────────────────────────────────────────────────────────────

async def _log_startup(scheduler: AsyncIOScheduler) -> None:
    async with AsyncSessionLocal() as db:
        tier1, tier2, tier3 = await _classify_skins(db)

    total = len(tier1) + len(tier2) + len(tier3)

    poll_job = scheduler.get_job("poll_tier1")
    next_run = (
        poll_job.next_run_time.strftime("%d/%m %H:%M:%S")
        if poll_job and poll_job.next_run_time
        else "—"
    )
    logger.info(
        "Scheduler opérationnel — %d skin(s) | T1(5min):%d T2(30min):%d T3(6h):%d | Prochain poll T1 : %s",
        total,
        len(tier1),
        len(tier2),
        len(tier3),
        next_run,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_signal() -> None:
        logger.info("Signal d'arrêt reçu — shutdown en cours…")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _on_signal)

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        _poll_tier1_job,
        trigger=IntervalTrigger(minutes=5),
        id="poll_tier1",
        name="Poll T1 — CSFloat + Skinport (> 10 €)",
        max_instances=1,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        _poll_tier2_job,
        trigger=IntervalTrigger(minutes=30),
        id="poll_tier2",
        name="Poll T2 — Skinport (1–10 €)",
        max_instances=1,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        _poll_tier3_job,
        trigger=IntervalTrigger(hours=6),
        id="poll_tier3",
        name="Poll T3 — Skinport (< 1 € ou inconnu)",
        max_instances=1,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _backfill_job,
        trigger=CronTrigger(hour=_BACKFILL_HOUR, minute=0),
        id="backfill_steam",
        name="Backfill Steam historique",
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.start()
    await _log_startup(scheduler)

    await stop_event.wait()

    logger.info("Arrêt du scheduler (jobs en cours laissés se terminer)…")
    scheduler.shutdown(wait=False)
    logger.info("Scheduler arrêté")


if __name__ == "__main__":
    asyncio.run(main())
