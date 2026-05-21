# News & Markets Dashboard — Frontend

The React + TypeScript single-page app for the News & Markets Dashboard — a
four-quadrant overview (News, Politics, Economics, Finance) with the Finance
domain built end-to-end: a live overview panel and a per-instrument drill-down.

## Stack

- Vite + React 19 + TypeScript
- Tailwind CSS v4 with a CSS-first design-token layer
- Motion (Framer Motion) for animation; the View Transitions API for
  route-level morphs
- D3 for bespoke charts (sparkline, candlestick)
- TanStack Query for data fetching/caching; React Router v7 for routing

## Setup

    npm install
    cp .env.example .env

`VITE_API_BASE_URL` points at the backend (default `http://127.0.0.1:8000`).

## Scripts

- `npm run dev` — dev server on http://localhost:5173
- `npm run build` — type-check and production build
- `npm run preview` — preview the production build
- `npm test` — unit & component tests (Vitest)
- `npm run test:e2e` — end-to-end tests (Playwright)
- `npm run lint` — type-check only

## Running the full app

1. Start the backend: `cd ../backend && uvicorn app.main:app`
2. Start the frontend: `npm run dev`

Tests mock the backend and do not require it to be running.

## Architecture

- `src/design/` — design tokens and motion presets (the visual language)
- `src/charts/` — the D3-in-React chart system (frame, axis, sparkline,
  candlestick); every visualization is bespoke
- `src/lib/` — API client, types, formatters
- `src/auth/` — single-user token gate
- `src/components/` — app shell and the generic domain panel
- `src/finance/` — the Finance domain (overview panel + drill-down pieces)
- `src/routes/` — the Home dashboard and the instrument drill-down route

## Deployment

The frontend deploys to Vercel and auto-builds on push to `main`. Set
`VITE_API_BASE_URL` to the deployed backend URL in the Vercel project. See the
repo-root [`DEPLOY.md`](../DEPLOY.md) for the full runbook.
