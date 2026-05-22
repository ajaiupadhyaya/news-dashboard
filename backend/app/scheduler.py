import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.cache import cache
from app.config import get_settings
from app.services import economics_service, finance_service, news_service

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def warm_overview() -> None:
    """Recompute the Finance overview and store it in the cache."""
    try:
        cache.set("finance:overview", finance_service.build_overview())
        logger.info("warmed finance:overview")
    except Exception:
        logger.warning("warm_overview failed", exc_info=True)


def warm_markets() -> None:
    """Recompute the Finance markets page and store it in the cache."""
    try:
        cache.set("finance:markets", finance_service.build_markets())
        logger.info("warmed finance:markets")
    except Exception:
        logger.warning("warm_markets failed", exc_info=True)


def warm_economics() -> None:
    """Recompute the Economics overview + dashboard and store them in cache."""
    try:
        cache.set("economics:overview", economics_service.build_overview())
    except Exception:
        logger.warning("warm_economics: overview step failed", exc_info=True)
        return
    try:
        cache.set("economics:dashboard", economics_service.build_dashboard())
    except Exception:
        logger.warning("warm_economics: dashboard step failed", exc_info=True)
        return
    logger.info("warmed economics:overview + economics:dashboard")


def warm_news() -> None:
    """Run the news ingestion pipeline and recache the overview."""
    try:
        news_service.refresh_news()
        cache.set("news:overview", news_service.build_overview())
        logger.info("warmed news:overview")
    except Exception:
        logger.warning("warm_news failed", exc_info=True)


def start_scheduler() -> BackgroundScheduler | None:
    """Start background jobs when SCHEDULER_ENABLED=true; otherwise no-op."""
    global _scheduler
    if not get_settings().scheduler_enabled:
        logger.info("scheduler disabled (set SCHEDULER_ENABLED=true to enable)")
        return None
    if _scheduler is not None and _scheduler.running:
        logger.warning("start_scheduler called while already running")
        return _scheduler
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(warm_overview, "interval", minutes=10, id="warm_overview",
                  max_instances=1, coalesce=True)
    sched.add_job(warm_markets, "interval", minutes=10, id="warm_markets",
                  max_instances=1, coalesce=True)
    sched.add_job(warm_economics, "interval", hours=6, id="warm_economics",
                  max_instances=1, coalesce=True)
    sched.add_job(warm_news, "interval", minutes=15, id="warm_news",
                  max_instances=1, coalesce=True)
    sched.start()
    _scheduler = sched
    logger.info("scheduler started")
    return sched


def shutdown_scheduler() -> None:
    """Stop the scheduler if running. Safe to call when not started."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
