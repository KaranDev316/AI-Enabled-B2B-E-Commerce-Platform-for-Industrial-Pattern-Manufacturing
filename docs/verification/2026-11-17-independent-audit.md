# Independent audit — 17 November 2026

Tested revision: `564d52e`. These checks were written independently of `backend/tests`, using the requirements in PRP-001, PRP-003 and PRP-009. No application source was changed.

## Execution

Fresh disposable PostgreSQL 17.12 database, UTF-8, Python 3.12.16, real Alembic migrations through revision 004, Uvicorn on loopback port 8019, real HTTP requests and local private file storage. No dependency overrides, SQLite or existing pytest fixtures. Synthetic users only. The frontend build was the Vite build produced in the earlier verification turn.

The scripts recorded **29 checks: 20 passed and 9 failed**. This is a targeted audit, not complete requirement coverage. See [individual results](independent-results.json).

Both saved scripts were rerun: all nine failing checks reproduced. Concurrent ticket creation produced two HTTP 500 responses on that rerun (three on the initial run), confirming that the exact schedule changes the failure count. The checked-in JSON records the initial completed run.

Separately, applying migrations passed; `alembic check` failed with two missing indexes. Chrome browser observations confirmed that an unauthenticated `/customer` visit redirected to `/login`, and a disposable customer could sign in and reach the customer workspace. Refresh, logout and further browser workflows were not completed because the browser was being used concurrently.

## Reproduced defects

| Priority | Finding | Reproduction and observed result | Relevant source |
| --- | --- | --- | --- |
| High | Mandatory password change can be bypassed | Admin resets customer password; old session correctly becomes invalid. Sign in using the reset password: `must_change_password=true`. Submit `POST /api/rfqs` with the new session and valid CSRF: **201**, RFQ persisted before changing password. | `backend/app/dependencies.py:get_current_user`, PRP-001 AC-01-08 |
| High | Two-file limit is not transaction safe | Three independent PostgreSQL transactions enter `attach_rfq_file`. A barrier immediately before storage writes ensures all capacity checks overlap; real storage writes and DB commits proceed. **Three files persist** on one RFQ. This is a synchronized service-level reproduction, not a claim that the single-worker HTTP run exceeded the limit. | `backend/app/services/rfq_service.py:attach_rfq_file`, PRP-003 AC-03-05 |
| High | Concurrent ticket numbering collides | Six concurrent real HTTP support-ticket submissions: **201, 201, 201, 500, 500, 500**. PostgreSQL reports duplicate `ticket_number` keys. Number generation uses current row count + 1. | `backend/app/services/support_service.py:generate_ticket_number` |
| Medium | Invalid CAD content accepted | Ordinary text named `.iges` and 100 arbitrary `x` bytes named `.stl` each return **201**. IGES checks for any one section letter; binary STL accepts any payload at least 84 bytes long. | `backend/app/services/file_validation.py:validate_file_content`, PRP-003 AC-03-07 |
| Medium | Unicode filename breaks download | Valid PNG uploaded as `चित्र.png` returns **201**; retrieving the saved file returns **500**. Server raises `UnicodeEncodeError` while encoding the raw filename in `Content-Disposition`. | `backend/app/api/rfqs.py:stream_rfq_file`, PRP-003 AC-03-06 |
| Medium | Overlong profile input causes server error | `PATCH /api/profile/me` with a 256-character company name returns **500**, rather than field validation. PostgreSQL rejects the `VARCHAR(255)` write. | `backend/app/schemas/account.py:ProfileUpdateRequest`, `backend/app/services/account_service.py:update_own_profile` |
| Medium | Blank business details accepted | Registration using whitespace-only company name, contact person and phone returns **201**; trimming occurs after minimum-length validation. | `backend/app/schemas/account.py:CustomerRegisterRequest`, PRP-001 AC-01-02 |
| Medium | Blank support submission accepted | Subject and message containing only three spaces return **201**. | `backend/app/schemas/support.py:SupportTicketCreateRequest`, PRP-009 AC-09-02 |
| Low | Migrations differ from model metadata | After fresh upgrade to 004, `alembic check` requests `ix_rfq_files_uploaded_by_user_id` and `ix_support_ticket_files_uploaded_by_user_id`. | RFQ/support file models and migrations 003/004 |

The CAD finding accounts for two failing script checks; other script failures each correspond to one row. Schema drift is an additional finding outside the 29 script checks.

## Checks that passed

Customer registration and profile persistence, login, local cookie flags, case-insensitive duplicate registration rejection, public role-tampering rejection, customer/admin role separation, anonymous RFQ denial, cross-session CSRF rejection, untrusted-Origin rejection, PostgreSQL RFQ creation, cross-customer RFQ/file/reply denial, PNG byte-for-byte retrieval, support creation, password reset and old-session revocation. The unsynchronized six-upload HTTP run respected the two-file limit on this single Uvicorn worker; the overlapping transaction reproduction demonstrates the underlying race.

## Reproduction

Scripts are [independent_audit.py](../../backend/verification/independent_audit.py) and [concurrency_audit.py](../../backend/verification/concurrency_audit.py). They deliberately create synthetic records and require a disposable local PostgreSQL database whose name ends in `_test`. Do not point them at shared/application data. They run outside pytest and do not import its fixtures.

1. Create a fresh UTF-8 local PostgreSQL test database. Set `DATABASE_URL` to its `postgresql+psycopg` URL. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` empty, and `PRIVATE_STORAGE_DIR=/private/tmp/kpc-test-verification/independent-uploads` in both the API and script environments.
2. From `backend`, run `.venv/bin/python -m alembic upgrade head`.
3. Run the API with `ALLOWED_ORIGINS='["http://127.0.0.1:8019"]' .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8019`.
4. From another terminal with the same database/storage environment, run `PYTHONPATH=. .venv/bin/python verification/independent_audit.py`, then `PYTHONPATH=. .venv/bin/python verification/concurrency_audit.py`. Run the second even when the first exits 1: exit 1 records failed assertions. The second reuses the first script's generated fixture and appends results. Fresh synthetic names are generated for each first-script run.
5. Run `.venv/bin/python -m alembic check` separately.

Results and the ephemeral fixture are written under `/private/tmp/kpc-test-verification`. The checked-in JSON contains no passwords, session cookies or CSRF tokens. Concurrent HTTP scheduling can change the exact mix of statuses; the service barrier gives a controlled reproduction of the upload race.

## Limits

Supabase integration, hosted HTTPS, real browser RFQ/support submission, full role walkthroughs, migration downgrade/re-upgrade, crash recovery, and the complete verification plan remain unverified. No fixes are included in this audit. The existing suite passing does not establish readiness while these defects remain.
