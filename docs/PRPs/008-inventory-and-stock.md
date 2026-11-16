# PRP-008 — Manual inventory and stock history

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-27–REQ-29. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Admin maintains material quantities and can explain every stock change during the demonstration. Stock visibility supports operations without introducing procurement or automatic consumption.

## Requirements

### REQ-27 — Admin can maintain inventory material records

- **Actor** — Admin.
- **Trigger** — Adds or edits a material, searches inventory, or opens its details.
- **Success** — Materials have identifiable names/codes, units, current quantities, and minimum-stock thresholds. List/detail views agree. Empty/search-result states are clear.
- **Failure** — Invalid quantities/thresholds, duplicate identifiers, and unauthorized edits fail visibly. Editing descriptive fields cannot silently change stock or erase adjustment history.
- **Constraints** — Preserve the material's quantity unit and history meaning. Initial stock must be explainable through the same reasoned stock history used for later changes. Inventory is Admin-managed; no supplier record is required.
- **Source** — CONTEXT §§3, 6, 10–11.

### REQ-28 — Admin can make reasoned stock additions and deductions

- **Actor** — Admin.
- **Trigger** — Submits a stock adjustment with quantity, direction, and reason.
- **Success** — A valid positive addition/deduction updates stock and appends a history entry with change, reason, actor, and time. Current balance and history stay consistent.
- **Failure** — Reject missing reasons, invalid quantities, or deductions below available stock. Concurrent deductions cannot produce negative stock. Database failure saves neither a lone balance change nor a lone successful history entry.
- **Constraints** — Adjustments and stock change commit atomically. Do not silently rewrite history to correct a mistake; record an explained compensating adjustment. There is no automatic consumption, reservation, or purchase-order effect.
- **Source** — CONTEXT §§6, 8 and approved manual-inventory simplification.

### REQ-29 — Admin can identify low and unavailable stock

- **Actor** — Admin.
- **Trigger** — Opens inventory or its dashboard summary after quantities/thresholds change.
- **Success** — Indicators derive from saved stock and thresholds, distinguishing zero stock, positive stock below its minimum, and adequate stock. Details expose quantity and threshold so the status is explainable.
- **Failure** — Unavailable inventory data produces an error state instead of invented counts or a misleading healthy status.
- **Constraints** — The status is an on-page indicator. It does not create a notification, supplier message, or automated reorder. Equality with the threshold is adequate stock under the “below minimum” display rule.
- **Source** — CONTEXT §§3, 6, 10 and Inventory reference.

## Journeys

Admin creates a material, records its opening stock with a reason, and later makes a manual deduction. The balance falls below its minimum and the inventory/dashboard indicators update. A deduction greater than available stock is rejected, leaving quantity and history unchanged.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-08-01 | REQ-27 | Valid material appears consistently; duplicate/invalid records fail |
| AC-08-02 | REQ-27 | Descriptive edits preserve stock/history and unit meaning |
| AC-08-03 | REQ-28 | Add/deduct actions record amount, reason, actor/time, and matching balance |
| AC-08-04 | REQ-28 | Missing reason and excessive/concurrent deductions cannot corrupt stock |
| AC-08-05 | REQ-28 | A failed adjustment rolls back both balance and history changes |
| AC-08-06 | REQ-29 | Zero, below-minimum, and threshold-or-above cases show consistent indicators |

## Dependencies, risks, and exclusions

PRP-001 owns Admin authorization. PRP-010 reads material quantities and indicators. Orders and jobs do not mutate inventory automatically. Supplier management, purchases, supplier invoices, purchase returns, reorder actions, and reservation/consumption logic are excluded.

## UI references

Use the inventory portion of the supplied Inventory & Suppliers screen, with the navigation label changed to Inventory. Remove the Suppliers tab, supplier details, and Reorder action. Keep material details and adjustment history within the approved scope.
