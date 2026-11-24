# S07 — Manual versioned quotations

Scope: REQ-14, REQ-15, REQ-16 and manual provenance in REQ-13. Acceptance/order/invoice creation remains S08. This record does not close S01/S02 or claim hosted deployment verification.

## Current issue verification — 24 November 2026

Baseline: `a288756`, including the existing S07 fix `682d52b`, plus the S07 changes committed with this record. Earlier evidence below is historical and is not counted in this run.

- #33: verified issue v1 → Customer reject → Admin revise directly → issue v2 → Customer select v2. Rejected v1 retains its original itemization, amounts and response; only v2 is eligible. The rework success message now accurately says the prior version remains in history rather than claiming that a rejected version became superseded.
- #34: verified two independently authenticated Admin browser tabs on draft v3. Admin B saved notes first. Admin A's stale save returned a conflict and retained its unsaved notes. Cancelling the discard confirmation preserved them; confirming loaded Admin B's notes. Confirmed save followed by a forced quotation-GET 503 showed “Your change was saved, but the latest quotation could not be loaded.” Removing the fault and selecting Reload recovered the saved revision. An independent database query confirmed revision 3, the saved notes, and exactly three quotation versions. Initial GET failure on reopening showed an error and Reload, without an empty-list claim or draft-creation action; recovery restored v3. Successful mutation responses now immediately replace the local saved revision/status before the subsequent retrieval, so a failed retrieval cannot leave the UI using the previous revision. Manual refresh clears obsolete success feedback.
- #35: Admin input and both roles' pricing summaries visibly identify sample academic tax. The local fixture used one line with quantity 2 at INR 100 unit price, sample tax 8%, subtotal INR 200, tax INR 16, total INR 216; these are isolated test records, not business facts. Version history retained those amounts. No monetary calculation code changed.
- #36: the three previously skipped PostgreSQL races now pass, alongside a new rejected-version race, failed-revision rollback test, and migration-chain retention check. Hosted authenticated quotation/session/persistence verification is **not run**. On 24 November 2026 the task owner explicitly instructed: “ignore the hosted one, the fixes is okay commit and close the issue”. #36 is closed with this owner-approved waiver; this is not a hosted acceptance pass.

Environment: native local PostgreSQL, disposable database `kpc_s09_test` on `127.0.0.1:55439`; each automated PostgreSQL case uses its own generated schema. No shared Supabase records were touched. Local browser uses the approved frontend `127.0.0.1:5173` and backend `127.0.0.1:8001`. The API was restarted during the browser run and retained quotations/sessions. Failure injection used a temporary wrapper outside the repository around the actual FastAPI application: only GET paths ending `/quotations` returned 503 while a temporary flag existed. Writes and the database remained real; the flag was removed after verification. This is local failure evidence, not a hosted fault-injection pass.

Commands and final results:

```sh
cd backend
S07_POSTGRES_TEST_URL=postgresql+psycopg://127.0.0.1:55439/kpc_s09_test .venv/bin/python -B -m pytest -q -ra -p no:cacheprovider tests/test_quotations_s07.py tests/test_quotations_s07_postgres.py tests/test_migrations_s07.py tests/test_acceptance_s08.py
# 35 passed; 0 failed; 0 skipped; 0 xfailed; 0 errors; 1 Starlette/httpx deprecation warning.
cd ..
node --test frontend/tests/*.test.js
# 10 passed; 0 failed; 0 skipped; 0 cancelled; 0 todo.
npm --prefix frontend run build
# Passed.
git diff --check
# Passed.
```

`test_migrations_s07.py` executes real Alembic upgrades 001 through 006 sequentially, seeds quotation/items/rejection history, disposes connections, repeats upgrade 006 in a new process, then verifies retained records, version uniqueness and quotation constraints. It does not substitute `create_all` for migrations. The five concurrency/rollback test cases separately use PostgreSQL row locks. Frontend hook tests exercise stale-input retention, cancelled/failed/successful discard recovery, confirmed-write/failed-retrieval handling, load-error versus empty-state behavior, and sample tax disclosure; they are not counted as browser tests.

Visual references opened: `docs/ui-ux/admin/rfqs-and-quotations.webp`, `docs/ui-ux/customer/quotation-review.webp`, `docs/ui-ux/global/ui-kit.webp`. Native Chrome screenshots and accessibility observations checked existing shells, navy/orange hierarchy, item table, totals, summary, version controls, error/retry and discard prompt. The small native browser window was checked using page zoom to exercise wide desktop layout (Admin 50%, Customer 33%) and a narrow layout (150% for both roles); this is responsive browser evidence, not physical-device testing. The sidebar collapses at narrow width; forms and primary actions stack; tax wording remains readable. No route, shared layout, stylesheet, dependency, port or deployment configuration changed. Intentional adaptations are explicit academic-tax disclosure and honest recovery feedback within the existing layout; excluded AI/confidence, notification and 60/40 controls from old references remain excluded.

Remaining not-run checks: authenticated hosted Customer/Admin journeys against identified deployed revisions, hosted quotation retention after reload/restart, and deployed same-origin session/CSRF behavior. The supplied Vercel URL alone does not establish those checks. #33–#35 have local API/PostgreSQL/browser evidence. The task owner waived the hosted portion of #36 for this closure; those checks remain not run and must not be presented as passed or as full hosted/release acceptance.

## Contract and evidence

Fixtures: isolated Customer 1/Customer 2, Admin and Employee accounts; a Customer 1 custom RFQ. Browser fixtures use a separate disposable localhost PostgreSQL database, never Supabase. No model artifact is installed or required.

| Case | Action and expected persisted state | Evidence, 2026-11-20 |
| --- | --- | --- |
| AC-05-01 | Issue v1, then create v2 draft with expected version 1. v1 is immediately superseded; v2 is the only latest version. A stale customer response gets 409. Issued history retains original prices. Unissued drafts stay private. | `test_manual_lifecycle_money_and_change_request`; browser Admin revised v1 to v2 |
| AC-05-02 preparation | Seed accepted quote; update, send, and revision endpoints reject it. Two simultaneous first drafts or revisions yield one success and one 409, with unique ordered versions. Concurrent draft edits cannot overwrite a saved revision. | `test_version_conflict_and_accepted_immutable`; all 3 PostgreSQL race cases passed |
| AC-05-03 | Customer 2 cannot read/respond to Customer 1 quote; Employee cannot review; Customer cannot use Admin endpoints; writes need CSRF/trusted Origin. Empty, zero-total, missing-lead-time or expired drafts cannot issue. | Ownership/validation tests; incomplete draft test |
| AC-05-04 preparation | A stored sent quote with past validity displays expired and cannot receive a response at action time. Acceptance-time checks belong to S08. | `test_incomplete_expired_and_stale_draft` |
| AC-05-05 | Save requested change without changing prices or inventing a status; Admin sees it. Rejection persists rejected status and reason. | Lifecycle test; browser Customer change request visible to Admin |
| Manual provenance / INR | Store manual source and null estimation ID. Calculate amounts using Decimal, round sample tax half-up to paise; never accept client-provided totals. | 3 × ₹10.05 + 18% = ₹35.58; validation tests |
| Portal UI | Preserve shells, show itemized official quote, summary, drawings, history, and responses; use saved totals in editor. Acceptance unavailable. Full settlement replaces historical 60/40 terms. | Native Safari Customer review/request changes; Admin response review/revise/edit/save/issue; desktop and narrow-window screenshots inspected |
| Migration | Apply 001–006 to a disposable PostgreSQL database; add quote/item/decision tables, foreign keys, version uniqueness and status constraints. | `alembic upgrade head` succeeded locally; shared Supabase not migrated |

## Actual checks

- Backend suite at the S07 checkpoint: **89 passed, 1 skipped** (optional PostgreSQL connection test), before separate S08 work appeared in the shared workspace.
- Final focused S07 API tests: **12 passed**, including zero-total/expired issuance, unpublished-history privacy, Origin and provenance tampering.
- PostgreSQL S07 race tests: **3 passed**, using a disposable localhost database and per-test schemas.
- `npm --prefix frontend run build`: passed after the final contrast/selector spacing corrections.
- `git diff --check`: passed.
- Browser: real app/API and PostgreSQL test records on localhost 5191. Verified Customer change request retained ₹45,430.00 and 15-day lead time; Admin saw the response, created v2, saved 12 days, and issued v2. Compared desktop two-column and narrow stacked layouts. Fixed dark heading text on the navy official-quote header.
- Browser initial empty/error states and phone-size emulation were not separately exercised; API empty/private-draft and failure states are tested. Hosted HTTPS/cookie/deployment verification remains pending.

References inspected: `docs/ui-ux/admin/rfqs-and-quotations.webp`, `docs/ui-ux/customer/quotation-review.webp`, `docs/ui-ux/global/ui-kit.webp`. The existing RFQ queue/detail entry is retained; the manual editor extends that workflow. The official-quote area replaces the historical AI comparison because S07 requires manual pricing. No confidence percentages, mock notifications or external messages are introduced.

## Try the workflow

1. Apply migration 006 to the intended development database with `cd backend` then `.venv/bin/alembic upgrade head`, using that environment's configured DATABASE_URL. Restart the backend. Production migration/deployment is a separate operation.
2. Admin → RFQs & Quotations → Inspect Specs → Create / review quotation → Create quotation.
3. Add descriptions, quantities, unit prices, sample tax and lead time; optionally set a future validity date and notes. Save draft, check saved totals, then Issue quotation.
4. Owning Customer → Requests for Quotation → open RFQ → Review quotations. Review line items and send Request changes or Reject quotation with a reason.
5. Admin opens that RFQ again, sees responses in version history, and creates a revised draft. The prior offer is superseded immediately; save and issue the new version.

Rerun focused tests with `backend/.venv/bin/python -m pytest backend/tests/test_quotations_s07.py -q`. To run real races, set `S07_POSTGRES_TEST_URL` to a dedicated localhost PostgreSQL database ending in `_test`, then run `backend/tests/test_quotations_s07_postgres.py`. It creates/drops only uniquely named disposable schemas. Do not point these tests at the shared application database.

## Reopened S07 follow-up — quotation from a submitted RFQ (2026-11-20)

The original flow correctly linked quotations to RFQs but always opened an empty draft, hiding the requirement context. Admin now has explicit **Create quotation from this RFQ** and **Create blank quotation** choices. RFQ-based creation reads the persisted source title/quantity on the server, starts one unpriced line, and preserves the original RFQ ID. Admin still enters official prices and lead time; catalogue prices and customer notes are not automatically treated as commercial terms.

The editor shows the source material, quantity, dimensions, specifications, description, target date, notes and drawing links using the Admin reference's requirement/detail styling. Existing empty drafts offer **Use submitted requirement**, then save into the same draft/version. Populated drafts and revisions are not overwritten. No schema migration is needed.

Regression evidence: **14 focused S07 API tests passed**, including Customer submission → Admin login → review → RFQ-based draft → manual pricing → issue → owning Customer review. The test verifies one RFQ remains and original requirements are unchanged. Explicit blank creation and revision behavior still pass. The production frontend build passed.

Native Safari checks used disposable SQLite fixtures on localhost 5191: new RFQ-based creation populated the source title and quantity 7; an existing blank draft populated title and quantity 3 through **Use submitted requirement**, then saved into the same QT-1 v1. Desktop and narrow-window layouts were inspected against the Admin RFQs/quotations and global UI references. Requirement context sits beside pricing on desktop and follows the established stacked layout at narrow widths. No Supabase business records were altered during verification. Phone-size and hosted verification remain pending for this follow-up.
