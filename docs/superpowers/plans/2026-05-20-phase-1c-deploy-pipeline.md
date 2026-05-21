# Phase 1c — Deploy Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Phase 1 dashboard (FastAPI backend + React SPA) deployable to the web — containerize the backend, add Fly.io / Vercel / Supabase configuration, wire up CI, and document a repeatable live-deploy runbook.

**Architecture:** Two independent deploys plus a managed database. The FastAPI backend runs as a single-worker Docker container on **Fly.io** (always-on, so APScheduler stays alive). The React SPA is a static build hosted on **Vercel** (native git integration → auto-deploy on push to `main`). Persistent data lives in **Supabase Postgres**, reached over SQLAlchemy via the existing `DATABASE_URL` env var. **GitHub Actions** runs the full test suite on every push/PR and (once a token is configured) auto-deploys the backend to Fly.

**Tech Stack:** Docker (`python:3.12-slim`), Fly.io (`fly.toml`), Vercel (`vercel.json`), Supabase Postgres, GitHub Actions.

**Task split:** Tasks 1–7 create all configuration, code, and docs — each is fully verifiable on this machine and is the work of the subagent executor. **Task 8 is the live deployment** — it requires the owner's Fly.io / Vercel / Supabase accounts and credentials, so it is a **user-driven runbook**, not a subagent task.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/routes/health.py` (modify) | Add a `/health/ready` readiness probe that confirms DB connectivity |
| `backend/tests/test_health.py` (modify) | Tests for the readiness probe |
| `backend/Dockerfile` (create) | Container image for the Fly.io backend |
| `backend/.dockerignore` (create) | Keep the build context (and image) small |
| `backend/fly.toml` (create) | Fly.io app config — port, health check, always-on machine, non-secret env |
| `frontend/vercel.json` (create) | Vercel build settings, SPA rewrites, asset cache headers |
| `.github/workflows/ci.yml` (create) | CI — backend pytest, frontend unit tests + build, Playwright E2E |
| `.github/workflows/deploy-backend.yml` (create) | Auto-deploy the backend to Fly on push to `main` (gated on `FLY_API_TOKEN`) |
| `DEPLOY.md` (create) | The end-to-end live-deploy runbook |
| `README.md` (create) | Repo landing page — overview + links |
| `backend/README.md` / `frontend/README.md` (modify) | Add a "Deployment" pointer to `DEPLOY.md` |

---

### Task 1: Readiness probe (`/health/ready`)

The existing `/health` is a pure liveness probe (never touches the DB) and stays the Fly health check. This task adds a separate `/health/ready` that runs `SELECT 1` against the database — used to confirm the Supabase wiring after a deploy, and available for future monitoring. It must NOT be wired into Fly's health check: a transient Supabase blip should not get the machine killed.

**Files:**
- Modify: `backend/app/routes/health.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_health.py` (after the existing `test_app_starts_with_lifespan`):

```python
def test_ready_returns_ok_when_db_reachable(db):
    """With a working database, /health/ready reports ok."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_ready_returns_503_when_db_unreachable(monkeypatch):
    """If the database cannot be reached, /health/ready returns 503."""
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr("app.routes.health.get_engine", boom)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "database unavailable"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: the two new tests FAIL — `/health/ready` does not exist yet, so the route 404s (`200 != 404`).

- [ ] **Step 3: Implement the readiness probe**

Replace the entire contents of `backend/app/routes/health.py` with:

```python
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database import get_engine

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe — never touches the database or external APIs."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict:
    """Readiness probe — verifies the database is reachable.

    Used to confirm DB wiring after a deploy. Deliberately NOT the Fly
    health check: a transient database blip must not kill the machine.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("readiness check failed: %s", e)
        raise HTTPException(status_code=503, detail="database unavailable") from e
    return {"status": "ok", "database": "ok"}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: all health tests PASS (4 total).

- [ ] **Step 5: Run the full backend suite for regressions**

Run: `cd backend && python -m pytest -q`
Expected: the whole suite PASSES (65 tests — 63 prior + 2 new).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routes/health.py backend/tests/test_health.py
git commit -m "feat(backend): add /health/ready database readiness probe"
```

---

### Task 2: Backend container (`Dockerfile` + `.dockerignore`)

Containerize the FastAPI backend for Fly.io. Single uvicorn worker — APScheduler runs in-process and must not be multiplied across workers. Dependencies install in their own layer so code-only changes rebuild fast.

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Create `backend/.dockerignore`**

```
.venv/
**/__pycache__/
*.pyc
data/
.env
.env.example
.pytest_cache/
tests/
README.md
.gitignore
.dockerignore
Dockerfile
fly.toml
requirements-dev.txt
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
# News & Markets Dashboard — backend container (Fly.io).
# Build context is the backend/ directory.
FROM python:3.12-slim

# No .pyc files; unbuffered stdout so logs stream straight to Fly.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first — this layer is cached across code-only changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application package.
COPY app ./app

# Fly routes public HTTPS traffic to this internal port.
EXPOSE 8080

# Single worker: APScheduler runs in-process and must not be duplicated.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 3: Build the image**

Run: `docker build -t nmd-backend ./backend`
Expected: build SUCCEEDS, ending with `naming to docker.io/library/nmd-backend`.

- [ ] **Step 4: Smoke-test the container**

Run:
```bash
docker run -d -p 8080:8080 --name nmd-smoke nmd-backend
sleep 4
curl -fs localhost:8080/health
echo
curl -fs localhost:8080/health/ready
echo
docker rm -f nmd-smoke
```
Expected: `/health` prints `{"status":"ok"}` and `/health/ready` prints `{"status":"ok","database":"ok"}` (the container falls back to a local SQLite file when `DATABASE_URL` is unset, so readiness still passes). The final line prints `nmd-smoke`.

If any curl fails, inspect logs before deleting: `docker logs nmd-smoke`.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "feat(deploy): containerize the backend for Fly.io"
```

---

### Task 3: Fly.io app config (`fly.toml`)

Fly configuration for the backend: internal port `8080`, HTTPS forced, one always-on machine (so the scheduler keeps running), a liveness health check on `/health`, and non-secret env. Secrets (`DATABASE_URL`, `DASHBOARD_TOKEN`, `DASHBOARD_PASSWORD`, `CORS_ORIGINS`) are set separately via `fly secrets` in Task 8 — never committed.

**Files:**
- Create: `backend/fly.toml`

- [ ] **Step 1: Create `backend/fly.toml`**

```toml
# Fly.io configuration — News & Markets Dashboard backend.
# Deploy from the backend/ directory:  fly deploy
#
# The app name must be globally unique on Fly. If "news-dashboard-api" is
# taken, change it here — it is the single source of truth for the name.
app = "news-dashboard-api"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

# Non-secret configuration only. Secrets go through `fly secrets set`.
[env]
  SCHEDULER_ENABLED = "true"
  LOG_LEVEL = "INFO"
  CACHE_TTL_SECONDS = "300"

[http_service]
  internal_port = 8080
  force_https = true
  # Always-on: the in-process scheduler must keep running.
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1
  processes = ["app"]

  [[http_service.checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"
    method = "GET"
    path = "/health"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

- [ ] **Step 2: Validate the TOML parses**

Run: `python3 -c "import tomllib; tomllib.load(open('backend/fly.toml','rb')); print('fly.toml OK')"`
Expected: prints `fly.toml OK` (no exception). `tomllib` is in the Python 3.11+ standard library.

- [ ] **Step 3: Commit**

```bash
git add backend/fly.toml
git commit -m "feat(deploy): add Fly.io app configuration"
```

---

### Task 4: Vercel frontend config (`vercel.json`)

Vercel config for the SPA. The `rewrites` rule sends every non-file path to `index.html` so React Router's client-side routes (e.g. `/finance/AAPL`) resolve on hard reload. Vercel serves real static files before applying rewrites, so hashed assets are unaffected. Long-lived immutable caching is set for the content-hashed `assets/` bundle.

**Files:**
- Create: `frontend/vercel.json`

- [ ] **Step 1: Create `frontend/vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate the JSON parses**

Run: `python3 -c "import json; json.load(open('frontend/vercel.json')); print('vercel.json OK')"`
Expected: prints `vercel.json OK`.

- [ ] **Step 3: Verify the production build still succeeds**

Run: `cd frontend && npm run build`
Expected: `tsc --noEmit` passes and `vite build` writes `dist/` with `dist/index.html` and `dist/assets/`. (`vercel.json` does not affect the local build; this just confirms nothing regressed.)

- [ ] **Step 4: Commit**

```bash
git add frontend/vercel.json
git commit -m "feat(deploy): add Vercel SPA configuration"
```

---

### Task 5: CI workflow (`.github/workflows/ci.yml`)

Run the full test suite on every push and PR to `main`: backend pytest, frontend unit tests + production build, and the Playwright E2E flow. The E2E test stubs the API with `page.route`, so it needs no live backend — Playwright starts the Vite dev server itself via the `webServer` block in `playwright.config.ts`.

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend:
    name: Backend tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements-dev.txt
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: python -m pytest -q

  frontend:
    name: Frontend tests & build
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
      - name: Unit tests
        run: npm run test
      - name: Build
        run: npm run build

  e2e:
    name: Frontend E2E
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright browser
        run: npx playwright install --with-deps chromium
      - name: Run E2E tests
        run: npm run test:e2e
```

- [ ] **Step 2: Validate the YAML parses**

Run: `ruby -ryaml -e 'YAML.load_file(".github/workflows/ci.yml"); puts "ci.yml OK"'`
Expected: prints `ci.yml OK`. (`ruby` ships with macOS; `yaml` is in its standard library.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run backend, frontend, and E2E tests on push and PR"
```

---

### Task 6: Backend auto-deploy workflow (`.github/workflows/deploy-backend.yml`)

Auto-deploy the backend to Fly.io on every push to `main` that touches `backend/`. It is gated on a `FLY_API_TOKEN` repo secret: until that secret is added (Task 8), the deploy steps skip cleanly and the job still reports success — so the workflow never shows a red ❌ before it is wired up. The frontend needs no equivalent workflow: Vercel's native GitHub integration auto-deploys it.

**Files:**
- Create: `.github/workflows/deploy-backend.yml`

- [ ] **Step 1: Create `.github/workflows/deploy-backend.yml`**

```yaml
name: Deploy backend (Fly.io)

on:
  push:
    branches: [main]
    paths:
      - "backend/**"
      - ".github/workflows/deploy-backend.yml"
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Fly.io
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Guard — require FLY_API_TOKEN
        id: guard
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          if [ -z "$FLY_API_TOKEN" ]; then
            echo "FLY_API_TOKEN is not set — skipping deploy."
            echo "Add it under Settings → Secrets and variables → Actions to enable auto-deploy."
            echo "skip=true" >> "$GITHUB_OUTPUT"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Set up flyctl
        if: steps.guard.outputs.skip != 'true'
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy
        if: steps.guard.outputs.skip != 'true'
        run: flyctl deploy ./backend --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

- [ ] **Step 2: Validate the YAML parses**

Run: `ruby -ryaml -e 'YAML.load_file(".github/workflows/deploy-backend.yml"); puts "deploy-backend.yml OK"'`
Expected: prints `deploy-backend.yml OK`.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy-backend.yml
git commit -m "ci: auto-deploy the backend to Fly.io on push to main"
```

---

### Task 7: Deploy docs (`DEPLOY.md`, root `README.md`, README pointers)

Write the live-deploy runbook and give the repo a landing page. The runbook is the canonical, step-by-step version of Task 8.

**Files:**
- Create: `DEPLOY.md`
- Create: `README.md`
- Modify: `backend/README.md`
- Modify: `frontend/README.md`

- [ ] **Step 1: Create `DEPLOY.md`**

````markdown
# Deployment Runbook

The dashboard deploys as three pieces:

| Piece | Host | What it is |
|---|---|---|
| Database | Supabase | Managed Postgres |
| Backend | Fly.io | FastAPI container, always-on (the scheduler runs in-process) |
| Frontend | Vercel | Static React SPA, auto-deployed from GitHub |

Both public URLs are predictable from the names you choose, so pick them first:

- **Fly app name** → `https://<fly-app-name>.fly.dev`
- **Vercel project name** → `https://<vercel-project-name>.vercel.app`

This runbook uses `news-dashboard-api` (Fly) and `news-dashboard` (Vercel) — if
either is taken, substitute your own and adjust the commands.

---

## Prerequisites

- Accounts: [Supabase](https://supabase.com), [Fly.io](https://fly.io),
  [Vercel](https://vercel.com), and GitHub (repo already pushed).
- The Fly CLI: `brew install flyctl` (or `curl -L https://fly.io/install.sh | sh`).
- Vercel is driven entirely from its web dashboard below — no CLI needed.

---

## Step 1 — Supabase (database)

1. In the Supabase dashboard: **New project**. Choose a region near US-East and
   set a strong database password — **save it**.
2. Wait for provisioning to finish.
3. Open **Project Settings → Database → Connection string** and select the
   **Session pooler** tab (IPv4, port `5432`). Copy the URI — it looks like:

   ```
   postgresql://postgres.abcdefgh:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
   ```

4. Replace `[PASSWORD]` with the password from step 1 and append `?sslmode=require`:

   ```
   postgresql://postgres.abcdefgh:YOUR_PW@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```

   This whole string is your `DATABASE_URL`. No manual schema step is needed —
   the backend's `init_db()` creates every table on first boot.

---

## Step 2 — Fly.io (backend)

Run everything from the `backend/` directory.

1. Log in: `fly auth login`.
2. Create the app (reusing the committed `fly.toml`, no deploy yet):

   ```bash
   cd backend
   fly launch --no-deploy --copy-config --ha=false --name news-dashboard-api
   ```

   If the name is taken, pick another and update `app = "..."` in `backend/fly.toml`.
3. Set the secrets (a restart is triggered automatically):

   ```bash
   fly secrets set \
     DATABASE_URL="postgresql://...?sslmode=require" \
     DASHBOARD_PASSWORD="choose-a-strong-password" \
     DASHBOARD_TOKEN="$(openssl rand -hex 32)" \
     CORS_ORIGINS="https://news-dashboard.vercel.app"
   ```

   - `DASHBOARD_PASSWORD` — what you type on the login screen.
   - `DASHBOARD_TOKEN` — the bearer token the app stores after login; a random
     value. **Both** must be set, or auth is misconfigured (the backend rejects
     login with a 500 if only one is present).
   - `CORS_ORIGINS` — your Vercel production URL (from Step 3). Set it now using
     the predicted name; correct it later if the real domain differs.
4. Deploy: `fly deploy`.
5. Verify:

   ```bash
   curl https://news-dashboard-api.fly.dev/health
   curl https://news-dashboard-api.fly.dev/health/ready
   ```

   Expect `{"status":"ok"}` and `{"status":"ok","database":"ok"}`. If readiness
   fails, the `DATABASE_URL` secret is wrong — re-check Step 1.

---

## Step 3 — Vercel (frontend)

1. In the Vercel dashboard: **Add New → Project**, import
   `ajaiupadhyaya/news-dashboard`.
2. Set **Root Directory** to `frontend`. The framework auto-detects as Vite.
3. Add an environment variable:

   | Name | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://news-dashboard-api.fly.dev` |

4. **Deploy.** Note the production domain Vercel assigns.
5. If that domain is not `https://news-dashboard.vercel.app`, update the backend:

   ```bash
   fly secrets set CORS_ORIGINS="https://<actual-vercel-domain>"
   ```

From now on, every push to `main` auto-deploys the frontend via Vercel's GitHub
integration.

---

## Step 4 — Backend auto-deploy (optional)

To auto-deploy the backend on push to `main` (the `deploy-backend.yml` workflow):

1. Create a deploy token: `fly tokens create deploy` and copy it.
2. In GitHub: **Settings → Secrets and variables → Actions → New repository
   secret**. Name it `FLY_API_TOKEN`, paste the token.

Until this secret exists the workflow skips cleanly (the job still passes).

---

## Step 5 — Verify live

Open the Vercel URL, log in with `DASHBOARD_PASSWORD`, and confirm the Finance
panel loads its watchlist and an instrument drill-down opens.

---

## Costs

Roughly within the project's ~$5–25/mo budget: Supabase free tier ($0), one
Fly `shared-cpu-1x` 512 MB machine running 24/7 (~$3–5/mo), Vercel Hobby ($0).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Login returns 500 | Only one of `DASHBOARD_PASSWORD` / `DASHBOARD_TOKEN` is set — set both. |
| Frontend loads but all panels error | `VITE_API_BASE_URL` wrong, or `CORS_ORIGINS` doesn't match the Vercel domain. |
| `/health/ready` returns 503 | `DATABASE_URL` is wrong or missing `?sslmode=require`. |
| Browser console shows a CORS error | `CORS_ORIGINS` must be the exact Vercel origin, scheme included. |
````

- [ ] **Step 2: Create the root `README.md`**

```markdown
# News & Markets Dashboard

A personal, daily-driver dashboard for **news, politics, economics, and
finance** — a calm overview that reveals depth, motion, and bespoke
visualizations on interaction.

**Phase 1 (live):** the foundation + the Finance domain end-to-end — a
four-quadrant home, a Finance overview panel (watchlist, breadth, sector
heatmap, indices), and a per-instrument drill-down with a bespoke candlestick
chart. News, Politics, and Economics are placeholders pending later phases.

## Structure

| Path | What |
|---|---|
| `backend/` | FastAPI backend — Finance API, scheduler, caching. See `backend/README.md`. |
| `frontend/` | Vite + React + TypeScript SPA. See `frontend/README.md`. |
| `docs/` | Design spec and implementation plans. |
| `DEPLOY.md` | Live-deploy runbook (Supabase + Fly.io + Vercel). |

## Run it locally

```bash
# Backend — http://127.0.0.1:8000
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt && uvicorn app.main:app --reload

# Frontend — http://localhost:5173
cd frontend && npm install && npm run dev
```

## Deploy

See [`DEPLOY.md`](./DEPLOY.md).
```

- [ ] **Step 3: Add a Deployment section to `backend/README.md`**

Append to `backend/README.md`:

```markdown

## Deployment

The backend runs as a Docker container on Fly.io. See the repo-root
[`DEPLOY.md`](../DEPLOY.md) for the full runbook. Production configuration is
supplied via environment variables / Fly secrets — never committed.
```

- [ ] **Step 4: Add a Deployment section to `frontend/README.md`**

Append to `frontend/README.md`:

```markdown

## Deployment

The frontend deploys to Vercel and auto-builds on push to `main`. Set
`VITE_API_BASE_URL` to the deployed backend URL in the Vercel project. See the
repo-root [`DEPLOY.md`](../DEPLOY.md) for the full runbook.
```

- [ ] **Step 5: Verify the docs render and links resolve**

Run:
```bash
ls DEPLOY.md README.md && \
grep -c "DEPLOY.md" README.md backend/README.md frontend/README.md
```
Expected: both files listed; each README reports at least one `DEPLOY.md` reference.

- [ ] **Step 6: Commit**

```bash
git add DEPLOY.md README.md backend/README.md frontend/README.md
git commit -m "docs: add deploy runbook and repo landing page"
```

---

### Task 8: Live deployment — USER-DRIVEN

> **Not a subagent task.** This step provisions real infrastructure under the
> owner's Supabase / Fly.io / Vercel accounts and needs interactive logins and
> secrets. The subagent executor stops after Task 7 and hands off to the user.

The full procedure is in [`DEPLOY.md`](../../../DEPLOY.md). Checklist:

- [ ] **Supabase:** create the project, build the `DATABASE_URL` (Session pooler URI + `?sslmode=require`).
- [ ] **Fly.io:** `fly auth login` → `fly launch --no-deploy --copy-config --ha=false` → `fly secrets set` (`DATABASE_URL`, `DASHBOARD_PASSWORD`, `DASHBOARD_TOKEN`, `CORS_ORIGINS`) → `fly deploy`.
- [ ] **Verify backend:** `curl .../health` and `.../health/ready` both return ok.
- [ ] **Vercel:** import the repo, Root Directory `frontend`, set `VITE_API_BASE_URL`, deploy.
- [ ] **Wire CORS:** ensure the backend's `CORS_ORIGINS` matches the real Vercel domain.
- [ ] **GitHub:** add the `FLY_API_TOKEN` secret to enable backend auto-deploy.
- [ ] **Verify live:** open the Vercel URL, log in, confirm the Finance panel and a drill-down work.
- [ ] After a successful live deploy, update `project_news_dashboard.md` in memory: Plan 1c COMPLETE, record the live URLs.

---

## Plan complete

Phase 1 ships when Task 8 finishes: the Finance dashboard is live on the web,
CI guards every push, and both deploys are automated. Later phases (2 Economics,
3 News, 4 Politics, 5 AI layer, 6 polish) each get their own plan.
