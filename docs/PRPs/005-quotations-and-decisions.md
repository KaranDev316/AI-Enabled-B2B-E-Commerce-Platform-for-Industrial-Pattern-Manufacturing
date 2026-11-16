# PRP-005 — Versioned quotations and customer decisions

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-14–REQ-17. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Admin issues an itemized manufacturing offer. Customer can review, reject, request changes, or accept the current eligible version. Acceptance creates one traceable commercial record for the academic demonstration.

## Requirements

### REQ-14 — Admin can prepare and revise quotation versions

- **Actor** — Admin.
- **Trigger** — Prepares a quotation for an RFQ or revises an unaccepted quotation.
- **Success** — Each version retains item descriptions, quantities, prices, subtotal, sample tax percentage/amount, total, lead time, optional validity, and pricing provenance. Version numbers increase within the RFQ. Creating a new version supersedes the preceding unaccepted version, including when the new version is still a draft.
- **Failure** — Invalid values fail visibly. Conflicting simultaneous revisions cannot create duplicate version numbers or two current versions. Accepted quotations cannot be edited or superseded.
- **Constraints** — INR decimal calculations and immutable accepted snapshots follow CONTEXT §6. Use only draft, sent, accepted, superseded, expired, and rejected quotation statuses. Preserve prior versions for review. No automatic estimate-to-official-price approval.
- **Source** — CONTEXT §§6–7, 11.

### REQ-15 — Admin can issue a quotation and Customer can inspect eligibility

- **Actor** — Admin and owning Customer.
- **Trigger** — Admin sends a complete quotation or Customer opens its review page.
- **Success** — The sent version is available in the Customer Portal with full itemization, official lead time, optional validity, pricing-source information, and decision controls appropriate to its eligibility. Previous versions remain distinguishable.
- **Failure** — Incomplete drafts cannot be issued. Customer cannot accept a draft, expired, superseded, rejected, or another customer's quotation. Expiry is checked at action time even if its stored status is stale.
- **Constraints** — Eligible means highest version number for the RFQ, status sent, and unexpired when `valid_until` exists. Issuing makes the quotation available in the portal; it does not send email or notifications.
- **Source** — CONTEXT §§3, 5–6, 10.

### REQ-16 — Customer can reject or request changes

- **Actor** — Owning Customer.
- **Trigger** — Reviews the current sent quotation and chooses reject or request changes.
- **Success** — Rejection records the rejected status. A change request records the customer's requested revision for Admin review. Admin prepares any revised offer through REQ-14 so prior values remain traceable.
- **Failure** — Stale or unauthorized decisions do not overwrite a newer version or accepted offer. A failed decision is not presented as saved.
- **Constraints** — Change requests do not edit official prices directly or introduce a new quotation-status enum. No additional inquiry system or external messaging is required.
- **Source** — CONTEXT §6, quotation decision screen, quotation sequence reference.

### REQ-17 — Customer acceptance creates exactly one order and invoice

- **Actor** — Owning Customer.
- **Trigger** — Accepts the latest valid sent quotation.
- **Success** — Acceptance, one awaiting-payment order, and one demonstration invoice are saved together with accepted commercial snapshots. Repeated acceptance of that already accepted quotation returns its existing order/invoice.
- **Failure** — Expired, stale, unauthorized, or otherwise ineligible first acceptance creates no order. A partial database failure does not leave an accepted quote without the matching order/invoice. Concurrent acceptance/revision cannot accept a superseded version.
- **Constraints** — Enforce one order per accepted quotation and one invoice per order with database constraints and transactional state checks. Retrying a successful acceptance must be distinguished from accepting an ineligible version for the first time. Production cannot start at acceptance.
- **Source** — CONTEXT §§6, 8, 11 and user's idempotency/version rules.

## Journeys

Admin drafts version 1, issues it, and Customer asks for a change. Admin creates version 2, superseding version 1 immediately. Customer reviews and accepts version 2. The portal opens the existing awaiting-payment order and invoice even if the acceptance submission is repeated.

A customer leaves a quotation open while Admin creates a newer draft. The old acceptance attempt is rejected with a current-state explanation. An already accepted quotation remains immutable.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-05-01 | REQ-14 | A newer draft increments the version and prevents acceptance of the former version |
| AC-05-02 | REQ-14 | Accepted versions cannot be edited/superseded; concurrent revisions stay consistent |
| AC-05-03 | REQ-15 | Only the owner sees the offer; incomplete draft cannot be sent |
| AC-05-04 | REQ-15 | Expired validity blocks acceptance even with a stale sent status |
| AC-05-05 | REQ-16 | Rejection and a saved change request are visible to Admin without editing quote values |
| AC-05-06 | REQ-17 | Successful acceptance creates one awaiting-payment order and one invoice |
| AC-05-07 | REQ-17 | Duplicate/concurrent acceptance returns one existing result with no duplicates |
| AC-05-08 | REQ-17 | Failure rollback and concurrent revision preserve quote/order/invoice consistency |

## Dependencies, risks, and exclusions

PRP-001 owns identity/ownership, PRP-003 RFQs, and PRP-004 advisory estimates. PRP-006 owns the resulting order, invoice, and settlement. Version races and stale browser pages are critical risks. Accepted-order amendments, negotiated chat, notification delivery, and purchasing workflows are excluded.

## UI references

Use the Admin RFQs & Quotations and Customer Quotation Review & Decision designs. Replace 60/40 payment milestones with the approved full-settlement-before-confirmation rule. Label sample taxes and academic billing. Remove confidence percentages and AI assistant controls.
