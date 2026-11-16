# PRP-007 — Production, quality review, and delivery

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-22–REQ-26. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Admin assigns confirmed work. Employee performs and reports that work. Admin retains responsibility for quality approval, delivery, and closure. Customer can follow the resulting production status.

## Requirements

### REQ-22 — Admin can assign one production job to one employee

- **Actor** — Admin.
- **Trigger** — Assigns a fully settled, confirmed order to an active Employee.
- **Success** — One job is associated with the order and one employee. The employee can see its requirements, instructions, and authorized files in My Tasks. Initial production stage is Design & Tooling.
- **Failure** — Unpaid/cancelled orders, inactive/non-employee assignees, and duplicate job creation are rejected. Concurrent assignment cannot create multiple jobs for an order.
- **Constraints** — One order has at most one job. No simultaneous multi-employee assignment, sub-jobs, scheduling optimizer, or automatic material reservation. Assignment permissions are enforced on the backend.
- **Source** — CONTEXT §§5–6, 8, 11 and explicit one-order/one-employee decision.

### REQ-23 — Assigned Employee can update progress and production stages

- **Actor** — Assigned Employee.
- **Trigger** — Starts assigned work, updates progress, pauses/resumes work, or advances production toward quality review.
- **Success** — Saved progress is between 0 and 100 percent and becomes the order's production progress. Design & Tooling advances to Machining/Production, then submitted work enters Quality Check. Every stage transition records previous/new stage, actor, time, and note in `job_stage_history`. Temporary pauses remain visible to Admin.
- **Failure** — Unassigned users and invalid transitions fail. A stale update cannot overwrite an Admin quality decision. A failed save leaves the last persisted state intact.
- **Constraints** — Employee cannot approve its own completion, mark delivery, or close the order. A displayed 100 percent is insufficient for completion. Customer-visible progress remains distinct from internal instructions and issue details.
- **Source** — CONTEXT §§5–6, 8 and revised My Tasks / tracking designs.

### REQ-24 — Admin can approve quality or return work for rework

- **Actor** — Admin.
- **Trigger** — Reviews a job submitted at Quality Check.
- **Success** — Approval moves the job to Completed. Return moves it to Machining/Production with a required rework note and updated progress reflecting remaining work. Both outcomes appear in stage history. Reworked work must be submitted for quality review again.
- **Failure** — Employee approval, approval outside Quality Check, a return without a note, or conflicting simultaneous decisions are rejected. No duplicate transition is recorded as a new approval on an already-completed job.
- **Constraints** — Quality approval is an explicit Admin action. Completed job views retain instructions, progress/history, and authorized attachments. Completion does not by itself record delivery or close the order.
- **Source** — CONTEXT §6 and user rework/history fix.

### REQ-25 — Employee can report production issues and inspect their status

- **Actor** — Employee and Admin.
- **Trigger** — Employee reports a production, machine, or material issue, optionally related to an assigned job; Admin reviews or updates its status.
- **Success** — Issue captures type, title, description, priority, and optional permitted attachments. Employee can inspect its reported issues and status. Admin can review and record the issue's handling status. A reported issue or pause does not create another job.
- **Failure** — Missing required fields, another employee's job association, invalid attachments, or unauthorized changes fail without false success.
- **Constraints** — Attachments allow JPG/JPEG, PNG, PDF; maximum two per submission and 20 MB each. Apply shared private-file rules. Production issues remain distinct from Customer support tickets. No machine integration or notification delivery is required.
- **Source** — CONTEXT §§3, 5–7 and Employee Report Issue reference.

### REQ-26 — Admin can record delivery and close an eligible order

- **Actor** — Admin.
- **Trigger** — Records delivery after completed production, then closes the order.
- **Success** — Delivery and closure are separately recorded, visible lifecycle events. Both require the job to have passed Admin quality review and the invoice to be fully settled. Customer sees the recorded delivered/closed result.
- **Failure** — Incomplete/reworked production, unsettled invoices, employee/customer attempts, or closure before recorded delivery are rejected. Repeated submissions do not create duplicate delivery/closure events.
- **Constraints** — No GPS, carrier integration, digital proof of delivery, warranty, or casting-trial workflow. Stored dates record actions honestly, not invented estimated completion as fact.
- **Source** — CONTEXT §§5–6, 10.

## Journeys

Admin assigns a confirmed order. Employee progresses through Design & Tooling and Machining/Production, then submits for quality review. Admin returns it with a rework note. Employee performs the correction and resubmits. Admin approves, later records delivery, and closes the order. History retains every transition, including the return.

Employee reports a machine issue and pauses work. Admin can see the issue and pause while the same job remains assigned. Customer tracking continues to show saved customer-visible production status.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-07-01 | REQ-22 | Only a fully settled confirmed order can receive one active Employee assignment |
| AC-07-02 | REQ-22 | Concurrent assignment cannot create a second job; unassigned work/files remain inaccessible |
| AC-07-03 | REQ-23 | Valid progress persists and matches the order; out-of-range progress fails |
| AC-07-04 | REQ-23 | Stage transitions retain actor/time/note; pause does not create another job |
| AC-07-05 | REQ-24 | Employee cannot self-approve, and 100 percent alone does not complete work |
| AC-07-06 | REQ-24 | Return requires note/progress, goes to Machining, and requires a new quality submission |
| AC-07-07 | REQ-25 | Employee can report/view an issue; Admin handles status; invalid/private attachments are protected |
| AC-07-08 | REQ-26 | Quality-approved, paid work can be delivered and then closed as distinct events |
| AC-07-09 | REQ-24, REQ-26 | Stale/concurrent/repeated decisions cannot bypass gates or duplicate lifecycle events |

## Dependencies, risks, and exclusions

PRP-001 provides employees and permissions. PRP-003 supplies authorized manufacturing files. PRP-006 establishes settlement and order ownership. PRP-010 consumes stored stages/issues. Inventory stays manual under PRP-008. Exact operation dates and production percentages in screenshots are sample data, not workflow rules.

## UI references

Employee Dashboard, revised My Tasks, Completed Jobs, Report Issue; Admin Orders & Production; Customer Order Tracking & Production Timeline. Remove multi-job tables and employee delivery/closure authority from older designs. Keep production stages and chronological updates visually distinct.
