# Deployment Runbook

The dashboard deploys as three pieces:

| Piece | Host | What it is |
|---|---|---|
| Database | Supabase | Managed Postgres |
| Backend | Fly.io | FastAPI container, always-on (the scheduler runs in-process) |
| Frontend | Vercel | Static React SPA, auto-deployed from GitHub |

Both public URLs are predictable from the names you choose, so pick them first:

- **Fly app name** -> `https://<fly-app-name>.fly.dev`
- **Vercel project name** -> `https://<vercel-project-name>.vercel.app`

This runbook uses `news-dashboard-api` (Fly) and `news-dashboard` (Vercel) - if
either is taken, substitute your own and adjust the commands.

---

## Prerequisites

- Accounts: [Supabase](https://supabase.com), [Fly.io](https://fly.io),
  [Vercel](https://vercel.com), and GitHub (repo already pushed).
- The Fly CLI: `brew install flyctl` (or `curl -L https://fly.io/install.sh | sh`). The `fly` and `flyctl` commands are interchangeable.
- Vercel is driven entirely from its web dashboard below - no CLI needed.

---

## Step 1 - Supabase (database)

1. In the Supabase dashboard: **New project**. Choose a region near US-East and
   set a strong database password - **save it**.
2. Wait for provisioning to finish.
3. Open **Project Settings -> Database -> Connection string** and select the
   **Session pooler** tab (IPv4, port `5432`). Copy the URI - it looks like:

   ```
   postgresql://postgres.abcdefgh:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
   ```

4. Replace `[PASSWORD]` with the password from step 1 and append `?sslmode=require`:

   ```
   postgresql://postgres.abcdefgh:YOUR_PW@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```

   This whole string is your `DATABASE_URL`. No manual schema step is needed -
   the backend's `init_db()` creates every table on first boot.

---

## Step 2 - Fly.io (backend)

Run the commands in this step from the `backend/` directory (where `fly.toml` lives). `fly auth login` works from anywhere.

1. Log in: `fly auth login`.
2. Create the app (reusing the committed `fly.toml`, no deploy yet):

   ```bash
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

   - `DASHBOARD_PASSWORD` - what you type on the login screen.
   - `DASHBOARD_TOKEN` - the bearer token the app stores after login; a random
     value. **Both** must be set, or auth is misconfigured (the backend rejects
     login with a 500 if only one is present).
   - `CORS_ORIGINS` - your Vercel production URL (from Step 3). Set it now using
     the predicted name; correct it later if the real domain differs.
4. Deploy: `fly deploy`.
5. Verify:

   ```bash
   curl https://news-dashboard-api.fly.dev/health
   curl https://news-dashboard-api.fly.dev/health/ready
   ```

   Expect `{"status":"ok"}` and `{"status":"ok","database":"ok"}`. If readiness
   fails, the `DATABASE_URL` secret is wrong - re-check Step 1.

---

## Step 3 - Vercel (frontend)

1. In the Vercel dashboard: **Add New -> Project**, import
   `ajaiupadhyaya/news-dashboard`.
2. Set **Root Directory** to `frontend`. The framework auto-detects as Vite. The committed `frontend/vercel.json` supplies the build command, output directory, and SPA rewrites automatically — no manual build configuration is needed.
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

## Step 4 - Backend auto-deploy (optional)

To auto-deploy the backend on push to `main` (the `deploy-backend.yml` workflow):

1. Create a deploy token: `fly tokens create deploy` and copy it.
2. In GitHub: **Settings -> Secrets and variables -> Actions -> New repository
   secret**. Name it `FLY_API_TOKEN`, paste the token.

Until this secret exists the workflow skips cleanly (the job still passes).

---

## Step 5 - Verify live

Open the Vercel URL, log in with `DASHBOARD_PASSWORD`, and confirm the Finance
panel loads its watchlist and an instrument drill-down opens.

---

## Costs

Roughly within the project's ~$5-25/mo budget: Supabase free tier ($0), one
Fly `shared-cpu-1x` 1 GB machine running 24/7 (~$5-7/mo), Vercel Hobby ($0).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Login returns 500 | Only one of `DASHBOARD_PASSWORD` / `DASHBOARD_TOKEN` is set - set both. |
| Frontend loads but all panels error | `VITE_API_BASE_URL` wrong, or `CORS_ORIGINS` doesn't match the Vercel domain. |
| `/health/ready` returns 503 | `DATABASE_URL` is wrong or missing `?sslmode=require`. |
| Browser console shows a CORS error | `CORS_ORIGINS` must be the exact Vercel origin, scheme included. |
