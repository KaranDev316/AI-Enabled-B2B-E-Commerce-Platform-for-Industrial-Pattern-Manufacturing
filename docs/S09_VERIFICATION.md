# S09 — Safe simulated invoice settlement

Status: implemented and verified with isolated automated tests, 2026-11-21. Shared migration **008** and local startup were approved and verified on 2026-11-21. Browser/hosted workflow verification remains pending. This record does not claim deployment or slice closure.

## Implemented behavior

An owning Customer or Admin records a positive INR installment against an outstanding demo invoice. `POST /api/invoices/{invoice_id}/payments` accepts only amount, UUID idempotency key and the explicit demo outcome (`succeeded` or `failed`). Real payment credential fields are rejected. Standard session, ownership, Origin and CSRF checks apply.

Successful installments reduce the balance. Failed attempts remain in history without changing settlement or blocking an otherwise eligible cancellation. The final successful installment marks the invoice paid, confirms the order and adds one dated confirmation event. Admin order responses expose assignment eligibility; creating/assigning production jobs remains S10.

Payments and cancellation lock the same parent order before reading authoritative settlement. The successful payment ledger is summed and checked against cached invoice/snapshot balances before recording another attempt. An unexplained pre-existing settlement mismatch is rejected for review rather than silently changed. A database unique constraint protects each global payment key. Matching retries return the original attempt even after final settlement/cancellation; changed invoice, amount or outcome with the same key conflicts. Failed database work rolls back the ledger, balances and confirmation together.

Invoice detail and downloadable HTML include persisted successful/failed history and current settlement. Accepted items, tax and totals remain unchanged. Customer/Admin lists and open details refresh through existing sync/polling behavior. The four commercial panels' pre-existing hook initialization order was corrected so they render without accessing callbacks before initialization.

The payment form saves its key and exact details in tab storage before submission. A network error, unreadable response or uncertain server failure retains that attempt and offers an explicit same-key retry, including after reload. Inputs stay locked for an unresolved attempt. A known successful/failed result clears the pending operation; an explicit business rejection allows correction. Login does not automatically replay a payment.

## Contract and evidence

| Acceptance | Expected persisted result | Evidence |
| --- | --- | --- |
| AC-06-03 | Failed attempt leaves balance unchanged; partial success reduces balance; full settlement confirms once | `test_partial_failed_final_settlement_and_download` |
| AC-06-04 | Matching retry returns the same ID/result; changed details conflict; concurrent same-key submissions store one payment | `test_matching_retries_and_different_payload_conflicts`; `test_concurrent_same_key_returns_original`; `test_global_key_reuse_across_invoices_conflicts` |
| AC-06-05 | Invalid/over-limit amounts, wrong ownership, missing CSRF/untrusted Origin and real credential fields fail without payment writes | `test_invalid_amounts`; `test_overpayment_ownership_auth_csrf_origin_and_no_credentials`; `test_concurrent_overpayment_is_blocked` |
| Atomicity | Injected confirmation failure leaves no payment or settlement/confirmation changes; same-key retry succeeds | `test_payment_rollback_then_same_key_retry` uses independently committed fixtures |
| AC-06-06 | Stored item/tax/total snapshot survives settlement; one invoice downloads current balance and attempt history | S09 actual-app flow plus existing S08 snapshot tests |
| AC-06-07/08 | Failed attempts permit unpaid cancellation; any success blocks it; concurrent payment/cancellation has one consistent outcome | `test_failed_attempt_allows_cancellation_and_exact_retry_after_cancel`; `test_payment_cancellation_race_has_one_consistent_outcome` |
| S10 boundary | Partial payment is ineligible; full settlement enables eligibility without creating a job | Actual-app installment test; `test_concurrent_installments_confirm_once` |
| Persistence | Upgrade 007 → 008 retains issued invoice snapshot; constraints and a first payment work | `test_s09_upgrade_preserves_invoice_and_enforces_payment_constraints` |
| Uncertain response | Lost response/reload reuses original key and content; definitive rejections differ from uncertain errors | `frontend/tests/demoPayments.test.js` |
| Render regression | All four commercial panels render; demo form shows amount/outcome and preserves a pending retry on a paid invoice | `frontend/tests/commercialRender.test.js` |

## Checks performed

- Full backend suite with `S07_POSTGRES_TEST_URL` pointing to a dedicated localhost PostgreSQL test database: **138 passed, 1 skipped**. All S09 race/migration checks and startup checks ran. The skip is the separate optional `TEST_DATABASE_URL` smoke check. Existing FastAPI/Alembic deprecation warnings remain.
- `node --test frontend/tests/*.test.js`: **5 passed**.
- `npm --prefix frontend run build` and `git diff --check`: passed.
- Automated fixtures are isolated; no customer/admin accounts, invoices or payment records were created in shared Supabase.
- With explicit user approval, the normal startup entry point completed migration activation. A read-back confirmed Supabase revision **008** and the `simulated_payments` table. The local backend started on **127.0.0.1:8001**; its health endpoint passed and OpenAPI includes the S09 payment endpoint.
- Native browser automation failed to initialize. Desktop/mobile visual comparison, browser clicks and the hosted workflow were not verified. Server rendering checks do not substitute for those checks.

## Design references and adaptations

Inspected `docs/ui-ux/customer/invoices-and-payments.webp`, `admin/invoices-and-payments.webp` and `global/ui-kit.webp`. Existing Customer invoice modal and Admin invoice detail pane, KPI cards, tables, colors and controls are retained. Added the payment history and demo amount/outcome form inside those existing surfaces. Real bank/card/UPI entry from historical mockups is replaced with explicit simulation controls; no new payment framework or gateway is introduced. Tables retain horizontal overflow support and amount/outcome fields stack at narrow widths. Layout behavior still requires native browser verification.

## Activation and manual verification

1. With authorization for the target database, run `cd backend` then `.venv/bin/python start.py`. The existing startup process applies pending revisions, including **008**, before serving on port **8001**. Render must use the same startup path when this commit is deployed.
2. Use an accepted S08 quotation's unpaid invoice. Customer → Invoices → Demo Payment opens the existing invoice detail modal. Record an explicit failed demo attempt; confirm history appears and balance stays unchanged.
3. Record a successful partial installment. Customer/Admin must see the same paid/remaining amounts; cancellation and production assignment remain unavailable.
4. Settle the remaining amount. Confirm one order confirmation, paid invoice, zero balance and Admin assignment eligibility. Download the invoice and compare amounts/history.
5. Retry an operation whose response was lost using **Retry Same Demo Attempt**, including after reload. Confirm there is no duplicate installment. Concurrent amount/key/cancellation cases have automated PostgreSQL evidence above.
6. Check a separate wholly unpaid order can still be cancelled after failed attempts and cannot receive a subsequent new payment. Check another Customer and Employee cannot access or pay the invoice.
7. Compare desktop and narrow-screen controls with references, then deploy matching frontend/backend and repeat the owner/Admin workflow over Vercel/Render HTTPS before closing S09.
