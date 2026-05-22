"""Local ONNX text-embedding service (fastembed). The model loads lazily
and is reused; clustering runs only in the scheduler, so the one-time
load never touches the request path."""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
# Cache the model weights under the backend directory so the same path is
# used at container-build time (pre-download) and at runtime.
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".fastembed"

_model = None


def _get_model():
    """Load the fastembed model once, then reuse it."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _model = TextEmbedding(model_name=_MODEL_NAME,
                               cache_dir=str(_CACHE_DIR))
    return _model


def warm_model() -> None:
    """Load (downloading on first run) the embedding model. Called at
    container-build time so the running container needs no network."""
    _get_model()


def embed(texts: list[str]) -> list[list[float]]:
    """Embed `texts` into vectors. Returns [] on any failure — the caller
    (clustering) falls back to a title-based grouping."""
    if not texts:
        return []
    try:
        model = _get_model()
        return [[float(x) for x in vec] for vec in model.embed(texts)]
    except Exception as exc:        # noqa: BLE001 — degrade gracefully
        logger.warning("embedding failed: %s", exc)
        return []
