# Automatic deployments — Vercel frontend, Render backend, Supabase database

## Normal releases

Commit and push the reviewed changes to `main`. GitHub Actions runs backend tests, guarded PostgreSQL race/migration checks and the frontend build. Once the existing Render service is configured to wait for successful CI, it installs requirements and executes `python start.py --host 0.0.0.0`. That command upgrades the database to the newest checked-in Alembic revision before starting the API. Vercel builds the Git-connected `frontend` project automatically; the repository sets `npm run build` and `dist` explicitly and preserves the API proxy.

Applied migration revisions do not run again. A Python-only change needs no new migration file. A new table/column/constraint still requires a reviewed Alembic migration committed with its backend change. This automation never generates schema changes, commits local work or bypasses review. The two hosting providers deploy independently; keep a release compatible during their brief version overlap.

## One-time settings for the existing services

Set these only after `backend/start.py` has been pushed to the linked repository.

| Render setting | Value |
| --- | --- |
| Linked branch | `main` |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python start.py --host 0.0.0.0` |
| Health Check Path | `/api/health` |
| Auto-Deploy | `After CI Checks Pass` |

Keep the existing DATABASE_URL, allowed origins, secure-cookie setting and storage secrets in Render. Do not put them in repository configuration. No deploy-hook token, GitHub cloud secret, new service or paid pre-deploy command is needed. Render settings are not changed merely by adding a repository file.

Vercel keeps Root Directory `frontend` and the Git-connected production branch `main`. `frontend/vercel.json` now declares build/output settings; it retains the `/api` → Render rewrite. No database credential belongs in Vercel frontend settings.

## Startup behavior

- Local: `cd backend` then `.venv/bin/python start.py --reload`. Initial startup checks migrations, then serves on `127.0.0.1:8001`. Ordinary Python edits reload. If you add a migration while the reloader is already running, restart this entry point once to apply it.
- Render: uses its assigned PORT and binds `0.0.0.0`. Every deployment restarts through the same entry point.
- Schema-only check: `.venv/bin/python start.py --migrate-only`.
- Failed migration: API startup stops. Fix the migration/deployment failure, then deploy again; no manual schema stamp or automatic downgrade is performed.
- Concurrent PostgreSQL startups using this entry point take a shared advisory lock around the migration command. The migration runs on a separate database connection while that lock is held, compatible with the project's session-pooler connection. Use this entry point consistently for automated migrations.

`/api/health` remains a liveness endpoint. Migration completion is evidenced by startup logs and the migration revision, not inferred from that endpoint alone. On a code rollback, applied database migrations remain; use compatible forward changes rather than assuming a database rollback.

## Verification

`backend/tests/test_startup.py` checks migration failure blocks serving, the API starts only after a successful check, and two real migration-only runs leave the database at the current head. CI runs the entry point twice against its own PostgreSQL test database before the backend suite. Deployment must be verified in the provider dashboards after the one-time settings and repository changes are published.

## Official references

- [Render automatic deployments and CI gating](https://render.com/docs/deploys)
- [Vercel Git deployments](https://vercel.com/docs/git)
- [Vercel build configuration](https://vercel.com/docs/builds/configure-a-build)
