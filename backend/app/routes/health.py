import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database import get_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe — never touches the database or external APIs."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    """Readiness probe — verifies the database is reachable.

    Used to confirm DB wiring after a deploy. Deliberately NOT the Fly
    health check: a transient database blip must not kill the machine.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("readiness check failed: %s", e)
        raise HTTPException(status_code=503, detail="database unavailable") from e
    return {"status": "ok", "database": "ok"}
