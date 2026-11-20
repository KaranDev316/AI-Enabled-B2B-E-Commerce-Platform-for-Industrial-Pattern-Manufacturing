# S07 — Manual versioned quotations

Scope: REQ-14, REQ-15, REQ-16 and manual provenance in REQ-13. Acceptance/order/invoice creation remains S08. This record does not close S01/S02 or claim hosted deployment verification.

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
