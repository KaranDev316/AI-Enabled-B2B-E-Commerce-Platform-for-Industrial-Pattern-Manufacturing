# KPC — Master Product Requirements Prompt

Version 1.0 · 2026-11-15 · Final-year BCA project

**Status:** Requirements documentation derived from the approved project baseline. Application implementation and acceptance scenarios are **NOT VERIFIED**.

**Authority:** [CONTEXT.md](CONTEXT.md) governs scope, technology, ownership, and constraints. This PRP and its ten feature documents elaborate that baseline. Earlier screens, slides, diagrams, and sample data cannot independently add features. This document does not replace the context, a detailed data dictionary, or a slice verification contract.

## 1. Product purpose and value

KPC — Khodel Pattern Craft digitizes the B2B workflow for an Ahmedabad manufacturer of wooden and metallic industrial patterns. Customers can find products, submit requirements and drawings, review an official quotation, simulate payment, and follow production. Employees report assigned production work. Admin coordinates products, quotations, orders, quality, inventory, accounts, and support.

The problem is fragmented calls, WhatsApp messages, paperwork, manual stock checks, and repeated follow-up. The academic demonstration should show one coherent, persisted workflow with clear ownership and recoverable failure states. It must remain manageable for a three-person BCA team and free-hosted demonstration.

The core value is traceability from a customer's requirement to an accepted quotation, invoice, assigned job, quality decision, and recorded delivery. Linear regression is an explainable advisory demonstration using synthetic data. Admin remains responsible for official prices and lead times.

## 2. Users and ownership

| Actor | Goals and permitted responsibility |
| --- | --- |
| Visitor | Read company information and active catalogue; register as Customer |
| Customer | Maintain its business profile; submit RFQs; decide on its quotations; inspect orders/invoices; make simulated payments; track production; use support |
| Employee | Inspect assigned job/files; update progress; pause work; report issues; submit production for Admin quality review; inspect completed work |
| Admin | Manage catalogue/accounts; review RFQs; prepare quotations; assign paid orders; review quality; record delivery/closure; maintain manual stock; respond to support; inspect reports |

There is one customer login per business profile. Customer-owned records and private files cannot be shared across customers. Each order has at most one production job and one assigned employee. Fixed roles replace the historical configurable-role and supplier models.

## 3. Document set and reading order

Read this master and CONTEXT first. Use the relevant feature PRP as the requirement source for a subsequent vertical slice. Read its dependencies before specifying cross-feature behavior. Numbering below is a documentation sequence, not a claim that each file is a single implementation task.

| PRP | Feature document | Requirements |
| --- | --- | --- |
| 001 | [Accounts, profiles, and access](PRPs/001-accounts-and-access.md) | REQ-01–REQ-04 |
| 002 | [Public catalogue and product management](PRPs/002-public-catalogue-and-products.md) | REQ-05–REQ-07 |
| 003 | [RFQ submission, review, and files](PRPs/003-rfqs-and-files.md) | REQ-08–REQ-10 |
| 004 | [Advisory price and lead-time estimation](PRPs/004-ai-price-and-lead-time.md) | REQ-11–REQ-13 |
| 005 | [Versioned quotations and customer decisions](PRPs/005-quotations-and-decisions.md) | REQ-14–REQ-17 |
| 006 | [Orders, simulated payments, and invoices](PRPs/006-orders-payments-and-invoices.md) | REQ-18–REQ-21 |
| 007 | [Production, quality review, and delivery](PRPs/007-production-quality-and-delivery.md) | REQ-22–REQ-26 |
| 008 | [Manual inventory and stock history](PRPs/008-inventory-and-stock.md) | REQ-27–REQ-29 |
| 009 | [Unified support and complaints](PRPs/009-support-and-complaints.md) | REQ-30–REQ-32 |
| 010 | [Role dashboards and stored-record reports](PRPs/010-dashboards-and-reports.md) | REQ-33–REQ-35 |

All 35 functional requirements are **Must** within the approved final scope. There is no optional future-feature backlog. Each requirement has one owning feature document with actor, trigger, success, failure, constraints, and source. `AC-xx-yy` identifies its product-level acceptance scenarios. A future implementation verification contract should reference these IDs without redefining them.

## 4. Canonical end-to-end journey

1. Visitor browses the landing page, catalogue, and product details. Customer registers or signs in and maintains its business contact information.
2. Customer submits a three-step RFQ for an existing product or custom requirement, optionally attaching up to two allowed files of up to 20 MB each.
3. Admin reviews the stored RFQ and drawings. Admin may request an advisory estimate, then prepares and issues an official itemized quotation.
4. Customer reviews the current offer and accepts, rejects, or requests changes. Revised quotations retain version history. Only the highest, sent, unexpired version can be accepted for the first time.
5. Successful acceptance atomically creates one awaiting-payment order and one demo invoice. Duplicate acceptance returns the existing result.
6. Positive partial simulated payments reduce outstanding balance. Full settlement confirms the order. Admin then assigns one job to one active employee.
7. Employee records Design & Tooling and Machining/Production progress, then submits the job for Quality Check. Admin approves completion or returns it to Machining/Production with a rework note and updated progress.
8. After approved completion and full settlement, Admin records delivery and closes the order as distinct events. Customer sees the saved lifecycle and invoice history.
9. Support conversations, manual inventory adjustments, role dashboards, and basic reports support this workflow using their own authorized persisted records.

### Alternative and failure journeys

| Situation | Required result |
| --- | --- |
| Model unavailable or unsupported inputs | Explain unavailability; allow manual quotation with null estimate reference and manual pricing source |
| New quotation version exists | Older unaccepted version is superseded immediately, even while the newer version is draft |
| Quotation expires while page is open | Acceptance checks current validity and rejects the expired offer |
| Acceptance or payment response is lost | Retry retrieves the existing matching result; no duplicate order/invoice/payment |
| Partial simulated payment | Balance decreases; order remains awaiting payment; assignment and cancellation remain blocked |
| Failed simulated payment | No balance reduction; failure remains distinguishable from success |
| Entirely unpaid order is cancelled | Preserve its history; prevent subsequent payment and assignment |
| Quality review returns work | Record rework transition/note; same job returns to Machining and must be resubmitted |
| Upload or metadata write fails | Report failure and reconcile partial objects/metadata; do not claim a broken attachment succeeded |
| Session expires or account is deactivated | Protected access stops; no automatic replay of an unfinished mutation after login |

## 5. Shared business invariants

These are cross-feature rules. Feature PRPs specify their user-visible consequences.

- **Identity:** Canonical users with fixed roles, customer/employee profiles, and server-managed sessions. Registration cannot grant privileged roles.
- **Quotation authority:** Admin controls official prices/lead time. Accepted quotations are immutable. A newer draft blocks old acceptance. The first acceptance requires current eligibility; retry of an already successful acceptance returns its original order/invoice.
- **Commercial consistency:** INR decimal values. Accepted line items, subtotal, tax percentage/amount, and total are stored snapshots. Sample taxes and billing are labeled academic demo data.
- **Settlement:** Outstanding is stored total minus successful simulated payments. Positive partial payments are allowed; overpayment is forbidden. Full settlement is required before confirmation/assignment. No 60/40 milestone.
- **Cancellation:** Only awaiting-payment orders with zero successful payments can be cancelled. Refunds and post-payment cancellation are excluded.
- **Production authority:** Employee submits work; Admin approves or returns it. A percentage alone cannot complete a job. One job drives one order's progress without aggregation.
- **History:** Stage transitions retain previous/new stage, actor, timestamp, and note. Rework requires a note. Stock adjustments retain reason and history. Support messages retain author/time.
- **Inventory:** All changes are manual. Deductions cannot exceed stock. Orders/jobs never automatically reserve or consume material.
- **Files:** Private persistent storage and authorized preview/download. Images/PDF preview; CAD download only. RFQ maximum is two files total, each at most 20 MB. Other attachment submissions allow at most two files of 20 MB each.
- **Estimation:** Offline synthetic-data linear regression, reproducible held-out evaluation, saved preprocessing/version. No request-time training or confidence percentage. Save estimate provenance separately from Admin's official quotation.

## 6. Shared quality and security requirements

All are Must. These are scoped product/engineering constraints, not invented throughput or availability promises.

| ID | Requirement | Required evidence at verification |
| --- | --- | --- |
| NFR-01 | Enforce role, record ownership, and active-account/session checks on every protected action, file access, and export | Cross-customer and unassigned-employee access fails; logout/reset/deactivation/expiry stop access |
| NFR-02 | Protect cookie mutations with trusted Origin checks and session-bound CSRF tokens; use the approved cookie/session/hash rules | Rejected absent/null/untrusted Origin on browser mutations, including login; rejected missing/invalid token for authenticated changes; valid same-origin flow succeeds |
| NFR-03 | Validate inputs on backend and provide consistent error code/message/optional field feedback; distinguish loading, empty, invalid, denied, conflict, and server failure | Invalid input causes no unauthorized state change; browser retains recoverable form input; failure is not shown as success |
| NFR-04 | Preserve transactional and concurrency integrity across quotations, acceptance, payments, assignments, quality decisions, and stock | Duplicate/concurrent submissions satisfy invariants; rollback leaves no partial commercial or inventory record |
| NFR-05 | Enforce backend file count/streamed size/extension/content checks and private storage permissions | Boundary and mismatch tests; cross-record download denial; partial storage/database failure cleanup |
| NFR-06 | Keep credentials, session/CSRF tokens, database/storage secrets, and uploaded contents out of logs/public configuration/exports | Configuration and output inspection; no real payment credentials are collected |
| NFR-07 | Keep summaries, histories, invoices, estimates, and reports truthful and traceable to saved records | Known demo fixtures reconcile views/exports; synthetic data and demo money clearly labeled; manual pricing source retained |
| NFR-08 | Use one shared sidebar per portal and consistent navy/orange visual language; usable labeled forms and non-color-only status feedback | Browser review of core desktop workflows, keyboard-accessible controls, clear labels and loading/error/empty states; landing page retains supplied mobile intent |
| NFR-09 | Preserve data/uploads across application restarts and schema evolution using approved hosted persistence and Alembic | Restart/redeployment and migration checks retain existing demo records and file access |
| NFR-10 | Run critical pytest checks and frontend build in CI, plus the browser demonstration checklist | Recorded automated results and manual observations; no unperformed scenario is reported as passing |

### File-type boundaries

| Purpose | Allowed types |
| --- | --- |
| RFQ / manufacturing drawing | JPG/JPEG, PNG, PDF, STEP/STP, IGES/IGS, STL, DWG |
| Support / employee issue attachment | JPG/JPEG, PNG, PDF |
| Product / profile image | JPG/JPEG, PNG |

Choose one byte interpretation for the approved 20 MB limit in the verification contract and use it consistently in frontend/backend boundary tests. This is a unit convention, not permission to raise the limit. Content checks confirm an allowed format; they do not certify a CAD drawing's manufacturability.

## 7. Confirmed technical boundaries

The full decisions and reasons remain in CONTEXT §§4, 7–9. No additional technology is selected here.

- React 19, JavaScript, Vite, React Router, Bootstrap 5, npm, Node.js 24.
- Python 3.12, FastAPI/Pydantic, synchronous SQLAlchemy handlers, PostgreSQL 17, Alembic.
- PostgreSQL-backed sessions, Argon2id, HttpOnly/SameSite=Lax cookies, HTTPS Secure cookies, Origin and CSRF validation. Vite's development proxy keeps browser calls same-origin.
- One Render Free native Python service serves the built frontend and API. Supabase Free provides PostgreSQL/private Storage. No Supabase Auth, Docker, or paid hosting.
- Trusted offline-trained scikit-learn linear regression artifacts load at startup from MODEL_PATH. No API retraining or external AI service.
- Repository boundaries remain `frontend/`, `backend/`, `backend/ml/`, `data/demo/`, and `docs/`. Secrets remain backend-only; only the relative API prefix is public frontend configuration.

No application repository was supplied. File placement here describes required documentation and the approved future repository boundaries, not an observed existing implementation.

## 8. UI and historical-artifact reconciliation

Use approved screenshots for layout and visual intent after applying the final scope. Do not infer functionality merely from a button, sample figure, or older diagram. Original source images remain unmodified references.

| Historical element | Required interpretation |
| --- | --- |
| Overcrowded Admin dashboard | Use the final simplified Admin dashboard |
| Inventory & Suppliers / supplier tabs | Inventory only; remove supplier/procurement actions |
| Users & Roles / configurable permissions | Users with fixed Admin, Customer, Employee roles |
| Multiple jobs/employees per order | One job and one assigned employee |
| 500 MB / five uploads | Two files per RFQ, 20 MB each |
| Payment provider/card/UPI entry, 60/40 terms | Safe simulation; partial amounts allowed but full settlement before assignment |
| Confidence percent / Random Forest / AI assistant | Linear-regression advisory estimate; no confidence display or chat |
| Notifications, recommendations, performance profile cards | Excluded controls do not become requirements |
| Inconsistent Customer sidebars | Shared Customer component; catalogue reuses public catalogue |
| Production completion shown as delivery | Separate quality-approved completion, delivery, and closure |
| Separate inquiries/complaints | One support ticket with multiple messages |

Refinements in these PRPs make observable behavior testable, including three consistent support statuses, below-minimum stock display semantics, distinct delivery/closure actions, CSV safety, and security-preserving retry behavior. They are requirements elaborations, not claims that every detailed sentence appeared verbatim in an earlier approval. Any implementation choice that would alter the approved scope or business invariants requires a context decision update.

## 9. Explicit non-goals

No supplier accounts/records or procurement; configurable roles or Sales/Finance users; shared-business customer access; two-factor authentication; notifications or email/SMS/WhatsApp delivery; chat/AI assistant/OpenAI integration; product recommendations; customer reviews/ratings; refunds/returns; separate Inquiry/Complaint models; interactive CAD rendering/analysis; ERP/machine/GPS integration; digital proof of delivery; casting trials/warranties; backup/restore or AI-settings pages; Employee Messages or separate Active Jobs; multiple jobs/employees per order; stock reservation/automatic consumption; real payments; Docker; paid hosting.

Screenshot extras such as a standalone specification-PDF generator, ticket assignment queues, and scheduled reports are not added to the required MVP. This is the complete scoped academic product, with no later-phase feature list.

## 10. Dependencies and risks

| Dependency or risk | Requirement consequence |
| --- | --- |
| Identity/ownership foundation | All protected feature verification depends on PRP-001 |
| RFQ-to-order linkage | PRP-003 supplies requirements, PRP-004 advisory estimates, PRP-005 official versions, PRP-006 commercial records, PRP-007 production |
| Missing model or synthetic-data limitations | Manual quotation works; evaluation remains honestly labeled |
| Database/storage failure separately | Upload consistency and authorized retry/download are verified |
| Stale browser pages/concurrent actions | State checks and atomicity guard acceptance, settlement, cancellation, assignment, quality, stock |
| Free-host sleep/pause/quotas | Resume and check demonstration services beforehand; no continuous-availability promise |
| Render temporary filesystem | Uploads remain in private persistent storage; model artifact is a deployment asset |
| Older diagrams/screens conflict | CONTEXT wins; verification must use resolved ownership and exclusions |
| Dashboard/report aggregation drift | Reconcile totals against a known stored dataset and labeled date semantics |

## 11. Release acceptance and verification boundary

A demonstration release requires evidence for every Must requirement and relevant shared NFR. The feature tables are product acceptance scenarios, not executed test reports. Detailed fixtures, exact requests, edge-case inputs, and automation belong in the subsequent verification contract for each slice.

The release walkthrough must cover:

1. Registration/login, role isolation, and a working public catalogue.
2. Existing-product and custom RFQ submission with allowed files and correct review data.
3. Both AI-assisted and manual quotation preparation, revision, expiry rejection, and valid acceptance.
4. One order/invoice from duplicate acceptance; partial payment, failed payment, safe retry, and full settlement.
5. Eligible cancellation and rejection of post-payment cancellation.
6. One assigned job, employee progress/issue reporting, quality return/rework, resubmission, approval, delivery, and closure.
7. Manual stock history with safe deductions; customer/Admin support conversation and resolution.
8. Role dashboards, stored-record report reconciliation, and matching safe CSV export.
9. Ownership/CSRF/file-limit/concurrency failures, migrations, hosted persistence, and model-unavailable behavior.

Evidence should identify the requirement/scenario, environment, data fixture, observed result, and any unresolved defect. Secrets and private credentials must not appear in evidence. No “all tests passed” statement is permitted without actual execution results.

## 12. Source traceability

| Source | Governs |
| --- | --- |
| CONTEXT §§1–3 | Purpose, source hierarchy, complete approved MVP |
| CONTEXT §§4, 8–9 | Stack, environment, security, repository and verification constraints |
| CONTEXT §5 | Actors, ownership, one-job/one-employee boundary |
| CONTEXT §6 | Quotation validity, money, cancellation, production, inventory, support |
| CONTEXT §7 | Upload limits/formats, model training/inference/provenance |
| CONTEXT §§10–12 | UI normalization, exclusions, canonical model, approved conflict resolutions |
| Supplied presentations/diagrams/screens | Business and visual reference, subordinate to CONTEXT |
| Earlier Product Requirements Prompt/workflow format | Document structure and traceable REQ/acceptance format only; no scope imported from another project |

Feature PRPs cite the specific context sections and relevant screen/diagram references for their requirements. Filename references identify supplied assets; the documentation ZIP does not duplicate the large original image/diagram collection.

## 13. Current status and immediate next action

**Completed:** Master PRP and ten feature PRPs, with 35 functional requirement definitions and linked acceptance scenarios. CONTEXT is retained unchanged.

**Not performed:** Application implementation, database creation, model training, deployment, or execution of product acceptance tests.

**Blocking scope questions:** None under the approved context baseline. Exact field ranges, endpoint contracts, schema columns, dependency pins, and test fixtures are subordinate implementation/verification details. They must preserve these requirements and be specified before the relevant slice is implemented.

**Next action:** Derive a dependency-aware vertical-slice plan from these PRPs, then prepare the first slice's verification contract. Do not treat the ten feature files as permission to build the entire application in one unverified change.
