# KPC — Vertical Slice Delivery Plan

Version 1.0 · 2026-11-15 · Final-year BCA project

**Status:** Planning complete for this document. Every slice below is **NOT STARTED / NOT VERIFIED**. No application implementation, model training, or deployment is claimed.

**Authority:** [CONTEXT.md](CONTEXT.md) defines the approved project baseline. [PRP.md](PRP.md) and its ten feature PRPs define the requirements. This plan sequences their delivery without changing scope or technology. Existing context and PRPs remain unchanged.

## 1. Purpose and working method

Deliver KPC through small, demonstrable user journeys. Each slice connects the necessary screen, backend behavior, persisted records, authorization, and verification for one outcome. Database, backend, and frontend work for that outcome belong together.

The ten feature PRPs organize requirements. The sixteen slices below organize delivery. Some requirements span slices; their coverage is recorded explicitly. Finishing an early part does not mean the whole requirement passes.

Use the recommended sequence unless all listed dependencies are already verified. The sequence is an implementation plan for the complete approved MVP, not a list of optional future features. AI estimation remains required even though manual quoting is delivered first.

Before implementing a slice, write its verification contract: fixtures, precise validation rules, permitted transitions, observable outcomes, failure cases, and evidence. Do not generate all application code from this plan in one change.

## 2. Delivery rules

- Implement and demonstrate one slice at a time. Keep the last verified journeys working.
- Add only the schema, migrations, screens, and services needed for the current outcome. Apply Alembic migrations without wiping existing demo data.
- Enforce security, ownership, transactions, and input validation when a feature first appears. They are not postponed to the last slice.
- Use stored records for demonstrations. Seed data may establish prerequisites, but it cannot substitute for a user action whose slice is marked complete.
- During incremental development, hide or clearly disable unfinished controls. Do not display invented metrics, successful writes, or placeholder status as real behavior.
- Reuse shared portal sidebars and common loading/empty/error/form components as they become necessary. Avoid a separate UI-framework-building phase.
- Keep manual quotation available independently of the model. Production remains blocked until full simulated settlement.
- Each slice includes relevant pytest coverage, a frontend build, and a browser walkthrough. Regression checks follow affected dependencies and business risks.
- No hour estimates or dates are asserted: there is no inspected application repository or measured team delivery rate.

## 3. Sequence at a glance

“Depends on” lists direct prerequisites; their own prerequisites are inherited. Slice completion still requires the shared done criteria in section 7.

| Slice | Demonstrable outcome | Depends on | Main requirement coverage |
| --- | --- | --- | --- |
| S01 | Active users sign in to their own protected portal and log out | None | REQ-02 |
| S02 | Customer registers/edits profile; Admin manages employee/account access | S01 | REQ-01, REQ-03, REQ-04 |
| S03 | Visitor browses persisted company/catalogue/product information | S01 | REQ-05; image display part of REQ-07 |
| S04 | Admin changes catalogue products/categories/images and public views update | S03 | REQ-06, REQ-07 |
| S05 | Customer submits a standard/custom RFQ; Admin reads it | S02, S04 | REQ-08, REQ-10 |
| S06 | Customer attaches drawings; authorized users preview/download them | S05 | REQ-09; attachment part of REQ-08; image part of REQ-03 |
| S07 | Admin issues/revises a manual quote; Customer reviews/rejects/requests changes | S06 | REQ-14, REQ-15, REQ-16; manual provenance part of REQ-13 |
| S08 | Acceptance creates one order/invoice; entirely unpaid order can be cancelled | S07 | REQ-17, REQ-18, REQ-20, REQ-21 |
| S09 | Customer/Admin record safe partial simulated settlement | S08 | REQ-19; payment-sensitive parts of REQ-20, REQ-21 |
| S10 | Admin assigns one job; Employee updates progress; Customer tracks it | S09 | REQ-22, REQ-23; tracking part of REQ-18; employee access part of REQ-09 |
| S11 | Admin returns/approves quality, records delivery, and closes eligible orders | S10 | REQ-24, REQ-26; completion part of REQ-18 |
| S12 | Employee reports an issue; Admin handles its status | S10 | REQ-25 |
| S13 | Admin maintains stock with reasons and consistent adjustment history | S02 | REQ-27, REQ-28, REQ-29 |
| S14 | Customer/Admin complete a support conversation and resolution | S06, S08 | REQ-30, REQ-31, REQ-32 |
| S15 | Admin obtains an offline-trained advisory estimate or uses manual fallback | S07 | REQ-11, REQ-12, REQ-13; AI-assisted provenance part of REQ-14 |
| S16 | Role dashboards and Admin reports/CSV reconcile with completed workflows | S11, S12, S13, S14, S15 | REQ-33, REQ-34, REQ-35; full-release integration |

S03 uses S01's running deployment/application foundation; public reads do not require login. S13 and S14 do not gate production. Their position in the recommended order keeps the commercial/production journey coherent while preserving clear prerequisites.

## 4. Slice specifications

### S01 — Sign in, enter the correct portal, and sign out

**Goal and flow:** Active Customer, Employee, or Admin submits credentials → backend verifies password/account → database-backed session is established → correct portal opens → logout revokes access.

**Scope:** Approved application/runtime setup, initial Alembic migration, initial Admin provisioning, controlled demo identities for the other roles, login/logout, session expiry, role guards, cookie/Origin/CSRF behavior, and minimal shared portal shells. Establish the Vite development proxy, isolated test database, CI backend checks/frontend build, and a small same-origin hosted demonstration using the approved free hosting.

**Persisted boundary:** Canonical users and sessions; only profile foundations actually needed for account integrity. Demo credentials come from setup configuration, never committed secrets.

**Completion evidence:** Each role reaches its permitted shell and survives ordinary refresh. Wrong credentials/inactive accounts fail. Logout/expiry stop access. Missing/null/untrusted Origin on mutations and missing/invalid authenticated CSRF tokens are rejected. A direct unauthorized request fails even when bypassing navigation. Migration and hosted session behavior are demonstrated.

**Requirements / acceptance:** REQ-02; AC-01-03, AC-01-05, and the logout/expiry portion of AC-01-04. Reset/deactivation coverage completes in S02.

**Boundary:** Empty portal shells do not count as dashboards. No catalogue, customer-registration UI, business transactions, or alternative auth provider.

### S02 — Register, maintain profiles, and manage account access

**Goal and flow:** Visitor registers → Customer/profile are saved together → Customer logs in and changes business details. Admin creates an Employee, then exercises account deactivation and password reset.

**Scope:** Customer registration, permitted text profile edits, password change, employee creation, account activation/deactivation, forced password change after Admin reset. Customer/employee profile ownership and employment-field permissions are enforced.

**Persisted boundary:** User/profile relationships and account state; session invalidation linked to reset, deactivation, and password change.

**Completion evidence:** Duplicate/invalid registration leaves no partial account/profile. Public input cannot grant Admin/Employee. Profile edits survive refresh. Role or privileged-field tampering fails. Open sessions stop working after reset/deactivation. Reset forces a password change before normal work resumes.

**Requirements / acceptance:** REQ-01, REQ-03, REQ-04; AC-01-01, AC-01-02, AC-01-06, AC-01-07, AC-01-08; complete AC-01-04. Profile image upload is explicitly completed in S06 using the shared storage behavior.

**Boundary:** Fixed roles only. No invitations, email reset delivery, configurable permissions, supplier account, or two-factor authentication.

### S03 — Browse the persisted public catalogue

**Goal and flow:** Visitor opens landing page → searches/filters active products → reads a selected product → chooses RFQ entry and reaches login when needed.

**Scope:** Company information, catalogue, product details, indicative/on-request prices, active-product filtering, product-image display and missing-image fallback. Use controlled persisted catalogue fixtures until Admin writes arrive in S04. Establish authorized public delivery of catalogue imagery without making customer documents public.

**Persisted boundary:** Catalogue/category/specification records and seeded product-image metadata where supplied. Public access is limited to active public catalogue information.

**Completion evidence:** List/detail agree, search can be cleared, inactive/unknown products have correct feedback, missing price says on request, and loading/empty/error states are distinct. Landing page retains the supplied mobile intent. RFQ handoff does not auto-submit anything.

**Requirements / acceptance:** REQ-05; display part of REQ-07; AC-02-01, AC-02-02, AC-02-03, plus valid-image display from AC-02-06.

**Boundary:** No cart, checkout, recommendations, specification-PDF generator, or claimed completion of an RFQ journey.

### S04 — Maintain catalogue products and images

**Goal and flow:** Admin adds/edits a product/category and uploads a valid image → saved changes appear in the public catalogue → deactivation removes the product from new selection.

**Scope:** Product/category/specification maintenance, activation, image upload, generated storage keys, backend file checks, and cleanup after partial storage/database failures. This is the first complete upload-write journey; use private persistent storage from the outset.

**Persisted boundary:** Catalogue changes and product-image metadata/object associations. Do not delete referenced historical records or overwrite accepted commercial snapshots.

**Completion evidence:** Valid Admin writes survive refresh; Customer writes fail. Unsupported/oversize/mismatched images fail without broken saved associations. Deactivation hides new selection. A fixture containing an existing reference is preserved; repeat this check with real accepted orders after S08.

**Requirements / acceptance:** REQ-06, REQ-07; AC-02-04, AC-02-05, AC-02-06. Live historical-snapshot integration is revisited in S08.

**Boundary:** JPG/JPEG/PNG only here, 20 MB per file, at most two files per submission. No supplier fields or automatic image generation.

### S05 — Submit and inspect an RFQ without attachments

**Goal and flow:** Customer selects existing/custom requirement → enters specifications → reviews three-step wizard → submits → Admin inspects the stored request.

**Scope:** Both requirement types, required inputs, review/edit preservation, contact-information reuse, ownership, RFQ lists/details, and persisted submission/review status. Files are optional; their controls remain unavailable until S06.

**Persisted boundary:** Owned RFQ, its selected product or custom specification, and submitted information. No quotation or order is fabricated.

**Completion evidence:** Both paths work without attachments. Review does not duplicate inputs. Missing fields fail clearly. Back/edit retains values. Owner/Admin see matching saved facts; another Customer and an unassigned Employee cannot read the RFQ.

**Requirements / acceptance:** REQ-08 excluding attachment interaction, REQ-10; AC-03-01, AC-03-02, AC-03-03, AC-03-08.

**Boundary:** No separate custom-order bypass or draft-management product feature. Quotation availability is integrated in S07.

### S06 — Attach drawings and retrieve authorized files

**Goal and flow:** Customer adds permitted files within the RFQ wizard → submits → owner/Admin preview image/PDF or download CAD. User can also save a permitted own-profile image through the same validated storage foundation.

**Scope:** Maximum two RFQ files total, 20 MB each; complete approved RFQ allowlist; format/content checks, concurrent-count enforcement, metadata/object consistency, authorized previews/downloads, and profile-image upload. Profile images retain the narrower JPG/JPEG/PNG allowlist.

**Persisted boundary:** Private objects plus parent-owned metadata. No public bucket or persistent dependence on the application filesystem.

**Completion evidence:** Allowed boundary-size files succeed; third/oversize/mismatched files fail. Concurrent uploads cannot exceed RFQ count. Another Customer cannot retrieve a private object. Storage/metadata failures leave no falsely successful attachment. Files remain accessible after restart. Profile image changes preserve ownership.

**Requirements / acceptance:** REQ-09 except the later assigned-Employee path; attachment part of REQ-08 and image part of REQ-03; AC-03-04 through AC-03-07. S10 completes assigned-Employee access.

**Boundary:** Images/PDF preview, CAD download. No interactive CAD rendering, parsing for estimates, or manufacturability analysis. Fix the 20 MB byte convention in this slice's verification contract and apply it consistently to all uploads.

### S07 — Issue, revise, and respond to a manual quotation

**Goal and flow:** Admin reviews RFQ → drafts itemized price/lead time manually → issues offer → Customer reviews/rejects/requests changes → Admin creates a traceable revision.

**Scope:** INR decimal calculations, sample-tax label, version numbers, allowed quotation statuses, optional validity, customer review, change request/rejection, manual pricing-source metadata, and null estimate reference. Creating a newer draft immediately supersedes the previous unaccepted version.

**Persisted boundary:** RFQ-linked quotation versions/items and decisions. Preserve prior versions; never mutate an accepted version. Manual flow must not require a model artifact.

**Completion evidence:** Incomplete draft cannot be sent; owner-only review works; concurrent revisions cannot create duplicate versions. Old versions become ineligible immediately. Change requests preserve official values and reach Admin. Manual quotation works with no model artifact. Acceptance is unavailable until S08.

**Requirements / acceptance:** REQ-14, REQ-15, REQ-16; manual/provenance part of REQ-13; AC-05-01 through AC-05-05 as applicable to preparation/review. The action-time acceptance and accepted-immutability cases complete in S08. AC-04-06/07 receive full model-failure evidence in S15.

**Boundary:** No AI training/service yet, no confidence percent, no external message delivery. Earlier catalogue amounts remain indicative.

### S08 — Accept once, inspect invoice, and cancel an entirely unpaid order

**Goal and flow:** Customer accepts latest eligible offer → one awaiting-payment order and one demo invoice are committed → owner/Admin inspect/download invoice. A separate zero-payment order can be cancelled.

**Scope:** Eligibility checked at action time, duplicate-safe acceptance, quote/order/invoice atomicity, immutable commercial snapshots, order/invoice lists/details, demo invoice download, and zero-payment cancellation. No payment button is enabled until S09.

**Persisted boundary:** Accepted quote, unique order per accepted quote, unique invoice per order, accepted item/tax/amount snapshots, cancellation state/history.

**Completion evidence:** Expired/stale/unauthorized first acceptance fails. Concurrent acceptance/revision and rollback preserve invariants. Repeated successful acceptance returns the same records. Product/tax edits leave invoice unchanged. Cancellation preserves history and blocks assignment. Paid-order guards are tested with controlled fixtures here and real payment flows in S09.

**Requirements / acceptance:** REQ-17, initial commercial views of REQ-18, REQ-20, REQ-21; AC-05-02/04 acceptance checks, AC-05-06 through AC-05-08, AC-06-01, AC-06-06, AC-06-07. Recheck AC-02-05 with a real accepted order.

**Boundary:** Acceptance does not confirm production. Tracking has no invented job/stage history. Cancellation after any successful payment is forbidden even before payment UI exists.

### S09 — Settle a demo invoice safely

**Goal and flow:** Customer/Admin records partial simulated payment → outstanding decreases → final successful payment confirms order → matching retry returns original result.

**Scope:** Positive partial payments, failure feedback/history, outstanding computation, idempotency-key content checks, prevention of overpayment under concurrency, and transactional full-settlement confirmation. Invoice views reflect payment history without changing original totals.

**Persisted boundary:** Simulated payments, their outcome/idempotency, invoice settlement, and order confirmation. Payment and cancellation compete against the same authoritative state.

**Completion evidence:** Failed payment does not reduce balance. Zero/negative/excess amounts fail. Matching retries do not duplicate payment; different details with the same key conflict. Simultaneous payments cannot overpay. Cancellation/payment race never leaves a cancelled paid order. Partial payment blocks cancellation and assignment; full settlement permits assignment.

**Requirements / acceptance:** REQ-19; payment-sensitive completion of REQ-20/REQ-21; AC-06-03 through AC-06-08, including real-flow rechecks of snapshot and cancellation cases.

**Boundary:** No real credentials, gateway, refunds, or 60/40 production milestone. All payment controls and invoice outputs identify the simulation.

### S10 — Assign one job and report progress

**Goal and flow:** Admin assigns a confirmed paid order → one Employee opens requirements/files → records work progress/pause and submits Quality Check → Customer sees the corresponding production stage and dated updates.

**Scope:** Single-job creation and assignment to active employee, My Tasks, instructions/files, Design & Tooling and Machining/Production progress, pause/resume, submission for quality review, stage history, and customer tracking. Quality decisions are unavailable until S11.

**Persisted boundary:** One job per order, one assigned employee, job progress, pause state, stage transitions. Order progress follows that one job.

**Completion evidence:** Unpaid/cancelled orders and inactive/non-employee assignments fail. Concurrent creation yields no second job. Unassigned Employee cannot read/update work or drawings. Progress range is enforced. Customer stage/progress/history agrees with saved updates. Employee cannot self-approve or complete by setting 100 percent.

**Requirements / acceptance:** REQ-22, REQ-23; tracking part of REQ-18; assigned-Employee part of REQ-09; AC-07-01 through AC-07-05 and AC-06-02. Recheck file authorization from AC-03-06/08 after assignment.

**Boundary:** No multiple jobs, multiple assignees, auto stock consumption, delivery authority for Employee, or invented production dates.

### S11 — Review quality, handle rework, and record delivery/closure

**Goal and flow:** Admin reviews submitted work → returns to Machining with note/progress → Employee reworks/resubmits → Admin approves → separately records delivery and closure.

**Scope:** Quality approval/return, required rework note and consistent revised progress, complete transition history, Completed Jobs view, and paid/quality-approved delivery/closure gates.

**Persisted boundary:** Job-stage history, approved completion, separate delivery/closure events. The same job continues through rework.

**Completion evidence:** Return without note/progress fails. Rework goes to Machining and requires resubmission. Stale/concurrent decisions cannot bypass the current stage or duplicate events. Neither 100 percent nor Employee action grants completion. Unpaid/unapproved orders cannot be delivered/closed. Recorded events appear consistently to owner/Admin.

**Requirements / acceptance:** REQ-24, REQ-26; completed lifecycle part of REQ-18; AC-07-05, AC-07-06, AC-07-08, AC-07-09, and lifecycle recheck of AC-06-02.

**Boundary:** No carrier, GPS, proof-of-delivery, trial, or warranty workflow.

### S12 — Report and handle a production issue

**Goal and flow:** Employee reports machine/material/production issue, optionally linked to assigned work → Admin reviews/updates handling status → reporting Employee sees the saved result.

**Scope:** Issue fields/priority, own issue list/detail, optional permitted attachments, Admin handling status, and visibility alongside paused work without creating another job.

**Persisted boundary:** Production issue and its permitted association/status/attachments, distinct from Customer support tickets.

**Completion evidence:** Required-field errors preserve input. Another employee's job cannot be attached. Valid attachments can be retrieved only by permitted users. Admin status changes appear to the reporter. Issue reporting does not duplicate a job or alter paid/quality gates.

**Requirements / acceptance:** REQ-25; AC-07-07; recheck pause behavior from AC-07-04.

**Boundary:** No machine integration or notifications. JPG/JPEG/PNG/PDF, at most two attachments per submission, 20 MB each.

### S13 — Maintain reasoned stock balances

**Goal and flow:** Admin creates material → records opening quantity with reason → adds/deducts stock → reviews history and low-stock indicator.

**Scope:** Material identifiers, units, minimum thresholds, manual adjustments/reasons, nonnegative balances, history, low/out-of-stock display, and search/detail states.

**Persisted boundary:** Materials and atomic balance/history changes. Correct mistakes with explained compensating entries rather than silent history replacement.

**Completion evidence:** Duplicate/invalid material fails. Descriptive edits preserve unit/history meaning. Missing reason or excessive deduction fails. Concurrent deductions cannot create negative stock. Rollback preserves history/balance consistency. Zero, below-minimum, and threshold-or-above indicators match stored quantities.

**Requirements / acceptance:** REQ-27, REQ-28, REQ-29; AC-08-01 through AC-08-06.

**Boundary:** No suppliers, purchasing, reorder automation, job reservation, or automatic consumption. Production does not depend on this slice mutating stock.

### S14 — Resolve a customer support ticket

**Goal and flow:** Customer submits an inquiry/complaint → Admin replies and changes status → Customer adds context → Admin resolves → owner sees complete conversation.

**Scope:** Unified ticket creation/list/detail, optional own-order association, permitted attachments, Customer/Admin messages, and Open/In Progress/Resolved status. Reuse private-file safeguards with the support allowlist.

**Persisted boundary:** Owned support ticket and multiple authored/timestamped messages, status, attachments. No separate Inquiry/Complaint entities.

**Completion evidence:** Valid ticket works with/without related order. Another customer's order/files cannot be linked/read. Unauthorized replies/status changes fail. Messages stay chronological and tied to their ticket. Failed saves do not appear as successful replies/resolution. Both participants see consistent status.

**Requirements / acceptance:** REQ-30, REQ-31, REQ-32; AC-09-01 through AC-09-06.

**Boundary:** No standalone chat, AI assistant, email, support assignment queue, or separate employee-issue handling model in this flow.

### S15 — Add advisory estimation with a verified manual fallback

**Goal and flow:** Team prepares an offline-trained artifact → Admin requests estimate for structured RFQ inputs → sees advisory INR/days → prepares official quotation with traceable pricing source. If estimation is unavailable, the established manual flow still works.

**Scope:** Fixed labeled synthetic dataset, reproducible train/held-out split, training-only preprocessing, linear regression for both targets, separate MAEs, saved preprocessing/model version, trusted startup loading, validated inference, stored estimate inputs/results/version, and AI-assisted quotation provenance.

**Persisted boundary:** Versioned offline artifact at MODEL_PATH and saved estimate records linked optionally from quotation versions. This slice includes the offline evidence because it supports the user-visible estimate; it is not an isolated model experiment.

**Completion evidence:** Evaluation can be reproduced and is labeled synthetic. Saved version matches the loaded model. API requests never train. Missing/corrupt artifacts, unsupported inputs, and unusable predictions do not block manual quotation or produce fake estimates. Official values remain Admin-controlled. Existing manual/accepted quotation snapshots remain unchanged.

**Requirements / acceptance:** REQ-11, REQ-12, REQ-13; remaining provenance integration in REQ-14; AC-04-01 through AC-04-07. Recheck S07/S08 manual quoting and snapshot behavior with and without the model.

**Boundary:** No confidence percentage, external AI service, CAD feature extraction, automatic quote approval, or model-settings UI. No invented minimum accuracy target.

### S16 — Reconcile dashboards, reports, exports, and full demonstration

**Goal and flow:** Each role opens its dashboard → follows an authorized work item → Admin filters business/production/payment reports → exports matching records as CSV.

**Scope:** Scoped stored-record summaries/recent activity, simplified portal dashboards, basic order/production/payment reports, labeled date/snapshot semantics, complete filtered CSV, escaping/formula safety, and final cross-feature demonstration.

**Persisted boundary:** Read existing authoritative business records/histories. Do not create competing status definitions or notification entities to supply dashboards.

**Completion evidence:** Known fixtures reconcile counts/totals with underlying lists and payment history. Owner/role isolation holds. Empty/invalid-range/server-error states differ. CSV matches full filtered records and excludes secrets/private URLs. All required prior scenarios have recorded outcomes; fresh migrations, retained-data upgrade, restart/file persistence, deployed sessions, and model fallback are checked on the final integrated version.

**Requirements / acceptance:** REQ-33, REQ-34, REQ-35; AC-10-01 through AC-10-07, plus master PRP release walkthrough. Final integration does not replace earlier slice verification.

**Boundary:** No notification system, invented screenshot numbers, advanced forecasting, scheduled exports, or separate supplier/role analytics.

## 5. Requirement completion map

The “complete after” column identifies when the full functional requirement can be assessed, including dependencies. It does not assert that verification has passed.

| Requirements | Contributions | Complete after |
| --- | --- | --- |
| REQ-01 | S02 registration | S02 |
| REQ-02 | S01 sessions; S02 reset/deactivation integration | S02 |
| REQ-03 | S02 profile/password; S06 profile images | S06 |
| REQ-04 | S02 Admin account management | S02 |
| REQ-05 | S03 browsing; S05 actual RFQ handoff | S05 |
| REQ-06 | S04 maintenance; S08 live historical-reference recheck | S08 |
| REQ-07 | S03 image reads; S04 upload/write | S04 |
| REQ-08 | S05 wizard; S06 attachments | S06 |
| REQ-09 | S06 files; S10 assigned-Employee access | S10 |
| REQ-10 | S05 saved RFQ review; S07 available quotation status | S07 |
| REQ-11, REQ-12 | S15 offline model and inference | S15 |
| REQ-13 | S07 manual source/null reference; S15 model-failure/source integration | S15 |
| REQ-14 | S07 versions/items; S08 accepted immutability; S15 AI-assisted provenance | S15 |
| REQ-15 | S07 issuing/review; S08 acceptance-time eligibility | S08 |
| REQ-16 | S07 customer rejection/change requests | S07 |
| REQ-17 | S08 transactional acceptance | S08 |
| REQ-18 | S08 commercial views; S10 tracking; S11 completed lifecycle | S11 |
| REQ-19 | S09 simulated settlement | S09 |
| REQ-20 | S08 invoice/download; S09 live payment history | S09 |
| REQ-21 | S08 unpaid cancellation; S09 payment races/guards | S09 |
| REQ-22, REQ-23 | S10 assignment/progress; S11 stale quality-decision integration | S11 |
| REQ-24 | S11 quality/rework | S11 |
| REQ-25 | S12 production issues | S12 |
| REQ-26 | S11 delivery/closure | S11 |
| REQ-27, REQ-28, REQ-29 | S13 manual inventory | S13 |
| REQ-30, REQ-31, REQ-32 | S14 support conversation | S14 |
| REQ-33, REQ-34, REQ-35 | S16 dashboards/reports/export | S16 |

## 6. Shared NFR verification ownership

These checks recur when new surfaces are introduced. Their first appearance is not permission to skip them in subsequent slices.

| PRP quality rule | First evidence | Required follow-through |
| --- | --- | --- |
| NFR-01 access/ownership | S01–S02 | Every protected record/action, especially files, invoices, assigned jobs, and exports |
| NFR-02 Origin/CSRF/session protections | S01 | Every new mutation, plus S16 deployed same-origin check |
| NFR-03 validation/error states | S01 | Every slice's success, invalid, empty, denied/conflict, and failed-save path |
| NFR-04 atomicity/concurrency | S02 account/profile pair | Versions S07; acceptance S08; payments/cancel S09; assignment/quality S10–S11; stock S13 |
| NFR-05 file safety/privacy | S04 images | RFQ/profile S06, assigned access S10, issue S12, support S14 |
| NFR-06 secrets/log/export safety | S01 | Uploads, payment simulation, model artifacts, and S16 exports/evidence |
| NFR-07 truthful persisted data | S03 | Every business view; synthetic estimates S15; reconciliation S16 |
| NFR-08 consistent usable UI | S01 portal shells; S03 public pages | Every feature, then S16 whole-portal review |
| NFR-09 migrations/persistence | S01 | Every schema change; first uploaded-object restart check S04/S06; integrated S16 |
| NFR-10 automated/manual evidence | S01 | Every slice and final release |

## 7. Common definition of done

A slice is complete only when:

1. Its user journey works through the real UI, backend, and persistent data boundaries needed by that journey.
2. Its listed requirement portions and acceptance scenarios have observed evidence, including relevant failure and authorization cases.
3. Database changes use migrations and preserve earlier demo records. The application does not require a database wipe to adopt the slice.
4. Critical duplicate/concurrent/state-transition cases for the slice are verified where applicable.
5. Frontend build and relevant backend tests pass, and the browser walkthrough is recorded. Unrun checks remain explicitly unverified.
6. Existing affected journeys still work; no excluded features or alternative stack are introduced.
7. UI displays only real persisted outcomes and distinguishes unfinished capabilities. Shared portal navigation remains consistent.
8. Evidence records slice ID, requirement/scenario IDs, tested version/environment, fixture, actual result, and unresolved defects without secrets.

Failed evidence keeps the slice open. A working happy path alone does not complete payment, ownership, private-file, or quality-review requirements.

## 8. Demonstration checkpoints

| Checkpoint | What can be honestly demonstrated | Remaining required work |
| --- | --- | --- |
| After S04 | Protected accounts, editable profiles, public catalogue, Admin catalogue maintenance | RFQ/commercial/production and supporting workflows; profile images |
| After S06 | Customer-to-Admin RFQ with private attachments and profile images | Official decisions, billing, production, inventory/support, AI, reports |
| After S09 | Manual RFQ-to-quotation-to-order/invoice and safe simulated settlement | Production, issues, inventory/support, advisory AI, full dashboards/reports |
| After S11 | Assigned work, customer tracking, quality/rework, delivery/closure | Issues, inventory/support, advisory AI, complete reporting in the recommended sequence |
| After S16 | Complete approved academic MVP with integrated evidence | No planned additional product phase; resolve any failing release checks |

These checkpoints support review and debugging. None permits dropping the remaining approved requirements.

## 9. Next document and current action

The next document is **`docs/VERIFICATION_PLAN.md`**, beginning with a concrete S01 verification contract and reusable evidence conventions. Specify exact fixtures, session/Origin/CSRF cases, migration expectations, hosted/local environment differences, and pass/fail observations before coding S01. Do not add production features while writing that contract.

Then implement S01, verify it, review the change, and record its outcome before proceeding. Later slice contracts are prepared when their prerequisite behavior and interfaces are known. This avoids pretending that unimplemented API/schema details are already verified.

**Current state:** All sixteen slices remain NOT STARTED / NOT VERIFIED. This document is the delivery plan only. No original images, context decisions, PRP requirements, or application files were modified.
