# Samonta: integrated S10, S12 and S13

Base: origin/main ecc81b7, 22 November 2026. This package extends the approved latest
portals; it does not overwrite them with the older S10/S13 ZIP versions.

## Included

| Slice | Location | Behavior |
|---|---|---|
| S10 | Admin Orders & Production → Production Jobs; Employee My Tasks | Fully settled order assignment, one job/Employee per order, private drawings, progress, pause/resume, stage history |
| S12 | Employee Report Issue; Admin Orders & Production → Production Issues | Own reports, optional own job, two private attachments, Admin handling and status history |
| S13 | Admin Inventory; dashboard Low Stock Alerts | Material management, manual add/deduct with reason, exact quantities, immutable movement history and real low/out-of-stock counts |
| Customer view | My Orders → Production Tracking | Own order stage, percentage and customer-visible updates |

Existing quotations, commercial orders, simulated payments, PDF invoices and all public
routes remain in place. Background refresh preserves open inputs. Files use per-tab
protected fetches. S11 quality approval/delivery is not implemented by this package;
Employee submissions stop at Quality Check, and 100% is not completion.

## Windows installation using the included Git bundle

Keep the ZIP and its extracted folder outside your project, for example
`C:\Projects\Samonta-Integrated`. Stop the running backend/frontend with Ctrl+C.

1. Inspect your local changes. If tracked code changes exist, save them in a commit
   on your current feature branch first. Do not commit .env, keys, database files,
   private uploads, old archives or backups. The following switch must not discard work.

```powershell
cd C:\Projects\KPC-Priyam-Preview
git status
git fetch origin
```

2. Import the prepared commit and create a separate review branch. Adjust the bundle
   path to where you extracted this ZIP. The bundle requires main ecc81b7, fetched above.

```powershell
git fetch "C:\Projects\Samonta-Integrated\samonta-integrated.bundle" feature/samonta-s10-s12-s13
git switch -c feature/samonta-s10-s12-s13 FETCH_HEAD
```

Stop if Git reports uncommitted changes, untracked-file collisions or a missing base.
Do not force checkout or delete your older source. If this branch name already exists,
choose a different new branch name. `source/` contains review copies, not files to
extract over your project. The `.patch` is an alternative for a clean checkout of the
exact base, not something to apply in addition to the bundle.

3. Install the current dependencies with your existing virtual environment:

```powershell
cd C:\Projects\KPC-Priyam-Preview\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_samonta_database.py
```

**If the check prints STOP, do not run upgrade.** Old S13 used revision 006 and old
S10 used 007. Main now uses 006 for quotations, 007 for commercial orders and 008 for
payments. Revision number alone does not prove compatibility. This read-only check
looks for expected tables and catches legacy inventory/production tables ahead of
the recorded revision. It does not repair, stamp, drop or overwrite a database.
Keep a PostgreSQL backup and review the output before choosing a data migration.
Never solve this collision with `alembic stamp head`, a database reset or deleted tables.
No legacy database conversion is included because your actual schema is not available.

4. Only after a Compatible result, upgrade:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Expected head: **011**, in the single chain 008 → 009 Inventory → 010 Production →
011 Issues. Keep your backend .env private. Issue attachments reuse the configured
private Supabase bucket; allow image/jpeg, image/png and application/pdf up to 20 MB.

5. In a second terminal:

```powershell
cd C:\Projects\KPC-Priyam-Preview\frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173/. If that port is busy, use the existing server or stop its
terminal before restarting. Keep the existing proxy target 127.0.0.1:8001.

## Verify on your machine before merging

- Admin inventory: add a material, record opening stock, deduct stock with a reason,
  refresh, inspect history, and check low-stock threshold/equality behavior.
- Commercial flow: accept a quotation, record failed/partial simulated payments
  and confirm assignment is blocked. Fully settle it, assign to an active Employee,
  and confirm a second job cannot be assigned.
- Employee: inspect only assigned work/drawings, save progress, pause/resume,
  advance stages and submit machining at 100% to Quality Check.
- Customer: own tracking changes appear; internal notes, issue details and drawings
  do not. Quotation/order/payment/invoice screens still work.
- S12: report with and without attachments, reject an invalid upload, have Admin
  record a handling update, then confirm the reporting Employee can see it.
- Check desktop and narrow/mobile layouts, keyboard controls, loading/error/empty
  states, and simultaneous role tabs. Browser verification remains pending here.

Then push your new branch and open a PR to main:

```powershell
cd C:\Projects\KPC-Priyam-Preview
git push -u origin feature/samonta-s10-s12-s13
```

The package has not been pushed or merged into GitHub by the assistant.

## Verification performed

References inspected: global UI kit; Admin dashboard, inventory and orders/production;
Employee dashboard, tasks, completed jobs and report issue; Customer order tracking.
Adaptations omit unsupported sample metrics and use the documented 20 MB issue limit.
Existing route bindings, layouts, sidebar, ports and deployment proxy are preserved.

- Backend: 182 passed, 15 skipped (77.68 seconds).
- `npm --prefix frontend run build`: passed.
- `git diff --check` and Python compilation: passed.
- Actual S07 acceptance → S09 ledger → S10 assignment/progress flow is covered.
- Role/ownership restrictions, stale versions, rollback, upload rejection and cleanup
  are covered. SQLite concurrent inventory deductions and job writes are covered.
- Migration startup applies the full chain twice on a temporary SQLite database.
- Real PostgreSQL concurrency tests need their dedicated test database variables;
  skipped tests are not evidence of PostgreSQL verification.
- Chromium launch fails with `socket() failed: Operation not permitted`; no desktop
  or mobile browser walkthrough is claimed. Do that locally before merging.
