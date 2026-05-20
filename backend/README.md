# News & Markets Dashboard — Backend

FastAPI backend for the Finance domain (Phase 1a).

## Quickstart

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

## Tests

```bash
cd backend && python -m pytest -v
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe |
| POST | `/api/auth/login` | Exchange password for token |
| GET | `/api/auth/status` | Whether auth is enabled |
| GET | `/api/watchlist` | List watchlist symbols |
| POST | `/api/watchlist` | Add a symbol `{"symbol": "AAPL"}` |
| DELETE | `/api/watchlist/{symbol}` | Remove a symbol |
| GET | `/api/finance/overview` | Watchlist + indices + sectors + breadth |
| GET | `/api/finance/instrument/{symbol}` | OHLCV + technicals + fundamentals |

## Configuration

See `.env.example`. Auth is disabled unless `DASHBOARD_TOKEN` is set. The
database defaults to local SQLite; set `DATABASE_URL` to Postgres for production.
