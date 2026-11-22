# S13 verification contract

References: docs/PRPs/008-inventory-and-stock.md (PRP-008 manual inventory),
docs/ui-ux/admin/inventory.webp and docs/ui-ux/global/ui-kit.webp.
Follow the existing AdminLayout. Keep Inventory summary cards, filter row, materials table and
right detail/stock-history panel. Omit suppliers, usage tracking, procurement and reorder actions.

- Admin-only API reads/writes; Origin and session CSRF required for all mutations.
- Unique material code, name, category, unit, location, description and nonnegative minimum.
- New records start at zero. Opening stock is a reasoned adjustment, not a hidden quantity field.
- Descriptive edits cannot write quantity. Units remain immutable to preserve history meaning.
- Positive additions/deductions, mandatory reason, actor/time and before/after balances.
- Balance and history commit together. Conditional SQL updates prevent negative/overflow stock.
- A UUID request ID makes retrying the same adjustment safe; mismatched reuse is rejected.
- Out of stock means zero. Positive below minimum is low. Equality is adequate stock.
- History is append-only; corrections require compensating adjustments.
- Tests: permissions/CSRF/Origin, validation, duplicates, exact decimals, unit preservation,
  history reconciliation, atomic rollback, retry behavior and concurrent deductions.
- Verify material create/edit, stock updates, history, status filters and detail panel at desktop
  and narrow width. Do not claim screenshots/browsing passed if unavailable.

## Implemented scope

Materials have unique normalized uppercase codes, names, Raw Material/Consumable/Tool category,
kg/g/litre/metre/piece unit, minimum stock, location and description. Each starts at zero.
Stock movements record a positive amount and addition/deduction direction, reason, actor snapshot,
time and before/after balances. Up to three decimal places; pieces must be whole numbers.
The unit is immutable. No delete/history-edit endpoint, supplier or automatic stock consumption.

GET /api/admin/inventory/materials, /materials/{id}, /materials/{id}/adjustments and /summary.
POST /materials, PUT /materials/{id}, POST /materials/{id}/adjustments.
All endpoints are Admin-only; writes require trusted Origin and session CSRF.

Inventory UI is integrated into the approved AdminLayout's existing Inventory page. It provides
stored-count status cards, search/category/status filters, sorting and real pagination, a details/
stock-movement panel, material create/edit form and reasoned adjustment form. The dashboard stock
card now uses the inventory summary endpoint, independent of RFQ/support loading failures.
Errors retain entered form data. Retried adjustments reuse UUID request IDs; edited adjustments
get fresh IDs. Empty/error/loading states do not display invented healthy stock counts.

## Installation (Windows PowerShell)

Save samonta-s13-inventory.zip in C:\Projects\KPC-Priyam-Preview. Stop the backend.
Check git status first: commit or preserve any modified tracked source files before updating main.
Untracked downloaded archives do not need to be committed.

```powershell
cd C:\Projects\KPC-Priyam-Preview
git switch feature/samonta-integration
git fetch origin
git merge --ff-only origin/main
git switch -c feature/samonta-s13-inventory
$backupFile = ".\s13-source-backup-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
Compress-Archive -Path .\backend\app,.\backend\migrations,.\frontend\src -DestinationPath $backupFile
Expand-Archive .\samonta-s13-inventory.zip -DestinationPath . -Force
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

If a Git command fails, stop and resolve that error before extraction. No force/reset is needed.
Keep the frontend running on 5173; refresh and sign in as Admin → Inventory.
No new Python/npm dependencies, Supabase buckets or credentials are needed for S13.
Local PostgreSQL holds the new materials/history tables. Migration 009 follows official main revision 008; it does not reset existing data.
Coordinate revision ordering if teammates add another migration before integrating this branch.

## Evidence

- Full pinned backend suite: **104 passed, 1 skipped** (isolated PostgreSQL test not configured).
- Includes a real two-session concurrent-deduction test on a temporary SQLite database.
- Historical package: migration 005 → 006 and repeated upgrade checked on SQLite; existing S04 product preserved.
- Frontend production build passed. Git diff whitespace checks passed.
- Desktop/mobile visual walkthrough: **not completed**. The cloud browser cannot reach the local
  preview; it receives a gateway bearer-token error. Do not treat this as browser verification.
- Test fixtures use isolated databases. No demonstration materials are silently seeded into live data.

Intentional reference adaptations: Inventory-only label (no Suppliers); omit Reorder, Usage and
supplier controls because they are excluded; use Details and Stock Movement tabs and plain material
facts without fabricated stock photography. Keep existing Admin shell, reference card/table structure
and semantic stock colours. Desktop panel stacks on narrow screens.

Before calling S13 locally demonstrated: add a material; add opening stock with a reason; refresh;
edit its location; deduct to exactly the minimum (In Stock); deduct below it (Low Stock); attempt
an excessive deduction (rejected, unchanged balance/history); deduct remaining stock (Out of Stock);
check history actor/reasons and retry behavior, dashboard counts, filters and narrow-screen layout.

## Current integration

Integrated against main ecc81b7. Use 009_inventory.py, not the old 006_inventory.py.
The Admin dashboard now loads real low/out-of-stock counts independently of its
commercial dashboard data. Run check_samonta_database.py before upgrading.
See SAMONTA-INTEGRATION.md for the authoritative installation and verification status.
