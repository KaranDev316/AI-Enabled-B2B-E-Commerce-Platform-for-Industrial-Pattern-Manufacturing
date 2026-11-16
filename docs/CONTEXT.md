# KPC Project Context

Version 1.0 · Final project baseline · 2026-11-15

This document governs project scope, technical choices, and development constraints. The user approved the MVP, engineering package, conflict resolutions, amendments, and Render/Supabase hosting selection in this conversation. Changes to this baseline require explicit user approval and a decision-log update. `docs/PRP.md` will elaborate workflows and verification within this baseline.

## 1. Project

- **Name** — KPC, Khodel Pattern Craft.
- **Purpose** — Digitize the B2B catalogue, RFQ, quotation, order, manufacturing, billing, and support workflow for an industrial wooden and metallic pattern manufacturer in Ahmedabad.
- **Problem** — Calls, WhatsApp, paperwork, manual stock checks, and repeated follow-up make drawings, costing, production status, and payments difficult to coordinate.
- **Users** — Visitor, Customer, Employee, and Admin. Visitor means unauthenticated access. The other three are fixed account roles.
- **Constraints** — Three-person final-year BCA project. Keep the system understandable, demonstrable, and manageable. Free hosting and native development tools are required. Docker is excluded.
- **Status** — Presentations, diagrams, and UI references exist. Context planning is complete. No application repository was supplied, and implementation status has not been verified. This context phase produces documentation only.

## 2. Source authority

The approved decisions in this document govern conflicts with earlier artifacts. Historical diagrams, field definitions, sample values, and screenshot controls cannot independently add requirements.

| Source | Role |
| --- | --- |
| `project.pptx`, especially slides 4, 6–13 | Business purpose, original scope, and original stack |
| `Khodel_Pattern_Craft_Master_Project(1).pptx` | Academic design and original data dictionary |
| Supplied SVG use-case, sequence, activity, state, ER, class, and object diagrams | Design references subject to the resolutions in section 11 |
| Supplied UI images and `KPC_Complete_UI_UX_Design_Documentation.pdf` | Visual references subject to the final feature boundary |
| User approvals and amendments, 2026-11-15 | Authoritative scope, technology, ownership, and business decisions |

The original artifacts have not been modified by this document. Future project documentation must use the resolved baseline.

## 3. MVP boundary

Deliver the complete RFQ-to-delivery flow with the following supporting features. Detailed acceptance criteria belong in `docs/PRP.md`.

| Area | Included scope |
| --- | --- |
| Public website | Landing page with company information, catalogue, product details |
| Accounts | Customer registration, login/logout, profiles, Admin-created employees, account activation/deactivation and password reset |
| Products | Add/edit/activate/deactivate products, categories, specifications, and product images |
| RFQs | Three-step requirement/upload/review form for catalogue or custom requirements, RFQ status, file upload/download, image/PDF preview |
| Quotations | Admin itemized quotation and lead time, version history, customer acceptance/rejection/change requests |
| Orders | Order list/details, one production job per order, one assigned employee, progress tracking, quality review, delivery and closure |
| Billing | Demonstration invoice generation/download, partial simulated payments, outstanding balance and payment history |
| Inventory | Materials, quantities, manual stock additions/deductions with reasons, adjustment history, low-stock indicator |
| Support | Combined Support & Complaints tickets with conversation messages, Admin replies, and status changes |
| Reports | Role-specific summaries and recent activity, order/production/payment totals from stored records, CSV export |
| AI | Synthetic-data demonstration of price and lead-time estimation using linear regression, with Admin-controlled official quotations |

## 4. Stack and deployment

| Layer | Final choice | Reason |
| --- | --- | --- |
| Frontend | HTML5, CSS3, JavaScript ES6+, React 19, Vite, React Router, npm | Established React direction with one browser application |
| UI | Bootstrap 5 and shared portal components | Existing framework choice and consistent approved visual identity |
| Backend | Python 3.12, FastAPI, Pydantic | Established backend direction and validated inputs |
| Database | PostgreSQL 17, SQLAlchemy, Alembic | Relational business records and repeatable schema migrations |
| Authentication | PostgreSQL-backed sessions and browser cookies, Argon2id password hashes | Fixed-role browser access and server-controlled sessions |
| AI | Scikit-learn linear regression | Small, explainable demonstration model |
| Hosting | Render Free native Python web service | Public academic demonstration without Docker |
| Persistent data/files | Supabase Free PostgreSQL and private Storage buckets | Preserve records and uploads across application restarts |
| Testing | pytest and browser demonstration checklist | Critical workflow verification within academic scope |
| CI | GitHub Actions backend tests and frontend build | Repeatable checks before delivery |
| Tools | VS Code, Git/GitHub, browser inspection | Established development workflow |

### Deployment and environment boundaries

- Use one Git repository and one Render web service. Build React with Node.js 24 and npm. FastAPI serves the built frontend and API under the same public HTTPS origin.
- Develop with native Node.js and a Python virtual environment. Vite proxies API requests to FastAPI, keeping browser requests and cookies on the Vite origin. Use relative API URLs.
- Connect FastAPI to Supabase PostgreSQL through SQLAlchemy. Use the Supabase session pooler when IPv4 connectivity requires it. Backend access controls remain authoritative. Supabase Auth is outside the chosen authentication design.
- Store persistent uploads in private Supabase Storage. The application filesystem is temporary working space only. The approved free-hosting choice replaces the earlier persistent-local-filesystem proposal.
- Apply Alembic migrations through a controlled deployment/startup step before serving requests. Free Render hosting does not provide the paid pre-deploy command feature.
- Keep development, automated-test, and demonstration data isolated. Tests must use a dedicated test database and isolated file fixtures.
- Record exact compatible package versions in frontend lockfiles and pinned Python dependency files at setup. The selected runtime/framework version lines above are the compatibility baseline.
- Free-tier limits apply. Render can sleep after 15 idle minutes and has ephemeral local storage. Supabase Free includes limited database/storage capacity and can pause after inactivity. Resume and check services before the academic demonstration. Free hosting does not promise continuous availability.

## 5. Actors and ownership

- One customer login owns one business profile and its RFQs, quotations, orders, invoices, payments, files, and support tickets.
- Admin manages KPC operations, products, inventory, customer/employee account status, quotations, assignments, quality review, delivery, and closure.
- Each order has at most one production job, created when Admin assigns confirmed work. Each job has one assigned employee. Multiple jobs or simultaneous multiple employees per order are excluded.
- Employees access assigned work and its authorized drawings/instructions, update progress, report issues, and submit work for quality review.
- Customers view their records and customer-visible production status. Public access is limited to company/catalogue information and registration/login entry points.
- Supplier accounts, shared customer-company access, and configurable roles are excluded.

## 6. Business rules

### RFQs and quotations

1. Customer submits requirements and optional permitted files. Admin reviews the RFQ and prepares a quotation.
2. Quotations have `version_number`, `status`, and optional `valid_until`. Status values are `draft`, `sent`, `accepted`, `superseded`, `expired`, and `rejected`.
3. Version numbers increase within an RFQ. Creating a new version supersedes the preceding unaccepted version. An accepted quotation is immutable and cannot be superseded through this workflow.
4. An acceptable quotation is the highest version for the RFQ, has status `sent`, and has not passed `valid_until` when supplied. Check expiry during acceptance, even if a stored status has not yet been updated. A newer draft makes the preceding version unavailable for acceptance.
5. Customer may accept, reject, or request changes. A change request leads to a new version through Admin. Acceptance creates exactly one order and one demonstration invoice.
6. Admin owns official prices and lead time. AI estimates remain advisory.

### Money, invoice, and simulated payment

- Use INR and decimal monetary values. Store accepted line items, tax percentage, subtotal, tax amount, and total as immutable order/invoice snapshots. Demo tax rates are explicitly labeled sample data.
- Preserve the quotation's tax percentage and calculated amounts when creating the invoice. Subsequent rate changes do not change an issued invoice.
- Allow positive partial simulated payments. Outstanding balance equals stored invoice total minus the sum of successful simulated payments. Failed attempts do not reduce the balance. Reject overpayment.
- An order remains awaiting payment until its total is fully settled. Full simulated payment confirms it and permits Admin assignment. There is no 60/40 production milestone.
- Use a payment idempotency key with a database uniqueness constraint. A repeated matching submission returns its original result. Reuse with different payment details is rejected. Serialize balance updates so concurrent requests cannot overpay.
- Repeated quotation acceptance returns the existing order/invoice. Database constraints enforce one order per accepted quotation and one invoice per order.
- Customer cancellation is allowed only while awaiting payment and before any successful payment. Once a partial or full payment has been recorded, cancellation/refunds are outside this demonstration workflow. This preserves the approved cancellation boundary after introducing partial payments.
- Payments and invoices clearly identify the academic demonstration. Real payment credentials and gateway integration are excluded.

### Production, quality review, and closure

- Workflow stages are Design & Tooling, Machining/Production, Quality Check, and Completed.
- The employee records the assigned job's progress. With one job per order, order progress follows that job without aggregation across jobs.
- Employees submit finished production for quality review. Admin approves completion or returns it for rework. Job completion is gated by Admin approval, independently of the displayed percentage.
- Returning work sends the job to Machining/Production. Require a rework note and an updated progress value consistent with the work remaining.
- Record every stage transition in `job_stage_history`, including previous/new stage, actor, timestamp, and note. Quality rejection requires a note.
- Reported issues and temporary work pauses remain visible to Admin without creating extra jobs.
- Admin records delivery and closes the order only after the job passes quality review and the invoice is fully paid. Production completion, delivery, and closure remain distinct events.

### Inventory and support

- Stock changes are manual additions/deductions with reasons and history. Prevent deductions below available stock. Automatic reservation and job consumption are excluded.
- Use one `support_tickets` model and multiple `support_messages` per ticket. Customer and Admin messages form the conversation. Separate Inquiry and Complaint entities are excluded.
- Dashboards and CSV reports use stored records. Clearly identify demonstration records and manual quotation pricing where relevant.

## 7. Files and ML boundaries

### Uploads

- Maximum **two files per RFQ**, each **20 MB maximum**. This replaces all larger mockup limits. Apply the same per-file limit to other attachment endpoints and at most two files per attachment submission.
- RFQ/drawing allowlist is JPG/JPEG, PNG, PDF, STEP/STP, IGES/IGS, STL, and DWG. Support/issue attachments accept JPG/JPEG, PNG, and PDF. Product/profile images accept JPG/JPEG and PNG.
- Enforce counts, streamed byte-size limits, allowed extensions, and appropriate content/type checks on the backend. Browser-provided filenames and MIME types alone do not establish file type. CAD validation checks file format only and does not assert manufacturability.
- Use generated object keys and retain original names as metadata. Check record permissions before downloads/previews. Keep storage credentials on the backend.
- Preview images and PDFs. CAD files are downloadable. Interactive CAD rendering, parsing for estimates, and manufacturing analysis are excluded.
- File bytes are stored in private Supabase buckets and metadata in PostgreSQL. Save metadata only after successful storage and clean up orphaned objects after partial failures. Customer documents never use public bucket access.

### Offline estimation

- Put training code in `backend/ml/` and the fixed synthetic dataset in `data/demo/`.
- Train price and lead-time linear regression models offline using material, length/width/height, quantity, and complexity. Persist preprocessing with the estimators.
- Use a reproducible training/held-out split. Fit preprocessing and models on training data only. Report separate held-out mean absolute error for price in INR and lead time in days. Label results as synthetic-data performance.
- Save the trained artifact at `MODEL_PATH`. Its metadata contains a model-version string written at training time, for example `v1-linear-2026-11`. Copy that value into every saved estimate.
- Load the trusted model artifact once at API startup. API requests never train or retrain models. Include the offline-trained artifact in deployment assets.
- Validate required inputs. Missing/invalid inputs produce validation feedback. Missing/corrupt artifacts, unsupported inputs, or unusable predictions make estimation unavailable without blocking manual quotation creation.
- Store structured inputs, predicted price/lead time, model version, and creation time in `ai_price_estimates`. Confidence percentages are excluded.
- Quotations store nullable `estimation_id` and a pricing-source field identifying manual or AI-assisted entry. Manual quotations use a null estimate reference. Official quotation amounts remain Admin-controlled.

## 8. Engineering conventions

| Topic | Final rule |
| --- | --- |
| Naming | Python/database fields use `snake_case`, JavaScript uses `camelCase`, React components use `PascalCase` |
| Modules | Frontend feature folders and shared components. Backend API routes, Pydantic schemas, business services, and SQLAlchemy models |
| Async | Synchronous SQLAlchemy and normal FastAPI `def` handlers for blocking operations. Frontend requests use `async/await` |
| Validation | Pydantic backend validation, frontend feedback, backend ownership/role/state checks |
| Errors | JSON code, message, and optional field errors. Consistent validation/access/not-found/conflict/server-error handling, including normalized validation errors |
| UI feedback | Loading, empty, validation, access-denied, and server-error states. Show simulated payment failure separately from successful payment |
| Transactions | Related database changes commit together. Enforce uniqueness and concurrency safeguards for acceptance, payments, and stock. Alembic migrations preserve existing demonstration records |
| Sessions | Store server-managed sessions in PostgreSQL. Use HttpOnly, `SameSite=Lax` cookies and `Secure` on HTTPS. Rotate sessions at login and invalidate them at logout, password reset, or deactivation |
| CSRF | Validate the Origin header against configured trusted origins on state-changing requests, including login. Reject absent, null, or untrusted origins for browser mutation endpoints. Use session-bound CSRF tokens for authenticated changes. Vite proxies preserve the browser origin |
| Passwords | Argon2id hashes in `users.password_hash` with `VARCHAR(255)`. Initial Admin is provisioned through a setup command. Admin resets customer/employee passwords, requiring change on next login |
| Secrets/logging | Exclude local environment files from Git. Commit placeholder-only examples. Host secrets use provider settings. Logs exclude passwords, session/CSRF tokens, and uploaded-file contents |
| Tests | pytest covers critical authorization, quotation/version/expiry, duplicate/concurrent payment, migration, file-limit, and quality/rework behavior. Complete a browser demonstration checklist |
| CI | GitHub Actions runs backend tests with an isolated PostgreSQL test service and the frontend build. No application Docker setup is required |

Detailed endpoint schemas, field-validation ranges, and test cases belong in `docs/PRP.md` and must implement these rules without changing scope. Exact compatible dependency pins are recorded during setup. These are implementation details under this baseline, rather than unresolved architecture choices.

## 9. Repository and configuration

| Path | Purpose |
| --- | --- |
| `frontend/` | React application and npm lockfile |
| `backend/` | FastAPI application, tests, migrations, pinned Python dependencies |
| `backend/ml/` | Offline training, evaluation, and model artifacts |
| `data/demo/` | Synthetic training and demonstration data |
| `docs/CONTEXT.md` | Authoritative project baseline |
| `docs/PRP.md` | Next planning document with requirements and verification |

Environment-variable names only follow. Values belong in local/host configuration.

- `APP_ENV`, `DATABASE_URL`, `TEST_DATABASE_URL`, `SESSION_TTL_SECONDS`, `MODEL_PATH`, `LOG_LEVEL`, `ALLOWED_ORIGINS`, `VITE_API_BASE_URL`.
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET` for backend-only private storage integration.
- `PORT` for the host's web-service port.

`VITE_API_BASE_URL` is a public relative API prefix. Never expose storage/database credentials through `VITE_` variables. The former persistent `UPLOAD_DIR` and Docker-oriented `POSTGRES_*` environment proposal is superseded by the approved hosted storage and connection-string setup.

## 10. UI and explicit exclusions

Keep the navy/orange/white/light-gray identity, semantic status colors, and one shared sidebar component per portal. Use the simplified Admin Dashboard, revised Employee My Tasks, and Employee Profile without performance cards. The simplified Admin sidebar defines Admin navigation structure. Rename Inventory & Suppliers to Inventory and Users & Roles to Users to match scope. Customer catalogue access uses the shared public catalogue. RFQ Step 3 must use the same Customer sidebar as other Customer screens.

The following features and their dedicated entities/screens are outside this project.

- Supplier accounts, supplier records, purchase orders, supplier invoices, and purchase returns.
- Configurable roles, role-permission tables, Sales/Finance accounts, shared customer-business accounts, and two-factor authentication.
- Chat conversations/messages, OpenAI integration, AI assistant interactions, and product recommendations.
- Notifications and their entities, email/WhatsApp/SMS delivery, and notification controls.
- Customer returns/refunds, reviews/ratings, separate Inquiry/Complaint entities, and a separate Customer Inquiry page.
- Interactive CAD rendering/analysis, ERP or machine integration, GPS, digital proof of delivery, casting-trial management, and warranty issuance.
- Backup/restore and AI-settings screens, Employee Messages, and a separate Active Jobs page.
- Multiple production jobs/employees per order, automatic inventory reservation/consumption, real payments, Docker, and paid hosting.

## 11. Canonical model and resolved conflicts

Use `users` with a fixed role plus `customer_profiles` and `employee_profiles`. Canonical business groups are company/catalogue, RFQs/files, estimates, versioned quotations/items, orders/items, invoices/payments, sessions, one production job per order, stage history, progress/issues, materials/stock adjustments, and support tickets/messages. Enforce one customer profile per customer, one order per accepted quotation, one invoice per order, and one job per order with database constraints. Full column definitions belong in the PRP-derived data dictionary.

| Earlier conflict | Final resolution |
| --- | --- |
| Supplier role in project slides | Removed, along with procurement scope |
| Configurable roles shown in UI/diagrams | Fixed Admin/Customer/Employee values on `users` |
| Different user/profile structures | Canonical user and two profile tables above |
| `password_hash VARCHAR(15)` in slides versus 255 in class diagram | `VARCHAR(255)` with Argon2id |
| AI Interaction versus AIConversation/AIMessage | Exclude chat entities. Retain `ai_price_estimates` only |
| Separate inquiries and complaints | Unified ticket and message tables |
| Immediate confirmation/production in activity diagram | Acceptance creates awaiting-payment order/invoice. Full simulated settlement confirms it |
| Mockup payment milestones versus selected 100% payment | Partial installments allowed, with full settlement required before confirmation |
| Multiple jobs from option 9A versus explicit user simplification | One order, one production job, one assigned employee. Explicit written simplification governs |
| Cancellation with newly approved partial payments | Cancel only with zero successful payments while awaiting payment |
| Rework missing from simplified flow | Admin returns to Machining/Production, recorded in stage history |
| Large upload limits in screenshots | Two files per RFQ, 20 MB each |
| Persistent local filesystem versus free hosting | Private Supabase Storage |
| Random Forest recommendation | User selected linear regression |
| Screenshot confidence percentages | Removed |
| Sidebar differences and excluded controls | Shared per-portal components and scope-aligned navigation |

## 12. Decision log

All user decisions below were approved on 2026-11-15.

| Decision | Rationale and approval source |
| --- | --- |
| Complete academic RFQ-to-delivery MVP | User approved the simplified proposal |
| Context authority and one repository | User selected 1A and 2A |
| Cookie sessions, SQLAlchemy/Alembic | User selected 3A/4A and added CSRF, Origin, proxy, and migration requirements |
| Free hosting without Docker | User amended 5B and selected Render + Supabase in the hosting choice |
| Two RFQ attachments at 20 MB each | User explicitly reduced 6A |
| Full settlement, partial simulated payments, overpayment prevention | User selected 7A and approved payment fixes |
| One job/employee per order | User's explicit written simplification overrides conflicting numeric shorthand |
| Unified support, linear regression, pytest/manual browser checks | User selected 10A, linear regression for 11, and 12A |
| Offline model loading and training metadata | User's engineering amendment and model-version fix |
| Quotation versions, snapshots, rework history, manual pricing source | User approved section 3 with five fixes |
| Scope-aligned canonical model and explicit exclusions | User approved conflict resolutions and requested a final baseline |

Document-level consistency resolutions are the zero-payment cancellation guard and preservation of accepted quotations against superseding revisions. They reconcile the approved rules and are called out above for review.

## 13. Status and next action

Context baseline is complete. No blocking project-context questions remain. Produce `docs/PRP.md` next, then derive implementation tasks and verification from it. Planning must preserve this document's approved choices. Any scope or architectural amendment requires explicit user approval and a new decision-log entry.

### Hosting references

Provider constraints were checked on 2026-11-15. They describe external service limits, not additional application features.

- [Render free service limits](https://render.com/docs/free)
- [Render native runtime tools](https://render.com/docs/native-runtimes)
- [Render deployment steps](https://render.com/docs/deploys)
- [Supabase free-plan limits](https://supabase.com/pricing)
- [Supabase private storage](https://supabase.com/docs/guides/storage/buckets/fundamentals)
- [Supabase PostgreSQL connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
