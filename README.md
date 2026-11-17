# KPC — Khodel Pattern Craft

Final-year BCA project for a single industrial pattern manufacturer.

## Current state

Project foundation: React/Vite/Bootstrap frontend, FastAPI API, SQLAlchemy/Alembic configuration, and initial CI checks. The development page calls the API health endpoint. Authentication, database tables/migrations, and business features are not implemented yet. A successful health response proves API liveness only.

## Requirements

- Node.js 24 and npm (`.nvmrc` records the Node version line).
- Python 3.12 (`.python-version` records the version line).
- Git.
- Native PostgreSQL 17 for database work, with separate `kpc_dev` and `kpc_test` databases. The initial health/build checks can run before PostgreSQL is configured.

No Docker is needed on developers' computers. GitHub Actions uses an isolated PostgreSQL service for CI, as approved in CONTEXT.md.

## First local run

Clone this repository and open its root in VS Code. Never copy another developer's `.env` file or credentials.

```bash
git clone https://github.com/KaranDev316/AI-Enabled-B2B-E-Commerce-Platform-for-Industrial-Pattern-Manufacturing.git kpc
cd kpc
```

### Backend — terminal 1

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell instead of the Unix environment commands.

Edit `backend/.env` privately before database work. Set your own `DATABASE_URL` and a separate `TEST_DATABASE_URL`. The example values are placeholders. If your password contains URL-reserved characters, URL-encode those characters in the connection string. Do not commit `.env`.

### Frontend — terminal 2

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open **http://127.0.0.1:5173**. The page should report API connectivity. Vite forwards `/api` to port 8000 while preserving the browser Origin. Keep API calls relative; do not put database/storage secrets in any `VITE_` variable. If port 5173 is occupied, free it rather than silently switching the allowed browser origin.

## Database and migrations

Create separate development/test databases using your native PostgreSQL installation and your own local database roles. Configure the two connection strings privately. PostgreSQL/Supabase credentials are never supplied in project documentation.

Alembic is initialized, but **there is no migration revision or application table yet**. The initial users/sessions migration belongs to the scoped S01 work. After models are introduced and imported into the migration metadata, create, inspect, and apply their migration:

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

Do not run autogeneration before models exist. Never wipe the shared demonstration database to adopt a schema change. Agree on migration ordering with the backend owner.

## Run checks

```bash
cd backend
source .venv/bin/activate
python -m pytest -q -ra
```

The PostgreSQL test skips unless `TEST_DATABASE_URL` is exported in the test process environment. Loading `backend/.env` for application settings does not export it to the shell. Set that variable privately before running the database check. Its database name must end in `_test` and must not identify the application database. The current connection check performs only `SELECT 1`; later destructive fixtures need additional isolation guards.

```bash
cd frontend
npm run build
```

The backend will serve `frontend/dist` on port 8000 when that build exists. Restart the backend after the first frontend build, then visit **http://127.0.0.1:8000** to check the single-origin built application. Vite remains the development server for normal frontend editing. `npm run preview` previews frontend assets only and is not a substitute for the API proxy or backend-served build.

GitHub Actions runs the backend checks with PostgreSQL and the frontend build on main pushes and pull requests. Local checks do not prove that remote CI has passed.

## Structure and working agreements

| Path | Responsibility |
| --- | --- |
| `frontend/` | React UI and shared components |
| `backend/app/` | API, configuration, database foundation; feature modules added per slice |
| `backend/migrations/` | Alembic environment and reviewed schema revisions |
| `backend/tests/` | Automated verification |
| `backend/ml/` | Offline model work in S15 |
| `data/demo/` | Synthetic fixtures/dataset in their applicable slices |
| `docs/` | Project decisions, requirements, slice plan, and verification |

Read [CONTEXT.md](docs/CONTEXT.md), [PRP.md](docs/PRP.md), [VERTICAL_SLICE_PLAN.md](docs/VERTICAL_SLICE_PLAN.md), and [VERIFICATION_PLAN.md](docs/VERIFICATION_PLAN.md) before feature work. Historical UI controls cannot add excluded scope.

Use task branches such as `setup/frontend`, `s01/session-api`, or `s01/login-ui`. Open a pull request, record checks actually run, and have another developer review it. This README establishes the convention; it does not claim GitHub branch protection has been configured.

Suggested ownership: team lead handles frontend/integration; developer 2 owns backend/schema; developer 3 owns verification/demo data and later ML. Names and account invitations are assigned by the team. Everyone tests their own changes.

## Immediate next work

Complete native setup on each developer's computer, verify CI and PostgreSQL connectivity, and prepare the bounded S01 implementation prompts. Then implement secure sessions/login against the S01 verification contract. No authentication endpoint currently exists, so no S01 authentication check has passed.

## Reference documentation

- [UI/UX screen index](docs/ui-ux/README.md) — 28 original mockups covering the public site, Admin, Customer, Employee, and shared UI components. Use these for visual reference within the approved project scope.
- [Vite development server/proxy](https://vite.dev/config/server-options)
- [FastAPI first steps](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
