# S10 — production assignment and progress

Integrated against main ecc81b7 (22 November 2026), including S07 quotations,
S08 commercial orders and S09 simulated payments. Supersedes the earlier S10 ZIP.

Admin: Orders & Production → Production Jobs. Assignment checks the order under a
row lock, invoice ownership and currency, non-cancellation, matching invoice/snapshot
balances and totals, and the sum/count of successful S09 ledger entries. Failed attempts
never count. A unique order FK permits only one job, assigned to one active Employee.
The assignment and order transition to in_production are committed with audit history.
This is still the project's demonstration payment system; no real payment gateway is added.

Employee: My Tasks → select job, inspect authorized RFQ drawings/instructions, update
progress, pause/resume with a note, advance Design & Tooling to Machining / Production,
and submit 100% machining work for Quality Check. Every write uses an expected version;
a stale tab must refresh and reselect its job. 100% alone never completes a job.
Quality approval, rework, delivery and closure remain S11's responsibility.

Customer: My Orders → expand Production Tracking. This is a redacted, read-only
view of the customer's own orders, saved stages, percentages and public updates.
Internal work notes, employee identities, issues and drawings are excluded.
Existing order/payment/cancellation screens and PDF invoices remain available.

Migration 010 follows official main's 008 and integrated inventory 009. Never copy
old 006_inventory.py or 007_production_jobs.py into the latest migration directory.
Run check_samonta_database.py before upgrading an existing development database.

References: admin/orders-and-production.webp, employee/my-tasks.webp,
employee/completed-jobs.webp, employee/dashboard.webp, customer/order-tracking.webp,
and global/ui-kit.webp. Unsupported screenshot sample dates and metrics are not copied.
No new layout, sidebar, route or dependency was introduced. Private drawings use the
current per-tab ProtectedDownload/ProtectedPreview flow.
