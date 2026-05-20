# News & Markets Dashboard — Design Spec

**Date:** 2026-05-20
**Status:** Approved design — ready for implementation planning
**Working directory:** `~/Documents/news-dashboard`

---

## 1. Purpose

A personal, daily-driver dashboard for monitoring **news, politics, economics, and
finance** — from a quick morning glance down to high-level, detailed analysis. One
user (the owner), used every day to track events, indicators, stocks, and companies.

It should feel **simple on the surface and powerful underneath**: a calm, uncluttered
home that reveals depth, motion, and craft the moment it's interacted with.

## 2. Goals & non-goals

**Goals**
- Cover four domains — news, politics, economics, finance — at **equal weight**.
- Support both a fast glance and deep analysis of any item.
- Best-in-class UI/UX: stunning animations, bespoke visualizations, a polished feel.
- Stay snappy: the UI never waits on a third-party API.
- Run on a small budget (~$5–25/mo for data) and free/near-free hosting.

**Non-goals**
- Not multi-user; no public accounts system.
- Not an extension of the existing **Models** project — standalone, though it borrows
  Models' code patterns (provider adapters, scheduler, caching, deploy path).
- Not a trade-execution platform; this is monitoring and analysis only.

## 3. Product shape (decisions made during brainstorming)

| Decision | Choice |
|---|---|
| Project | New standalone project |
| Domain weighting | Equal four-quadrant (news / politics / economics / finance) |
| Depth model | Overview home + drill-down pages |
| Data budget | Small (~$5–25/mo) — mostly free sources + one paid news API |
| Analysis style | Data backbone + AI synthesis layer on top |
| Geographic lens | US-core, global awareness |
| Architecture | Python FastAPI backend + Vite/React SPA frontend |
| Home layout | Option A — AI briefing ribbon on top, 2×2 quadrant grid, watchlist inside the Finance panel |

## 4. Architecture

**Core principle:** *the frontend never waits on a third-party API.* Everything the
UI reads is already ingested, computed, and cached. Drill-downs may trigger a fresh
fetch, but always with a cached fallback.

**Frontend** — Vite + React + TypeScript SPA.
- Routes: the four-quadrant overview home + one drill-down route per domain/item.
- Motion (Framer Motion) for animation; D3 for bespoke visualizations; View
  Transitions API for route-level morphs; Tailwind CSS over a custom design-token layer.
- Watchlist & preferences UI.

**Backend** — Python FastAPI, organized into:
- **Provider adapters** — one module per domain, each wrapping external feeds/APIs
  behind a uniform interface (pattern lifted from Models).
- **Scheduler** — APScheduler, env-gated. Periodic jobs: refresh feeds, recompute
  metrics, regenerate the AI daily briefing.
- **Analysis layer** — pandas/numpy: technicals, correlations, economic-surprise
  indices, sentiment, market breadth. Pure functions, independently testable.
- **AI service** — wraps the Claude API (`anthropic` SDK). Generates the daily
  briefing, "why this matters" explainers, and jargon definitions. Output cached.
- **API routes** — REST endpoints the frontend calls; serve only pre-computed/cached
  data, never block on slow external calls.

**Database** — Supabase Postgres, accessed via SQLAlchemy. Tables: cached feed items,
time-series history (markets/econ), computed-metric snapshots, AI briefing cache,
user watchlists/preferences.

**Auth** — single-user, a simple token/password gate. No multi-user system.

**Deploy** — Fly.io (backend, always-on) + Vercel (frontend) + Supabase (DB). This is
the proven free-tier path from the Models project.

**Data flow:** scheduler → provider adapters fetch → normalize → store in Postgres →
analysis layer computes metrics → AI service generates briefing → all cached. Frontend
→ calls FastAPI → reads pre-computed/cached data → renders.

## 5. Layout

**Overview home (Layout Option A):**
- **App bar** — logo, date, search/command, settings.
- **AI briefing ribbon** — full-width strip directly below the app bar; the first thing
  read each morning. "What matters today" + a few bullets, expandable to the full briefing.
- **2×2 quadrant grid** — four equal panels: News (top-left), Politics (top-right),
  Economics (bottom-left), Finance (bottom-right). Each panel has a domain header, a
  hero visualization, and a short list of items.
- The **watchlist** lives inside the Finance panel.

**Drill-down page** — opened by clicking a panel or an item. Contains the full hero
visualization, supporting detail panels, history, and an AI "why this matters"
explainer. Entered via a shared-element transition: the overview chart expands in place.

Each domain follows the same shape — an overview panel on the home, a drill-down page
behind it.

## 6. The four domains

### 📰 News
- **Overview:** top stories clustered by theme, de-duplicated across sources, each with
  a source count + freshness indicator; a "story momentum" viz.
- **Drill-down:** full story cluster — every source, a development timeline, AI summary
  + "why this matters," related threads.
- **Data:** free RSS feeds for breadth + one paid news aggregation API for clustering,
  de-duplication, and search.

### 🏛 Politics
- **Overview:** bills moving + key votes, an approval/polling gauge, an
  upcoming-events calendar.
- **Drill-down:** bill/vote tracker, polling trend charts, representative & agency
  profiles.
- **Data:** Congress.gov API (free, keyed), GovTrack, official RSS, polling aggregates.

### 📈 Economics
- **Overview:** key-indicator tiles (inflation, jobs, GDP, rates) with **surprise
  markers** (actual vs. expected) + an economic-release calendar.
- **Drill-down:** full time series for any indicator, recession-signal composites, an
  economic-surprise index.
- **Data:** FRED API (free — the backbone), BLS public API, an economic-calendar feed.

### 💹 Finance (+ watchlist)
- **Overview:** the watchlist with quotes + sparklines, market breadth, a sector
  heatmap, index summary.
- **Drill-down:** full instrument page — candlestick + technicals, fundamentals,
  company news, filings, correlations.
- **Data:** yfinance / Stooq (free), Polygon.io / FMP free tiers, EDGAR for filings.
  Adapters and analysis lifted directly from Models.

## 7. AI layer (cross-cutting)

- **Daily briefing** — a scheduled morning job synthesizes all four domains into the
  ribbon; full briefing expandable.
- **"Why this matters"** — an AI explainer on every drill-down page.
- **Explainers** — plain-language definitions of jargon, keeping the "basic level"
  accessible.
- **Cross-domain connections** — AI flags when an event in one domain affects another
  (e.g. a politics event hitting a market sector).
- All AI output is **cached and regenerated on a schedule, never per request** — this
  keeps cost predictable.

## 8. Design & UX principles

These are hard requirements, not polish-if-time:

- **Calm surface, rich depth.** The home reads clean and uncluttered; richness reveals
  only on interaction.
- **Shared-element transitions.** Clicking an overview panel morphs it into its
  drill-down — the chart expands in place, no jarring page load.
- **Micro-interactions everywhere.** Hover, focus, and selection states animate with
  spring physics. Motion guides attention; it is never decorative noise.
- **Progressive disclosure.** Layered density: glance → hover for more → click for full.
- **Charts as craft.** Every visualization is bespoke — professional and legible
  *first*, then creative. Smooth enter/update/exit transitions, interactive
  crosshairs/tooltips, deliberate color and typography. No off-the-shelf chart-library look.
- **Accessible & respectful.** Honors `prefers-reduced-motion`; legible at a glance.

**Tooling for the bar:**
- *Animation:* Motion (Framer Motion) for component/layout animation + spring physics;
  the View Transitions API for route-level morphs.
- *Visualization:* D3 for bespoke charts rendered into React. Canvas/WebGL only where
  data volume demands it (dense heatmaps). A shared **chart design system** — common
  scales, axes, color, motion — so every chart feels one family.
- A small **design-token system** (color, type, spacing, motion curves) so polish is
  systematic, not ad hoc.

## 9. Tech stack summary

| Layer | Choice |
|---|---|
| Frontend | Vite + React + TypeScript, Tailwind CSS + design tokens |
| Animation | Motion (Framer Motion), View Transitions API |
| Visualization | D3; Canvas/WebGL where needed |
| Backend | Python FastAPI, APScheduler, httpx, pandas/numpy |
| AI | Claude API via the `anthropic` SDK |
| Database | Supabase Postgres via SQLAlchemy |
| Hosting | Fly.io (backend) + Vercel (frontend) + Supabase (DB) |
| Auth | Single-user token/password gate |

## 10. Scope & phasing

This is a large product. This spec describes the whole thing; implementation is phased,
and each phase is independently shippable.

1. **Foundation** — backend scaffold, DB schema, frontend shell, auth gate, deploy
   pipeline, the four-quadrant home shell, and the **Finance domain end-to-end**
   (overview panel + drill-down, reusing Models adapters). Establishes the chart
   design system and the motion system.
2. **Economics** — FRED-backed; overview + drill-down.
3. **News** — feeds, clustering, drill-down.
4. **Politics** — overview + drill-down (the hardest data layer).
5. **AI layer** — daily briefing, "why this matters," explainers, cross-domain links.
6. **Polish pass** — apply the "stunning" bar across every visualization and
   interaction; performance and deploy hardening.

**The first implementation plan covers Phase 1 only.** Later phases each get their own
plan when reached.

## 11. Error handling

- Every external feed can fail → always serve a cached fallback; panels show a subtle
  "stale" badge rather than breaking.
- **Per-panel isolation** — one bad feed never takes down the page.
- Scheduler jobs log and retry with backoff.
- AI failure → silent fallback to the data-only view.

## 12. Testing

- **Backend:** pytest. Provider adapters tested against recorded/mocked responses; the
  analysis layer (pure functions) unit-tested; API routes tested. TDD for the
  logic-heavy analysis layer.
- **Frontend:** component tests for panels and charts; Playwright for the critical
  overview → drill-down flow.

## 13. Open decisions (deferred, non-blocking for Phase 1)

These do not block Phase 1 (Finance uses well-known free sources). Each is resolved
when its phase begins:

- **Paid news API** — candidates: NewsData.io, TheNewsAPI, GNews. Choose against the
  ~$5–25/mo budget at the start of Phase 3 (News).
- **Polling data source** for Politics — a reliable free/cheap polling aggregate source
  to be identified at the start of Phase 4. Politics overview degrades gracefully
  (bills + votes + calendar) if no good polling source is found.
- **Economic-calendar feed** — source to be identified at the start of Phase 2.
- **Project name** — "News & Markets Dashboard" is the working title; final name TBD.
