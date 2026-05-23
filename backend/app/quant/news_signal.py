"""News-signal accessor for the news-sentiment-momentum strategy.

Reads the dashboard's existing `news_articles` table (Phase 3). Extracts
ticker mentions from article title+summary by case-insensitive
word-boundary regex against the supplied symbol list.
"""

from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import select

from app.database import get_engine, news_articles


def _load_articles(start: str, end: str) -> pd.DataFrame:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(news_articles).where(
                (news_articles.c.published_at >= start)
                & (news_articles.c.published_at < end + "T23:59:59Z")
            )
        ).all()
    if not rows:
        return pd.DataFrame(columns=["id", "title", "summary", "published_at"])
    return pd.DataFrame([{
        "id": r.id,
        "title": (r.title or "").upper(),
        "summary": (r.summary or "").upper(),
        "published_at": r.published_at,
    } for r in rows])


def _date_of(published_at: str) -> str:
    return (published_at or "")[:10]


def news_coverage_matrix(
    *, symbols: list[str], start: str, end: str,
) -> pd.DataFrame:
    """Rows = date (ISO yyyy-mm-dd), columns = symbol, values = #articles mentioning."""
    arts = _load_articles(start, end)
    idx = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame(0, index=idx, columns=symbols)
    if arts.empty:
        return df

    arts["date"] = arts["published_at"].map(_date_of)
    arts["text"] = arts["title"] + " " + arts["summary"]

    for sym in symbols:
        pat = re.compile(rf"\b{re.escape(sym.upper())}\b")
        mask = arts["text"].map(lambda t: bool(pat.search(t)))
        sub = arts.loc[mask, ["date"]]
        counts = sub.groupby("date").size().to_dict()
        for d, n in counts.items():
            if d in df.index:
                df.loc[d, sym] = int(n)
    return df


def top_news_universe(
    *, candidate_symbols: list[str], as_of: str,
    lookback_days: int = 7, top_n: int = 100,
) -> list[str]:
    """Return the `top_n` symbols by rolling article count over the last
    `lookback_days` ending at `as_of` (ISO date)."""
    start = (
        pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")
    cov = news_coverage_matrix(symbols=candidate_symbols, start=start, end=as_of)
    if cov.empty:
        return candidate_symbols[:top_n]
    totals = cov.sum(axis=0).sort_values(ascending=False)
    return totals.head(top_n).index.tolist()
