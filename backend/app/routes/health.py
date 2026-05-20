from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe — never touches the database or external APIs."""
    return {"status": "ok"}
