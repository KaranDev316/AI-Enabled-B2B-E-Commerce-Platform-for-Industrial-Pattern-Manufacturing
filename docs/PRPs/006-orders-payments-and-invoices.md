# PRP-006 — Orders, simulated payments, and invoices

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-18–REQ-21. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Customer and Admin can inspect the same order and invoice, record demonstration settlement safely, and distinguish unpaid work from work ready for assignment.

## Requirements

### REQ-18 — Authorized users can inspect orders and their lifecycle

- **Actor** — Owning Customer and Admin; Employee through assigned work only.
- **Trigger** — Opens an order list/detail or customer tracking page.
- **Success** — Lists and details show stored product/requirement, quantity, accepted amount, payment state, production state, and recorded dates. Customer sees its own orders; Admin sees operational orders. Tracking distinguishes production stages from dated updates and marks estimates as estimates.
- **Failure** — Unknown records, unauthorized access, empty lists, and retrieval failures have clear states. A stale page cannot authorize an invalid mutation.
- **Constraints** — Accepted snapshots survive product/price/tax edits. One job drives order progress. Full settlement permits confirmation; separate production completion, delivery, and closure follow PRP-007.
- **Source** — CONTEXT §§3, 5–6, 10–11.

### REQ-19 — Simulated payments support partial settlement safely

- **Actor** — Owning Customer making a demonstration payment, or Admin recording a simulated payment.
- **Trigger** — Submits a positive payment against an outstanding invoice.
- **Success** — A successful payment appears in history and reduces outstanding balance by its amount. Failed attempts do not reduce the balance. Full settlement confirms the order and permits assignment. Matching retries using the same idempotency key return the original result.
- **Failure** — Reject zero/negative amounts, overpayment, wrong ownership, payments against cancelled orders, and reused keys with different payment details. Concurrent submissions cannot exceed the remaining balance. Network uncertainty prompts retrieval/retry of the same operation rather than a claimed success or a fresh charge.
- **Constraints** — Outstanding equals stored total minus successful simulated payments. Decimal INR, serialized balance changes, uniqueness, and atomic payment/confirmation changes are mandatory. Payment forms collect no real card, bank, or UPI credentials. Every payment action is visibly a demonstration.
- **Source** — CONTEXT §§6, 8 and user payment/idempotency fixes.

### REQ-20 — Authorized users can view and download the issued demo invoice

- **Actor** — Owning Customer and Admin.
- **Trigger** — Opens invoice details, payment history, or downloads the invoice.
- **Success** — One invoice per order displays accepted itemization, subtotal, sample tax percentage/amount, total, successful payments, and outstanding balance. A downloadable invoice contains the same commercial snapshot and identifies the academic demonstration.
- **Failure** — Unauthorized downloads fail. Download generation failure leaves the issued invoice and payments intact and reports a retryable error.
- **Constraints** — Changing product prices or tax settings cannot recalculate an issued invoice. Payment history changes settlement, not its original total. Do not create an extra invoice on download/retry. No real tax-compliance claim or email sending is introduced.
- **Source** — CONTEXT §§3, 6, 8, 11.

### REQ-21 — Customer can cancel only an entirely unpaid awaiting-payment order

- **Actor** — Owning Customer.
- **Trigger** — Confirms cancellation of an eligible order.
- **Success** — The order is marked cancelled without removing its history. It cannot subsequently receive payments or production assignment.
- **Failure** — Reject cancellation after any successful partial/full payment, after confirmation, or for another customer's order. A cancellation/payment race must produce one consistent outcome with no cancelled-and-paid order.
- **Constraints** — Eligibility requires awaiting payment and zero successful payments. Failed attempts alone do not block cancellation. No refunds, payment reversals, or post-payment cancellation workflow.
- **Source** — CONTEXT §6 and its explicit cancellation consistency resolution.

## Journeys

An accepted quote creates an awaiting-payment order. Customer pays part of the invoice in demo mode, sees the remaining balance, then settles it. Admin can now assign work. Repeating either payment with the same key does not duplicate it.

A customer cancels before any successful payment. A later payment is blocked. A second customer who has made a partial payment cannot cancel through this workflow.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-06-01 | REQ-18 | Owner/Admin see consistent records; another customer cannot retrieve them |
| AC-06-02 | REQ-18 | Tracking separates stage, percentage, dated updates, and estimated completion |
| AC-06-03 | REQ-19 | Partial success reduces outstanding; failure does not; final settlement confirms |
| AC-06-04 | REQ-19 | Matching retry returns the original result; differing key reuse conflicts |
| AC-06-05 | REQ-19 | Concurrent payments cannot overpay; invalid amounts and credentials are not accepted |
| AC-06-06 | REQ-20 | Download agrees with stored snapshot after product/tax edits and creates no duplicate invoice |
| AC-06-07 | REQ-21 | Only a zero-successful-payment awaiting-payment order can be cancelled |
| AC-06-08 | REQ-19, REQ-21 | Concurrent cancellation/payment leaves an eligible single consistent outcome |

## Dependencies, risks, and exclusions

PRP-005 creates the order/invoice. PRP-007 requires settled confirmation before assignment and settlement before closure. PRP-010 reports stored payments. Money integrity, duplicate submissions, and races require automated evidence. No gateway, financial institution integration, 60/40 milestone, refund, or real payment credential is in scope.

## UI references

Use Customer My Orders, Order Tracking, Invoices & Payments, and Admin Orders & Production / Invoices & Payments. Replace realistic credential-entry controls with safe demo controls. Do not carry over contradictory sample totals, multiple jobs, notification controls, or AI assistant buttons.
