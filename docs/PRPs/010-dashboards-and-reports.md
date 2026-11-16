# PRP-010 — Role dashboards and stored-record reports

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-33–REQ-35. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Each signed-in role sees a useful summary of its permitted work. Admin can inspect basic order, production, and simulated-payment reports and export the displayed information for the academic demonstration.

## Requirements

### REQ-33 — Each role sees a scoped dashboard and recent activity

- **Actor** — Customer, Employee, Admin.
- **Trigger** — Opens the role's dashboard or follows a summary link.
- **Success** — Customer sees its orders, quotations awaiting decision, and production progress. Employee sees assigned work, work in progress, completions, and recent permitted updates. Admin sees RFQs requiring review, operational orders, low-stock indicators, and production issues requiring attention. Links open the corresponding authorized records or filtered list.
- **Failure** — Missing data, no records, and failed retrieval are visually distinct. Summary shortcuts cannot bypass ownership or stage permissions.
- **Constraints** — Counts and recent activity come from stored business records and histories, not screenshot sample values. Reuse one shared sidebar per portal. On-page activity does not introduce notification entities, bells, emails, or subscriptions.
- **Source** — CONTEXT §§3, 5–6, 10 and simplified role dashboard references.

### REQ-34 — Admin can inspect basic business and production reports

- **Actor** — Admin.
- **Trigger** — Selects a report and supported date/status filters.
- **Success** — Order, production, and payment totals reconcile with matching stored records. Dates and filters are visible. Orders received use order creation date; completions use approved completion/closure events as labeled; payments received use successful simulated payment dates. Production summaries distinguish current stages from completed work.
- **Failure** — Invalid date ranges produce feedback. No matching records shows zero/empty results. Retrieval failure never becomes a plausible fabricated chart or total.
- **Constraints** — Label whether a measure is a current snapshot or activity during the selected period. Distinguish billed totals, successful simulated payments, and outstanding balances. Label synthetic/demo data and manual versus AI-assisted pricing when pricing-source information is shown. No predictive business analytics or claimed real revenue.
- **Source** — CONTEXT §§3, 6–7, 10 and Admin Reports reference.

### REQ-35 — Admin can export the report's filtered records as CSV

- **Actor** — Admin.
- **Trigger** — Chooses CSV export from a supported report.
- **Success** — Downloaded CSV matches the selected report scope and filters, has clear headers and units, and includes the complete filtered result rather than only the visible page. Dates, statuses, and monetary values agree with the UI.
- **Failure** — Unauthorized export is denied. Export failure reports an error without an apparently successful empty file. Legitimately empty results produce a clearly empty, header-bearing report.
- **Constraints** — Export only report-relevant fields, excluding credentials, tokens, and private file URLs. Escape CSV correctly and prevent user-controlled cell content from executing spreadsheet formulas. No scheduled email exports or spreadsheet integration.
- **Source** — CONTEXT §§3, 6, 8, 10 and approved CSV reporting scope.

## Journeys

Admin opens the simplified dashboard and follows a pending RFQ to review it. Later, Admin filters payment activity for a period and exports CSV. Successful simulated payment totals match the underlying payment history. Customer and Employee dashboards show only their own permitted work throughout the same workflow.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-10-01 | REQ-33 | Role dashboards agree with corresponding authorized lists |
| AC-10-02 | REQ-33 | New stored activity updates summaries; unrelated users' data never appears |
| AC-10-03 | REQ-34 | A known demo dataset reconciles order, production, and payment figures |
| AC-10-04 | REQ-34 | Date boundaries, zero results, invalid ranges, and retrieval failure remain distinguishable |
| AC-10-05 | REQ-35 | CSV includes the full filtered result and matches displayed headers/units/totals |
| AC-10-06 | REQ-35 | CSV escaping/formula safety works and forbidden sensitive fields are absent |
| AC-10-07 | REQ-33–REQ-35 | No notification, AI assistant, supplier, or configurable-role feature enters reporting UI |

## Dependencies, risks, and exclusions

Consumes the records owned by PRP-001 through PRP-009. This module cannot define competing order/payment/production statuses. The main risks are inconsistent aggregation, customer-data leakage, misleading date filters, and presenting mockup values as live facts. Advanced BI, forecasting, scheduled reports, separate inventory analytics, and unsupported percentage-growth claims are excluded from the required reports.

## UI references

Use the final simplified Admin Dashboard, Customer Dashboard, simplified Employee Dashboard, and Admin Reports. Retain basic charts only when backed by defined stored-record measures. Remove notifications, AI recommendations, supplier/configurable-role navigation, and unsupported metrics.
