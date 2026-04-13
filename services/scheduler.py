import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_sync():
    """Run sync in a new event loop (called from background thread)."""
    from services.sync import sync_all_reviews

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(sync_all_reviews())
        logger.info(f"Scheduled sync complete: {result['new_reviews']} new reviews")
    except Exception as e:
        logger.error(f"Scheduled sync failed: {e}")
    finally:
        loop.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_sync,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="review_sync",
        name="Review Sync",
    )
    _scheduler.start()
    logger.info(f"Scheduler started: syncing every {settings.sync_interval_minutes} minutes")


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
