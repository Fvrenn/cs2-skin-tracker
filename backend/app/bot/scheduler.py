"""
Standalone APScheduler process — run via: python -m app.bot.scheduler

Jobs:
  - poll_prices   : every 5 min — CSFloat + Skinport prices for all active skins
  - backfill_steam: daily at 3 AM — Steam long-term history backfill
"""
import asyncio
import logging
import signal
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select

from app.bot.backfill import backfill_all_skins
from app.bot.poller import poll_skin_prices
from app.database import AsyncSessionLocal
from app.models.skin import Skin, SkinStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_POLL_INTERVAL_MINUTES = 5
_BACKFILL_HOUR = 3


# ── Jobs ──────────────────────────────────────────────────────────────────────

async def _poll_job() -> None:
    t0 = time.monotonic()
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Skin.market_hash_name)
                .distinct()
                .where(Skin.status != SkinStatus.SOLD)
            )
            names: list[str] = list(result.scalars().all())

        if not names:
            logger.info("Poll — aucun skin actif à surveiller")
            return

        logger.info("Poll démarré — %d skin(s) distinct(s)", len(names))

        async with AsyncSessionLocal() as db:
            await poll_skin_prices(names, db)

        elapsed = time.monotonic() - t0
        logger.info("Poll terminé — %d skin(s) en %.1fs", len(names), elapsed)

    except Exception:
        logger.exception("Erreur non gérée dans poll_prices — relance dans %d min", _POLL_INTERVAL_MINUTES)
        raise


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
        row = await db.execute(
            select(func.count()).select_from(
                select(Skin.market_hash_name)
                .distinct()
                .where(Skin.status != SkinStatus.SOLD)
                .subquery()
            )
        )
        skin_count: int = row.scalar_one()

    poll_job = scheduler.get_job("poll_prices")
    next_run = (
        poll_job.next_run_time.strftime("%d/%m %H:%M:%S")
        if poll_job and poll_job.next_run_time
        else "—"
    )
    logger.info(
        "Scheduler opérationnel — %d skin(s) surveillé(s) | Prochain poll : %s",
        skin_count,
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
        _poll_job,
        trigger=IntervalTrigger(minutes=_POLL_INTERVAL_MINUTES),
        id="poll_prices",
        name="Poll CSFloat + Skinport",
        max_instances=1,
        misfire_grace_time=60,
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
