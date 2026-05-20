import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.cache import cache
from app.config import get_settings
from app.services import finance_service

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def warm_overview() -> None:
    """Recompute the Finance overview and store it in the cache."""
    try:
        cache.set("finance:overview", finance_service.build_overview())
        logger.info("warmed finance:overview")
    except Exception as e:
        logger.warning("warm_overview failed: %s", e)


def start_scheduler() -> BackgroundScheduler | None:
    """Start background jobs when SCHEDULER_ENABLED=true; otherwise no-op."""
    global _scheduler
    if not get_settings().scheduler_enabled:
        logger.info("scheduler disabled (set SCHEDULER_ENABLED=true to enable)")
        return None
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(warm_overview, "interval", minutes=10, id="warm_overview",
                  max_instances=1, coalesce=True)
    sched.start()
    _scheduler = sched
    logger.info("scheduler started")
    return sched


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
