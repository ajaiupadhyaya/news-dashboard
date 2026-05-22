# News & Markets Dashboard

A personal, daily-driver dashboard for **news, politics, economics, and
finance** - a calm overview that reveals depth, motion, and bespoke
visualizations on interaction.

**Phase 1 (live):** the foundation + the Finance domain end-to-end - a
four-quadrant home, a Finance overview panel (watchlist, breadth, sector
heatmap, indices), and a per-instrument drill-down with a bespoke candlestick
chart. News, Politics, and Economics are placeholders pending later phases.
Phase 2 adds the Economics domain — a FRED-backed indicator overview and an indicator drill-down.

## Structure

| Path | What |
|---|---|
| `backend/` | FastAPI backend - Finance API, scheduler, caching. See `backend/README.md`. |
| `frontend/` | Vite + React + TypeScript SPA. See `frontend/README.md`. |
| `docs/` | Design spec and implementation plans (under `docs/superpowers/`). |
| `DEPLOY.md` | Live-deploy runbook (Supabase + Fly.io + Vercel). |

## Run it locally

```bash
# Backend - http://127.0.0.1:8000
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt && uvicorn app.main:app --reload

# Frontend - http://localhost:5173
cd frontend && npm install && npm run dev
```

## Deploy

See [`DEPLOY.md`](./DEPLOY.md).
