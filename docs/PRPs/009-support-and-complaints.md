# PRP-009 — Unified support and complaints

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-30–REQ-32. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Customer can raise an inquiry or complaint and follow Admin's response in one ticket conversation. Admin can review, reply, and resolve the same record.

## Requirements

### REQ-30 — Customer can create and inspect an owned support ticket

- **Actor** — Customer.
- **Trigger** — Submits a support request with type, subject, description, optional related order, and optional attachments.
- **Success** — Ticket is saved with an identifier, owner, submission time, status, and supplied details. Related order belongs to that customer. It appears in the customer's list and Admin's support queue.
- **Failure** — Missing fields, another customer's order, unsupported/oversize files, or failed persistence produce clear feedback without a false submitted state.
- **Constraints** — Use unified `support_tickets` and `support_messages`. Attachments accept JPG/JPEG, PNG, PDF with at most two per submission and 20 MB per file. Shared private-file rules apply. No separate Inquiry or Complaint entity/page.
- **Source** — CONTEXT §§3, 5–7, 11 and Customer Support & Complaints.

### REQ-31 — Customer and Admin can exchange ticket messages

- **Actor** — Owning Customer and Admin.
- **Trigger** — Opens the conversation or submits a reply.
- **Success** — Saved messages appear in chronological order with author and timestamp, linked to the same ticket. Each participant can distinguish customer messages from Admin responses. Customer documents remain limited to authorized access.
- **Failure** — Empty/failed/unauthorized replies are not shown as saved. Another customer or Employee cannot retrieve or contribute to the conversation by guessing a ticket identifier.
- **Constraints** — This is support correspondence attached to a ticket, not standalone chat or an AI conversation. No email, notification, live-chat presence, or real-time messaging infrastructure is required.
- **Source** — CONTEXT §§3, 5–6, 10–11 and redesigned Admin Support & Tickets conversation.

### REQ-32 — Admin can manage ticket status and Customer can follow resolution

- **Actor** — Admin; owning Customer as reader.
- **Trigger** — Admin reviews or resolves a ticket, or either participant filters/opens ticket status.
- **Success** — Queue/detail/customer views agree on Open, In Progress, or Resolved status and recorded updates. Admin's resolution response remains visible in the conversation. Customer can filter and inspect its tickets and responses.
- **Failure** — Unauthorized status changes and stale conflicting updates fail without an incorrect success indicator. A retrieval failure is distinguishable from an empty queue.
- **Constraints** — These three statuses normalize the mockup's Pending/In Review labels to the same open/in-progress/resolved concepts. No Sales/Finance queues, configurable support roles, SLA automation, or separate notification timeline. Employee production issues remain in PRP-007.
- **Source** — CONTEXT §§3, 6, 10 and Admin/Customer support designs.

## Journeys

Customer raises an order-related complaint. Admin opens the ticket, marks it In Progress, and replies. Customer adds context to the same conversation. Admin provides a resolution and marks it Resolved. The owner sees the complete response history and final status.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-09-01 | REQ-30 | Valid ticket with/without own related order appears for owner and Admin |
| AC-09-02 | REQ-30 | Invalid fields, unrelated order, and disallowed files are rejected safely |
| AC-09-03 | REQ-31 | Customer/Admin messages preserve author, time, order, and ticket association |
| AC-09-04 | REQ-31 | Another customer/Employee cannot read or reply, including attachment access |
| AC-09-05 | REQ-32 | Admin status changes appear consistently in lists/details and owner view |
| AC-09-06 | REQ-31, REQ-32 | Failed replies/status updates do not fabricate messages or a resolved result |

## Dependencies, risks, and exclusions

PRP-001 owns account access and PRP-006 owns related-order validation. Shared upload requirements are defined in CONTEXT §7 and the master PRP. Avoid exposing internal production notes or other customers' orders through a support association. Admin-created tickets on behalf of customers, assignment queues, internal-note subsystems, ticket export, and additional analytics are not required by the approved scope.

## UI references

Use Customer Support & Complaints and the redesigned Admin Support & Tickets conversation design. The alternative details panel can remain a view of the same ticket. Screenshot controls alone do not add Create Ticket, Assign To, internal Add Note, or export workflows.
