# News & Markets Dashboard — Phase 3 (News) Design Spec

**Date:** 2026-05-22
**Status:** Approved design — ready for implementation planning
**Working directory:** `~/Documents/news-dashboard`
**Parent spec:** `docs/superpowers/specs/2026-05-20-news-dashboard-design.md` (§6 News, §13)

---

## 1. Purpose

Phase 3 adds the **News domain** end-to-end: a live News overview panel on the
four-quadrant Home (replacing the current "coming soon" placeholder in the
top-left quadrant) and a story drill-down page. It is RSS-backed — supplemented
by a free-tier news API — with semantic clustering of articles into stories, and
mirrors the architecture of the already-shipped, already-live Finance and
Economics domains. Phases 1 and 2 are complete and deployed; Phase 3 is purely
additive.

## 2. Goals & non-goals

**Goals**
- A live News overview panel: a "story momentum" hero visualization + a short,
  clickable list of top stories.
- A story drill-down page: the full story cluster (every source), a development
  timeline, momentum over time, and related stories.
- Cluster articles into de-duplicated, themed stories using semantic embeddings.
- Reuse the existing chart, motion, and design systems; add one new chart type
  (a force-laid-out beeswarm).
- Stay within the project's data budget — free RSS feeds plus a news API run on
  its free tier.
- The frontend never blocks on a feed — everything is pre-computed and cached
  (parent spec's core principle).

**Non-goals**
- Not the AI "why this matters" / summary layer — that is Phase 5. The drill-down
  reserves an empty slot for it, exactly as the Economics drill-down does.
- No global news search box — drill-down "related stories" (via embedding
  similarity) covers the parent spec's "related threads" need for Phase 3.
- Not the Politics domain (Phase 4).
- No paid news API in Phase 3 — the API provider is built as a real code path but
  runs on a free tier; a paid upgrade is a config change, not a code change.

## 3. Decisions made (2026-05-22 brainstorm)

| Decision | Choice |
|---|---|
| Data source | Free RSS feeds (~25 curated outlets) **+** a news API on its free tier. Resolves the parent spec §13 deferred "paid news API" decision: build the provider, run it free, upgrade later if a real gap appears. |
| News API | **NewsData.io** — most generous free tier (200 credits/day, category + country filters, a search endpoint). Behind a mockable provider seam, so it is swappable. |
| Clustering | **Semantic embeddings** — articles grouped into stories by cosine similarity of their embedding vectors. |
| Embeddings engine | **`fastembed`** local ONNX model (`BAAI/bge-small-en-v1.5`, 384-dim, ~130MB), baked into the Docker image at build time. $0/mo, no API key. Clustering runs in the scheduler, so model-load time never touches the UI. |
| Hero visualization | **Momentum field** — a force-laid-out beeswarm of story circles. |
| Overview scope | A single "Top Stories" view — no tabs or category facets. Each story's category is tracked internally and used as a color accent / shown on the drill-down. |

## 4. Architecture

Mirrors the Finance and Economics domains. Core principle unchanged: the frontend
reads only pre-computed, cached data; the scheduler refreshes it in the
background.

**Data flow:** scheduler → `rss_provider` + `news_api_provider` fetch articles →
`embeddings` service vectorizes each article → `news_clustering` groups them into
stories → `news_metrics` computes momentum + ranking → `news_service` assembles →
stored in Postgres (`news_articles`, `news_clusters`) + TTL cache →
`/api/news/*` serves cached → frontend renders.

### 4.1 Backend (`backend/app/`)

- `config.py` — add `NEWS_API_KEY` (env var; blank in dev/tests).
- `providers/rss_provider.py` — fetches and parses ~25 curated RSS feeds via
  `feedparser`. One mockable seam. **Per-feed isolation**: a single failing or
  malformed feed is skipped and logged; the others still return articles.
  Normalizes each entry to a common `Article` shape (title, summary, url, source,
  published-at, category).
- `providers/news_api_provider.py` — NewsData.io HTTP adapter (`httpx`).
  `get_latest()` returns recent articles normalized to the same `Article` shape.
  One mockable seam; returns `[]` on any failure **or when `NEWS_API_KEY` is
  unset**. Its articles flow into the same ingestion pipeline as RSS — it is a
  breadth supplement, not a separate path.
- `services/embeddings.py` — a `fastembed` wrapper exposing `embed(texts)` →
  list of vectors. One mockable seam. The model is loaded once and reused. On
  failure (model unavailable, etc.) it signals the caller so clustering falls
  back gracefully (see §8).
- `analysis/news_clustering.py` — **pure, unit-tested functions** (TDD):
  - cosine similarity between two vectors;
  - greedy single-link clustering: given article vectors within a rolling 48h
    window, group any pair whose similarity exceeds a threshold into the same
    story cluster;
  - representative-article selection for a cluster (the most central / earliest
    salient article that names the story).
- `analysis/news_metrics.py` — **pure, unit-tested functions** (TDD):
  - **momentum score** — coverage velocity: the article count in the most recent
    window relative to the cluster's trailing average rate over the 48h window,
    combined with the distinct-source count;
  - **status bucketing** — `surging` / `steady` / `fading` from the momentum
    score (surging when recent activity clearly exceeds the trailing rate,
    fading when it clearly trails it);
  - freshness (time since the latest article);
  - story ranking for the overview (momentum and source-diversity weighted).
- `services/news_service.py` — orchestration: `build_overview()` (top-ranked
  story clusters + their momentum-field data) and `build_story(cluster_id)` (one
  full cluster with all source articles, timeline, momentum series, related
  clusters).
- `models.py` — add pydantic models: `Article`, `StoryCluster` (overview-level
  story summary), `NewsOverview`, `StoryDetail`, `MomentumPoint`.
- `database.py` — add a `news_articles` table (cached normalized articles) and a
  `news_clusters` table (computed cluster snapshots), mirroring `ohlcv` and
  `econ_series`.
- `routes/news.py` — `GET /api/news/overview` and
  `GET /api/news/story/{cluster_id}`; auth-gated; served via the TTL cache.
- `scheduler.py` — add a `warm_news` job. Interval ~15 min — news moves fast.
- `main.py` — register the news router.
- `requirements.txt` — add `feedparser` and `fastembed`.
- `Dockerfile` — pre-download the `bge-small-en-v1.5` model at build time so the
  running container needs no network access for it.

### 4.2 Frontend (`frontend/src/`)

- `charts/BeeswarmChart.tsx` — a new bespoke chart for the chart system: a
  `d3-force` layout of story circles. Circle **size** = distinct-source count,
  **x-position** = momentum score, **color** = surging / steady / fading.
  Circles settle with spring physics and re-flow smoothly when data refreshes;
  hover tooltip; honors `prefers-reduced-motion` (static layout, no simulation
  animation). Joins the existing `Sparkline`, `CandlestickChart`, and
  `LineChart`. Adds the `d3-force` dependency.
- `news/NewsPanel.tsx` — the overview panel: the beeswarm momentum-field hero
  plus a short, clickable top-stories list below it.
- `news/StoryRow.tsx` — one top-stories list item: headline, source-count chip,
  freshness, and a momentum indicator.
- `news/StoryTimeline.tsx` — the drill-down development timeline (every source
  article in chronological order).
- `news/SourceList.tsx` — the drill-down source-diversity readout.
- `news/hooks.ts` — TanStack Query hooks for the two endpoints.
- `lib/newsFormat.ts` — formatting helpers (relative time, source counts,
  momentum labels).
- `routes/StoryRoute.tsx` — the drill-down page (see §7).
- `lib/types.ts` + `lib/api.ts` — add News types and endpoint functions.
- `router.tsx` — add the `/news/:clusterId` route.
- `routes/Home.tsx` — replace the News `ComingSoonPanel` with `NewsPanel`.
- The overview story → drill-down uses the same shared-element View Transition
  the Finance and Economics domains already use.

## 5. Data sources

### 5.1 RSS feeds (breadth backbone)

~25 curated RSS feeds from major general-news outlets — e.g. Reuters, AP, BBC,
NPR, The Guardian, NYT, Al Jazeera, PBS, ABC, CBS, and similar. The exact feed
list is finalized in the implementation plan as a static config list. Each feed
is parsed with `feedparser`; entries are normalized to the common `Article`
shape. Per-feed isolation means the list can grow or shrink without risk.

### 5.2 NewsData.io (breadth supplement)

Base URL `https://newsdata.io/api/1/`, `apikey` from `NEWS_API_KEY`. The
`latest` endpoint supplies recent articles, normalized to the same `Article`
shape and merged into the ingestion pipeline. Run on the free tier
(~200 credits/day) — far above the volume a single-user scheduler needs. With
`NEWS_API_KEY` unset, the provider returns `[]` and the domain runs RSS-only.

## 6. The overview panel

Replaces the placeholder in the News quadrant. A single "Top Stories" view — no
tabs. It contains:

- **The momentum field (hero):** a force-laid-out beeswarm. Each top story is a
  circle — **size** = distinct sources covering it, **x-position** = momentum
  score (surging stories drift right), **color** = surging / steady / fading.
  Circles settle with spring physics and re-flow when the data refreshes.
  Hovering a circle reveals the headline and key stats.
- **The top-stories list:** a short, clickable list below the beeswarm — each row
  shows the headline, a source-count chip, freshness, and a momentum indicator.

Clicking a circle or a list row opens the drill-down via the shared-element
transition. Calm at rest; richness on hover and interaction, per the parent
spec's design bar.

## 7. The drill-down page (`/news/:clusterId`)

The full story view for one cluster:

- **The development timeline** — every source article in the cluster, in
  chronological order, so you can see how the story broke and developed.
- **Source diversity** — which outlets are covering it, and how many.
- **Momentum over time** — the cluster's coverage velocity rendered with the
  existing `LineChart`.
- **Related stories** — other clusters surfaced by embedding similarity to this
  one.
- An empty slot reserved for the Phase 5 AI "why this matters" explainer.

Entered via the shared-element View Transition: the overview story expands in
place.

## 8. Error handling

Per the parent spec §11.

- **Per-feed / per-source isolation** — one failing RSS feed or a NewsData.io
  outage never blanks the panel; the remaining sources still produce stories.
- **Embeddings failure** — if the `fastembed` model is unavailable, clustering
  falls back to grouping articles by normalized title (exact / near-duplicate
  headline matching). This is degraded — semantically reworded headlines will not
  merge — but the panel stays functional.
- **All sources down** — serve the last-good cached overview; the panel shows a
  subtle "stale" badge rather than breaking.
- **Scheduler jobs** log and continue.
- With `NEWS_API_KEY` unset (local dev without a key), the API provider returns
  `[]` and the domain runs on RSS alone; the endpoints always return an
  empty-but-valid payload so the UI degrades gracefully.

## 9. Testing

- **Backend (pytest):** `rss_provider` and `news_api_provider` tested against
  recorded / mocked feed and API responses, including the per-source failure
  paths; `news_clustering` and `news_metrics` pure functions unit-tested (TDD);
  `embeddings` exercised with a mocked seam; routes tested with the cache and the
  auth dependency.
- **Frontend:** component tests for `NewsPanel`, `StoryRow`, `BeeswarmChart`,
  `StoryTimeline`, `SourceList`, and the drill-down page; a Playwright spec for
  the news overview → drill-down flow (API stubbed).

## 10. Scope

One implementation plan, roughly 18–22 TDD tasks, executed via subagent-driven
development. Out of scope: AI summaries / explainers (Phase 5), a global news
search box, the Politics domain (Phase 4), and any paid data source.
