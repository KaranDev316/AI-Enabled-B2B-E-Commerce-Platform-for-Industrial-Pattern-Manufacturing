# S04 — Admin catalogue management

Implemented on Samonta's integration branch, against Priyam's S01/S02/S05/S06/S14 foundation.

## Scope and verification contract

- Only an active Admin can read the management APIs or mutate products/categories/images.
- Every mutation requires a trusted Origin and the session-bound CSRF token.
- Products support name, unique lowercase hyphenated slug, category, material, description,
  plain-text specifications, optional nonnegative two-decimal indicative INR price, and activation.
- Missing categories, whitespace-only names, negative prices, invalid slugs and duplicate names/slugs fail with feedback.
- Products are deactivated rather than deleted. Existing product IDs and RFQ references remain.
  Accepted quotation/order snapshots belong to Alfred's S07/S08 and require later integration verification.
- Categories can be created and renamed. Referencing products retain their category IDs.
- Admin uploads 1–2 JPEG/PNG files per submission, up to 20 MiB each and 25 megapixels.
  Extension, MIME, actual decoded format and image integrity are checked before any storage write.
- Private Supabase Storage holds uploaded objects with generated catalogue-only keys. Product
  responses expose image IDs/URLs, never service keys, bucket paths or private RFQ documents.
- Anonymous reads serve only images associated with active products. Admin can preview inactive products' images.
- Public cards/details prefer uploaded images, offer image selection, and show specifications.
  The three supplied reference photos remain fallbacks for products without an upload.
- Failed multi-file storage/database writes compensate attempted objects and save no new image associations.
  Existing images survive failed later submissions. If compensation itself fails, the object key is
  logged for operator cleanup; it is not exposed by the catalogue. Image removal first removes its
  association and then deletes bytes; failed byte deletion is logged for operator cleanup.

## Install on Windows

Stop the running backend with Ctrl+C. In the project root, back up your source before extraction:

```powershell
cd C:\Projects\KPC-Priyam-Preview
$backupFile = ".\s04-source-backup-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
Compress-Archive -Path .\backend\app,.\backend\migrations,.\backend\requirements.txt,.\backend\requirements.in,.\frontend\src -DestinationPath $backupFile
Expand-Archive .\samonta-s04-catalogue.zip -DestinationPath . -Force
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep the frontend on port 5173. Refresh, sign in as Admin, and open **Products & Categories**.
Migration 005 adds specifications and image metadata; it does not reset existing databases.
No credentials, .env files, virtual environments or database files are distributed in this archive.

## Private image storage setup

Product/category editing works with the existing PostgreSQL connection. Uploads also require:

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_PRIVATE_SERVER_SIDE_KEY
SUPABASE_STORAGE_BUCKET=kpc-private-files
```

Create that bucket in your Supabase project and keep it **private**. Allow JPEG/PNG uploads up to
20 MiB in bucket settings. Reuse an existing private bucket only if these settings allow the
project's RFQ/support file types too. Keep the service-role key in backend .env only, never in
frontend variables or Git. Restart the backend after setting values. Missing storage settings
produce an actionable error and do not pretend the image was saved. The current Settings class
also reads a root .env and process environment: check for overrides if settings differ.

## Evidence and remaining checks

- Full backend suite: **72 passed, 1 skipped** using the pinned requirements (PostgreSQL connection test skipped).
- Automated API tests cover role/Origin/CSRF guards, validation, category changes, persistence,
  deactivation, preserved RFQ reference, private/public image access, JPEG/PNG roundtrip,
  two-image upload, size/count/type/signature failures, and storage/database compensation.
- Migration 004 → 005 and repeated upgrade checked on isolated SQLite with an existing product.
- Frontend production build checked.
- PostgreSQL test requires an isolated TEST_DATABASE_URL and is skipped without it.
- Live Supabase roundtrip and a desktop/mobile browser walkthrough remain to be performed on
  the configured development setup. Browser launch in the coding environment was blocked.
- Test-browser product/category actions to demonstrate: add category; add product; refresh;
  edit specifications/price; upload photo; inspect public detail; deactivate; verify public 404;
  reactivate; remove image; sign in as Customer and confirm no management access.
