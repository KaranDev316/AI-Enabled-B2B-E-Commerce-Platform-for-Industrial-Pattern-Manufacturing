# S08 — Acceptance, orders, demo invoices and unpaid cancellation

Implementation and isolated local verification: 2026-11-20. Hosted verification remains pending. The shared Supabase database has NOT been migrated to 007 by this implementation task.

## Scope and implementation

Customer accepts the latest eligible sent quotation. The API locks its parent RFQ, using the same lock as Admin revision, and checks ownership, status, latest version and expiry at action time. Acceptance, one awaiting-payment order, accepted snapshots, one demonstration invoice and the initial history event commit together. A successful retry returns the existing IDs, including after cancellation. An accepted quotation cannot be revised or edited.

Issued descriptions, quantities, unit prices, line totals, tax percentage, subtotal, tax and grand total are copied exactly from the quote. The order's manufactured quantity comes from the RFQ; service-line quantities are not added to the part count. Catalogue and business-profile edits do not recalculate issued records. References use database IDs after allocation, avoiding concurrent count-based number generation. Invoice due dates remain unset unless explicitly supplied to the internal creation helper.

Customer and Admin order/invoice routes are registered in `create_app`, and their existing portal navigation renders the commercial panels. Customer can inspect/download the demo invoice and cancel only an entirely unpaid awaiting-payment order. Cancellation locks the order and preserves the invoice, snapshots, reason and dated history. Admin dashboard order counts and recent rows now use persisted orders. Payment controls remain disabled; real settlement/payment races and production assignment are S09/S10 integrations, not claimed here.

Migration 007 adds commercial snapshots, invoices and order history; enforces a unique quotation link per snapshot and unique invoice per order; adds the quotation foreign key; widens order monetary storage to match quotation precision. Legacy orders without a commercial snapshot remain readable but are not cancellable through the new commercial workflow.

## Contract and evidence

Fixtures are synthetic accounts, RFQs, issued quotations and commercial records in isolated SQLite or guarded localhost PostgreSQL databases. No shared Supabase business records were created or changed.

| Acceptance source | Action and expected persisted state | Evidence |
| --- | --- | --- |
| AC-05-02/04, AC-05-06 | Owning Customer accepts current unexpired sent quote; invalid status, expired, superseded, unauthorized and untrusted/CSRF requests create no commercial records. Accepted quote cannot be edited/revised. | `test_acceptance_s08.py` uses the actual `create_app` routes |
| AC-05-07 | Repeat and concurrent acceptance return exactly one existing order/invoice pair. | Integrated retry test; real PostgreSQL concurrent acceptance test |
| AC-05-08 | Inject an invoice INSERT failure after order work begins; quote stays sent and no partial order/snapshot/invoice remains. Acceptance versus revision permits only one consistent outcome. | Independently committed SQLite rollback test; PostgreSQL parent-lock race |
| AC-06-01 | Owner/Admin lists, detail and download show the same stored records; Customer 2 and Employee cannot retrieve other accounts' commercial data. | Actual-app integration and standalone commercial tests |
| AC-06-06 / AC-02-05 | Catalogue price/name/deactivation and profile/RFQ changes do not alter accepted items, tax or totals. Download retry creates no new invoice. | Actual accepted-order snapshot test plus download/immutability test |
| AC-06-07 | Zero-payment awaiting order cancels; invoice marked cancelled; reason/history retained. Paid/confirmed guards use controlled settlement fixtures. Concurrent cancellation yields one cancellation history event. | Standalone cancellation guard tests; real PostgreSQL duplicate-cancellation test; native browser cancellation |
| Persistence | Upgrade 006 → 007 in a fresh PostgreSQL schema while retaining existing users/RFQs/quotations and a legacy order/amount; inspect unique indexes, foreign keys and commercial columns. | `test_migrations_s08.py` passed |

## Checks performed

- Final backend suite with PostgreSQL race/migration checks enabled: **116 passed, 1 skipped**. The skip is the separate optional `TEST_DATABASE_URL` connection smoke check; all S07/S08 PostgreSQL race and migration cases executed. FastAPI emits an existing TestClient deprecation warning.
- Cancellation status/payment-count/paid-amount boundaries and a retryable invoice-generation failure are covered. Failed generation leaves the issued snapshot intact.
- Strengthened accepted-order test verifies a real catalogue-linked RFQ survives subsequent product edits/deactivation without invoice changes.
- `npm --prefix frontend run build` and `git diff --check`: passed.
- Native Safari against a disposable PostgreSQL preview on localhost 5191: Customer accepted a sent quote, saw awaiting-payment order and invoice, inspected invoice itemization, downloaded a demo invoice, cancelled a separate wholly unpaid order, and inspected retained order history. Admin saw matching order/invoice states and amounts; dashboard showed the persisted records. Desktop and narrow-window layouts inspected. Dense tables scroll horizontally within their cards.
- API failure/ownership/empty cases are automated. Browser network-failure and phone emulation were not separately exercised. Vercel/Render HTTPS verification is pending.

## Design references and adaptations

Inspected the actual Customer Orders, Customer Invoices & Payments, Admin Orders & Production, Admin Invoices & Payments, quotation review and global UI-kit references. Existing shells, navigation, colors, card/table structure and Admin detail panes are retained. Duplicate nested headings were removed. Production states, progress, jobs and payment history are not invented. Historical payment milestones and payment-provider fields are omitted. Taxes and invoices are labeled academic demonstrations. Invoice download is an HTML document, not a PDF; the controls say Download Demo Invoice.

## Activation and manual check

1. Apply `007` to the intended application database using `cd backend` then `.venv/bin/alembic upgrade 007`. Restart the backend. Deploy the matching frontend/backend together when publishing.
2. Admin issues a complete manual quotation for an existing customer RFQ.
3. Owning Customer opens the quotation and chooses **Accept & place order**. It must show accepted state plus links to orders/invoice. Retrying **Retrieve order & invoice** returns the same records.
4. Customer and Admin inspect Orders and Invoices. Confirm itemization, sample tax and totals match the issued quote. Download the demo invoice.
5. Customer cancels an entirely unpaid awaiting-payment order. Verify cancelled state, retained invoice and dated reason/history. Acceptance retries must not create a replacement order.

For reproducible PostgreSQL checks, set `S07_POSTGRES_TEST_URL` to a dedicated localhost database ending in `_test`. Concurrency tests and migration tests create/drop only uniquely named disposable schemas. Do not use the shared application database.

S08 is implemented and locally verified. Shared migration, deployment and hosted workflow verification remain required before claiming hosted completion. The separate multi-tab session synchronization issue remains outside this slice.
