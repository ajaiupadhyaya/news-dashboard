from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.cache import cache
from app.services import news_service

router = APIRouter(prefix="/api/news", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    """Cached so the frontend never blocks on the news pipeline."""
    return cache.get_or_compute("news:overview",
                                news_service.build_overview)


@router.get("/story/{cluster_id}")
def story(cluster_id: str):
    key = f"news:story:{cluster_id}"
    result = cache.get_or_compute(
        key, lambda: news_service.build_story(cluster_id))
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"No story for {cluster_id}")
    return result
