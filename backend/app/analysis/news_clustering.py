"""Pure analysis functions for clustering news articles. No I/O."""
import math
import re

# Cosine-similarity threshold above which two articles are the same story.
SIMILARITY_THRESHOLD = 0.60

_NORM_RE = re.compile(r"[^a-z0-9]+")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors. 0.0 when either is
    empty, mismatched in length, or zero-magnitude."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def cluster_articles(vectors: list[list[float]],
                     threshold: float = SIMILARITY_THRESHOLD
                     ) -> list[list[int]]:
    """Greedy single-link clustering of article embedding vectors.

    Returns a list of clusters, each a list of indices into `vectors`.
    Each article joins the existing cluster with the highest member
    similarity at or above `threshold`; otherwise it starts a new cluster.
    Input order is preserved — pass articles oldest-first for stable output.
    """
    clusters: list[list[int]] = []
    for i, vec in enumerate(vectors):
        best_cluster: list[int] | None = None
        best_sim = 0.0
        for cluster in clusters:
            sim = max(cosine_similarity(vec, vectors[j]) for j in cluster)
            if sim >= threshold and sim > best_sim:
                best_sim = sim
                best_cluster = cluster
        if best_cluster is None:
            clusters.append([i])
        else:
            best_cluster.append(i)
    return clusters


def normalize_title(title: str) -> str:
    """Lowercase and collapse non-alphanumerics — for fallback grouping."""
    return _NORM_RE.sub(" ", title.lower()).strip()


def cluster_by_title(titles: list[str]) -> list[list[int]]:
    """Fallback clustering: group articles by normalized-title equality.
    Used when embeddings are unavailable."""
    groups: dict[str, list[int]] = {}
    order: list[str] = []
    for i, title in enumerate(titles):
        key = normalize_title(title)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(i)
    return [groups[k] for k in order]


def pick_representative(published_ats: list[str]) -> int:
    """Index of the earliest-published article — the one that broke the
    story. 0 for an empty list."""
    if not published_ats:
        return 0
    return min(range(len(published_ats)),
               key=lambda i: published_ats[i])
