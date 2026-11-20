# KPC — Verification Plan

Version 1.0 · 2026-11-15 · Final-year BCA project

**Status:** Verification specification only. All cases are **NOT RUN**. No application code, database, CI execution, browser test, model evaluation, or deployment has been verified by creating this file.

**Authority:** Read [CONTEXT.md](CONTEXT.md), [PRP.md](PRP.md), [VERTICAL_SLICE_PLAN.md](VERTICAL_SLICE_PLAN.md), and [PRP-001 — Accounts and access](PRPs/001-accounts-and-access.md). The approved baseline governs any conflict. This document defines evidence and pass/fail checks; it does not change product scope.

## 1. Purpose and coverage

Prove that a delivered slice satisfies its user-visible behavior and protects its data. A screenshot of a successful page is not enough evidence for session revocation, authorization, transactions, or persistence.

This version contains:

- A concrete verification contract for **S01 — Sign in, enter the correct portal, and sign out**.
- Shared execution, evidence, defect, and completion rules.
- Verification obligations for S02–S16, without pretending their unimplemented interfaces are already known.

S01 covers REQ-02, AC-01-03, AC-01-05, and the logout/expiry portion of AC-01-04. Admin reset/deactivation workflows remain S02. Account-status fixtures in S01 verify access enforcement, not completion of an Admin management interface.

## 2. Verification levels

| Level | Purpose | Evidence |
| --- | --- | --- |
| Backend automated checks | Exercise validation, session state, authorization, Origin/CSRF, persistence, and failure behavior | pytest results plus assertions against an isolated PostgreSQL database |
| Browser walkthrough | Verify real cookies, navigation, feedback, loading states, and the development proxy | Recorded steps and observations using the actual frontend/backend |
| Migration/configuration review | Confirm selected runtimes, schema migration, password storage, secret handling, and CI isolation | Sanitized configuration/schema review and migration/build results |
| Hosted smoke check | Verify the built frontend and API on the approved single HTTPS origin | Login, refresh, logout, direct-link, cookie-attribute, and restart observations |

Use actual PostgreSQL for session/persistence evidence. A mock can inject a failure, but a mocked successful repository cannot prove a real database integration. Browser automation tooling is not added to the stack; the approved manual browser checklist is sufficient alongside pytest.

## 3. Environment and execution safety

### Environment boundaries

| Environment | Required setup | Restrictions |
| --- | --- | --- |
| Local development | Native Node/Python, frontend Vite proxy, FastAPI, isolated development database | Browser API calls use the frontend origin and relative API prefix |
| Automated tests | TEST_DATABASE_URL points to a dedicated disposable PostgreSQL database; isolated fixtures and controllable test clock | Never use the demonstration database, production credentials, or destructive resets against DATABASE_URL |
| CI | Backend checks against isolated PostgreSQL test service; frontend dependency install/build | No committed secrets, real customer records, or application Docker requirement |
| Hosted demonstration | Approved Render/Supabase arrangement; built frontend/API under one HTTPS origin | Test only synthetic/demo identities; deliberate outages and destructive migration tests stay in isolation |

Before a run, record the code revision, dependency-lock/pin revision, migration revision, database environment label, browser/version, and relevant nonsecret configuration. Log whether testing uses HTTP development or HTTPS hosting. Record SESSION_TTL_SECONDS for that run; this document does not choose the application's normal session lifetime.

Secrets remain in local/host configuration. Test passwords are generated or supplied privately during fixture setup, never written into this document or the evidence report. Do not print connection strings, session cookies, CSRF values, or password hashes.

### Preconditions for an executable S01 run

1. S01 implementation exists and the selected runtime/dependency pins are recorded.
2. Initial migration and initial Admin setup are available. Fixture provisioning creates valid fixed-role accounts and required profile relationships without inventing public employee registration.
3. The test harness verifies database isolation before any schema reset or fixture deletion.
4. Logical operations in section 5 are mapped to the actual implementation's routes, schemas, cookie name, CSRF transport, and role guard. Record these bindings with the run.
5. A real browser can reach local development and the built hosted application. Hosting unavailability is a blocked hosted check, not a local-test pass.

These are implementation/run prerequisites. They are not unresolved scope decisions, and no additional service or architecture choice is requested.

## 4. S01 fixture catalogue

Use these stable labels in tests and evidence. The example login names are synthetic fixture data, not real accounts.

| Fixture | Definition | Used to prove |
| --- | --- | --- |
| U-C1 | Active Customer, `customer.one@example.test`, owned business profile | Valid Customer login and own session identity |
| U-C2 | Second active Customer, `customer.two@example.test`, separate profile | Isolation between sessions and identities |
| U-E1 | Active Employee, `employee.one@example.test`, employee profile | Employee role access |
| U-A1 | Active Admin, `admin.one@example.test`, provisioned through approved setup | Admin role access |
| U-OFF | Inactive account with otherwise valid credentials | Inactive login rejection |
| U-NONE | Login identifier absent from the database | Generic invalid-login behavior |
| S-VALID | Valid unexpired session belonging to one active fixture user | Authenticated requests and CSRF checks |
| S-REVOKED | Previously valid session explicitly revoked/invalidated in test setup | Server rejection of a replayed session |
| S-EXPIRED | Session whose authoritative expiry has been reached | Server-side expiry enforcement |
| S-OTHER | Independent valid session for U-C2 with its own CSRF value | Session-bound CSRF isolation |
| O-TRUSTED | Exact browser origin configured for the current environment | Valid state-changing requests |
| O-OTHER | Untrusted origin, such as `https://untrusted.example.test` | Origin rejection |
| DB-FAIL | Isolated test database failure or controlled failure injection | Fail-closed behavior and honest error reporting |

For each fixture, verify active state, fixed role, and intended profile association before exercising login. Use correct/incorrect private passwords without including their values in reports. Each test starts from an explicit session state; an old valid cookie must not make a failed-login test appear successful.

For expiry tests, control the test clock or stored expiry. Check immediately before the recorded expiry and at/after it, without a long sleep. Do not add a clock-control endpoint to the deployed application.

## 5. Observable operation contract

These labels identify real S01 behavior without inventing unapproved URL paths. Bind them to actual implemented requests before executing tests. An unbound operation is **BLOCKED**, not passed.

| Logical operation | Input / action | Required observable result |
| --- | --- | --- |
| Sign in | Validated login identifier/password and trusted Origin | Active account gets a newly established server-managed session and its own role identity |
| Read current session | Browser session cookie | Valid session resolves to its actual user/role; invalid/expired session grants no protected access |
| Resolve portal access | Authenticated identity and requested portal | Matching portal is allowed; another role's portal is denied or safely redirected without protected content |
| Sign out | Valid session, trusted Origin, session-bound CSRF token | Server session is invalidated and browser authentication cookie is expired/cleared |
| Initial Admin setup | Authorized local setup action with private credentials | Admin exists with correct fixed role and approved password hashing; no public bootstrap endpoint |

### Response and data expectations

- Successful login returns only the identity/session information needed by the frontend. It must not expose password hashes, another account's profile, or the session secret in a JSON body or readable browser storage.
- Wrong password, nonexistent identifier, and inactive account share a generic credential-failure message. They create no newly usable authenticated session.
- Missing/invalid inputs produce structured validation feedback using the approved code/message/optional-field-errors format. Password input is never silently trimmed or transformed into a different password.
- Valid authenticated reads return the session owner's identity, regardless of submitted user/role claims. Client-controlled role values cannot grant authority.
- Unauthenticated access, forbidden role access, validation errors, and dependency failures are distinguishable to the application. Record actual HTTP statuses and error codes in the binding record; do not call an error a success solely because the UI rendered.
- Login initially has no authenticated session-bound CSRF token. Its mandatory protection here is trusted Origin validation. Authenticated mutations, including logout, require both trusted Origin and a valid session-bound CSRF token.
- Ordinary read-only requests must not change business or authentication state through an action disguised as navigation. Backend expiry enforcement still applies to reads.

### Portal authorization matrix

| Current identity | Customer portal | Employee portal | Admin portal |
| --- | --- | --- | --- |
| No valid session | Require login | Require login | Require login |
| Active Customer | Allow | Deny / safe redirect | Deny / safe redirect |
| Active Employee | Deny / safe redirect | Allow | Deny / safe redirect |
| Active Admin | Deny / safe redirect | Deny / safe redirect | Allow |
| Expired/revoked/inactive identity | Require login | Require login | Require login |

Admin manages customer/employee records through Admin features, not by automatically becoming those users. S01 shells contain no business data yet. Verify the real backend role guard directly and through any actual protected S01 role boundary; do not add a fake privileged business endpoint only for testing. S02 must repeat the checks against real Admin account-management actions.

## 6. S01 automated and integration cases

**All cases below are initially NOT RUN.** A case can contain parameterized rows; every required row must pass before the case passes. “No change” means no new usable session or unauthorized mutation; harmless internal security logging is not prohibited.

| ID | Arrange and action | Pass condition | Traceability |
| --- | --- | --- | --- |
| S01-V01 | Sign in separately as U-C1, U-E1, U-A1 with valid credentials and O-TRUSTED | Each obtains a persisted session for the correct user/role and can read its own identity | REQ-02; AC-01-03 |
| S01-V02 | Fresh unauthenticated client: wrong password, U-NONE, then U-OFF with correct password | Same generic credential failure; no new usable authenticated session or protected content | REQ-02; NFR-01, NFR-03 |
| S01-V03 | Omit identifier/password; send wrong field types; submit malformed request body | Structured field/request validation; no crash details, echoed password, or new session | NFR-03, NFR-06 |
| S01-V04 | Sign in with a valid private password, then a changed/incorrect value including whitespace variants | Only the exact valid password authenticates; no silent password normalization | REQ-02; NFR-01 |
| S01-V05 | Supply invented role/user claims with otherwise valid U-C1 login/session | Rejected extra claims or ignored for authority; resolved identity remains U-C1/Customer | REQ-02; NFR-01 |
| S01-V06 | Read protected session context without cookie, with unknown cookie, then S-REVOKED | No protected identity/content; app receives unauthenticated outcome | REQ-02; AC-01-04 portion |
| S01-V07 | Exercise each row of portal matrix and the actual backend role guard | Only matching active role is admitted; hiding links alone is insufficient | AC-01-03; NFR-01 |
| S01-V08 | Establish session, then complete a new successful login in the same client | Login rotates session identifier; replaced identifier cannot be reused for access; new session works | CONTEXT §8; NFR-02 |
| S01-V09 | Create session with known test expiry; read just before, exactly at, and after expiry | Valid before expiry; rejected at/after expiry even if client still sends the cookie | AC-01-04 portion; NFR-01 |
| S01-V10 | With S-VALID, trusted Origin and correct CSRF, sign out; replay old cookie | Server session no longer authorizes; cookie clearing is returned; replay remains denied | REQ-02; AC-01-04 portion |
| S01-V11 | Sign out twice or submit an expired session to logout | No session is recreated and no server crash occurs; already-signed-out state stays unauthenticated | REQ-02; NFR-03 |
| S01-V12 | Attempt login with valid credentials for each Origin case in section 7 | Only trusted Origin may establish a session; rejected cases create no usable session | AC-01-05; NFR-02 |
| S01-V13 | With S-VALID and otherwise correct logout request, exercise rejected Origin cases | Mutation rejected; existing session is not falsely reported revoked by that request | AC-01-05; NFR-02 |
| S01-V14 | With trusted Origin and S-VALID, omit CSRF or use malformed/incorrect token | Logout rejected; session remains valid until a legitimate logout/expiry | AC-01-05; NFR-02 |
| S01-V15 | Use S-OTHER's CSRF with S-VALID; repeat with token from a replaced session | Both tokens fail for the current session; a valid current token still permits logout | AC-01-05; NFR-02 |
| S01-V16 | Read current session through two independent clients U-C1/U-C2; inject other user's identifier | Each response belongs only to its authenticated user; no cross-session identity or CSRF leakage | NFR-01, NFR-06 |
| S01-V17 | Establish session, then mark its user inactive in isolated fixture state; make next protected request | Access denied despite still-unexpired cookie; no new action succeeds | CONTEXT §§5, 8; NFR-01 |
| S01-V18 | Fail database write during login/session creation | No usable authenticated session is claimed; restored service does not reveal a falsely committed session | NFR-03, NFR-04 |
| S01-V19 | Fail session lookup/database access during a protected request | Fail closed with honest service error; no fallback to client role/local storage or cached authorization | NFR-01, NFR-03 |
| S01-V20 | Fail logout's server invalidation operation | Do not claim verified server revocation; communicate failure safely; after recovery a legitimate retry can revoke | NFR-03, NFR-04 |
| S01-V21 | Inspect synthetic-user password storage and configured verifier | Argon2id verification works; hash column supports VARCHAR(255); no plaintext password column/value storage | CONTEXT §8; NFR-06 |
| S01-V22 | Inspect login/logout headers and public response/configuration output | Correct cookie attributes for environment; no exposed session secret, password/hash, or backend credentials | NFR-02, NFR-06 |
| S01-V23 | Run initial migration on empty isolated PostgreSQL; provision Admin and synthetic roles | Valid schema/relations/session persistence; provisioning succeeds without manual schema edits | S01 foundation; NFR-09 |
| S01-V24 | Re-run migration to same head against populated fixture DB; restart API before session expiry | Existing identities/records persist; valid database session still resolves; logout state is not resurrected | NFR-09 |
| S01-V25 | Run isolated CI backend suite and frontend build; inspect CI connection labels | Checks execute against dedicated test data; successful build; no demo DB reset or secrets in outputs | NFR-06, NFR-10 |
| S01-V26 | Capture normal login failure, validation failure, and injected database-error logs in isolation | Sanitized errors; no passwords, cookie/CSRF values, connection strings, or raw SQL secrets in evidence | NFR-03, NFR-06 |

V17 tests the session guard with fixture state only. It does not pass the S02 Admin deactivation journey. V24 checks the existing S01 migration and restart; upgrade compatibility for subsequent migrations must be added when those migrations exist.

## 7. Origin, CSRF, and cookie matrices

### Mutation Origin matrix

Run the following against login and authenticated logout. For logout, use a valid session and correct CSRF token to isolate the Origin check.

| Origin sent | Expected result |
| --- | --- |
| Exact O-TRUSTED, including intended scheme/host/port | Allow Origin check; remaining credentials/session/CSRF checks still apply |
| O-OTHER | Reject mutation |
| Origin header absent | Reject mutation |
| Literal `null` Origin | Reject mutation |
| Trusted host with unconfigured scheme or port | Reject mutation |
| Lookalike/suffix host containing the trusted hostname | Reject mutation |

Use a direct test client to construct absent/null/untrusted headers; browsers may prevent some test inputs. Then independently prove that an ordinary browser login/logout works through the Vite proxy and hosted same-origin route. Passing fabricated HTTP requests alone does not prove the browser configuration works.

### Authenticated CSRF matrix

With trusted Origin and valid session, missing, malformed, incorrect, other-session, and replaced-session tokens all fail. Only the current session's valid token may authorize logout. A valid token cannot compensate for an expired session or untrusted Origin. Do not log the token values used to establish this evidence.

### Cookie checks

| Property | Local development | Hosted HTTPS |
| --- | --- | --- |
| HttpOnly | Required for authentication cookie | Required |
| SameSite | Lax | Lax |
| Secure | Configure for actual transport; record HTTP-only development exception if used | Required |
| Cookie reachability | Browser sends cookie on relative API calls through Vite origin | Browser sends cookie to the same hosted origin |
| Expiry and logout | Server rejects expired/revoked session regardless of cookie presence | Same |
| Browser storage | No authentication session secret in localStorage/sessionStorage or script-readable cookie | Same |

A CSRF token may be available to frontend code through its intended mechanism; HttpOnly applies to the authentication cookie. Evidence records attributes and whether values differ, never the secret values themselves.

## 8. S01 browser and hosted walkthrough

| ID | Steps | Required observation |
| --- | --- | --- |
| S01-B01 | Open a protected portal link in a clean browser session | Login is required; no protected identity/content flashes before session resolution |
| S01-B02 | Log in as each active role using separate sessions | Correct portal shell, identity, and shared navigation; no invented dashboard metrics |
| S01-B03 | Use wrong credentials, then correct them | Generic failure shown; password is not echoed; retry succeeds without duplicate form submissions |
| S01-B04 | Refresh and open a direct protected link while authenticated | Correct session persists; built frontend routing works; no unnecessary login or wrong-portal access |
| S01-B05 | Try another role's portal URL and use browser back/forward | Safe denial/redirect; no protected content from another role |
| S01-B06 | Log out in one tab; make a protected request in another; use browser back and refresh | Revoked session grants no fresh data/actions; stale authenticated UI is cleared when state is resolved |
| S01-B07 | Reach configured test expiry, then request protected content | Prompt to log in again; no silent replay of an unfinished mutation after login |
| S01-B08 | Use keyboard navigation and form submission; observe loading and error states | Labeled controls, visible focus, usable feedback, no color-only error meaning; submission state is understandable |
| S01-B09 | Exercise local frontend through Vite proxy with browser network inspection | Relative same-origin API calls, cookies retained, legitimate Origin/CSRF accepted |
| S01-B10 | Repeat login, refresh/direct link, and logout on hosted HTTPS; inspect cookie attributes | Same-origin hosted flow succeeds with Secure/HttpOnly/SameSite=Lax; no runtime secrets in frontend responses |
| S01-B11 | Restart the application without wiping persistent data; revisit an unexpired session, then logged-out session | Valid session survives API restart; revoked session remains invalid; existing identities persist |
| S01-B12 | Simulate local network/API failure during session resolution or logout, then recover | No invented success or fallback authorization; clear retry/login recovery without exposing credentials |

S01-B06 does not require a new real-time cross-tab notification system. The security requirement is that revoked credentials cannot authorize further requests; cached visual state must not grant access.

Hosted smoke work uses synthetic accounts and safe restart checks only. Deliberate database outages and rollback tests run in the isolated test environment. If hosting sleeps or is unavailable, record the blocked condition and rerun after recovery.

## 9. Traceability and completion boundaries

| Source requirement/scenario | S01 evidence | Not claimed here |
| --- | --- | --- |
| REQ-02 / AC-01-03 | V01, V05, V07, V16; B01–B05 | Business features inside future portals |
| AC-01-04, logout/expiry portion | V06, V08–V11, V24; B06–B07, B11 | Admin reset/deactivation workflow completion in S02 |
| AC-01-05 | V12–V15; Origin/CSRF matrices; B09–B10 | Coverage of mutations not yet introduced |
| NFR-01 access/ownership | V01–V07, V09–V11, V16–V17, V19; portal matrix | Cross-customer RFQs/files/orders, tested in their slices |
| NFR-02 session/CSRF | V08–V15, V22; B09–B10 | A passed check for every future endpoint |
| NFR-03 validation/errors | V02–V04, V11, V18–V20, V26; B03, B07, B12 | Future form-specific validation |
| NFR-04 atomicity | V18, V20 | Quote/payment/stock concurrency |
| NFR-06 secrets | V21–V22, V25–V26; B10 | Future file/export contents |
| NFR-08 usable shared UI | B01–B08 | Final dashboards and public mobile layout |
| NFR-09 persistence | V23–V24; B11 | Private uploads and later migration upgrades |
| NFR-10 execution evidence | V25 plus complete case records | An unexecuted suite passing merely because tests exist |

NFR-05 file safety and NFR-07 business/report truthfulness receive feature-specific checks when those data surfaces exist. S01 must still avoid fabricated portal data. No requirement is waived by this staged allocation.

## 10. Evidence record and result vocabulary

For every executed case, record:

| Field | Content |
| --- | --- |
| Case and coverage | Case ID, requirement/scenario IDs, parameterized row if applicable |
| Tested version | Commit/revision and dependency/migration versions |
| Environment | Local/test/CI/hosted label; browser if relevant; no secret connection values |
| Fixture and preconditions | Fixture labels, active role, session state, clock condition |
| Action | Actual implemented operation/route binding and sanitized input description |
| Expected | Observable pass condition from this document |
| Actual | What was observed, including authorized/denied outcome and state changes |
| Evidence | Sanitized test output or manual observation reference |
| Result | NOT RUN, PASS, FAIL, or BLOCKED |
| Follow-up | Defect reference, cause if established, required rerun |

- **NOT RUN:** No execution evidence yet.
- **PASS:** Actual result matches the condition for every required row on the recorded version/environment.
- **FAIL:** The implementation was exercised and violated the expected behavior.
- **BLOCKED:** A prerequisite, dependency, or environment prevented a valid execution. State the reason; do not convert it to PASS.

Do not paste secrets or raw authentication headers into evidence. Browser screenshots are optional, not required. Prefer sanitized text observations; if screenshots are captured for a project report, redact private credentials and tokens first.

A later code change affecting a passing case requires a rerun. Retain earlier observations as history instead of presenting them as evidence for a different version.

## 11. S01 exit gate

S01 is ready to close only when:

1. All 26 V cases and 12 B cases have passing evidence for their applicable environment, including all required matrix rows.
2. No case is silently skipped or counted as passing because a dependency is unavailable. Required hosted checks remain blocking for closing the hosted S01 deliverable.
3. Credential failures, role checks, expiry, logout, Origin/CSRF, and fail-closed behavior hold against actual backend/session state.
4. Initial migration, retained fixture records, password storage, isolated CI tests, and frontend build are evidenced.
5. Browser development-proxy and deployed HTTPS flows work with their correct cookie attributes.
6. No unresolved defect compromises access, confidentiality, persistence, or the stated S01 journey. Other observed defects remain visible and must meet the slice's acceptance conditions before closure.
7. The completion report explicitly limits its claim to S01 and records which account-management aspects remain for S02.

Creating this document passes none of these gates. Current results are **26 V cases NOT RUN; 12 B cases NOT RUN; S01 NOT VERIFIED**.

## 12. Verification obligations for remaining slices

Before each slice is implemented, expand its contract using the same fixture/action/expected-state/evidence structure. Reference the existing PRP AC IDs instead of redefining their requirements. Rows below remain **CONTRACT NOT EXPANDED / NOT RUN** unless a linked slice evidence record explicitly states otherwise. S07 preparation/review has a bounded [contract and local evidence](S07_VERIFICATION.md); hosted verification and S08 acceptance remain separate.

| Slice | Required focus before closure | Existing acceptance source |
| --- | --- | --- |
| S02 | Atomic registration/profile, privileged-role tampering, account status/reset, forced password change, existing-session invalidation | PRP-001 AC-01-01/02/04/06/07/08 |
| S03 | Persisted catalogue/detail consistency, active filters, price labeling, empty/error states, public access | PRP-002 AC-02-01/02/03; image display part of AC-02-06 |
| S04 | Admin product/image writes, valid/mismatched/oversize images, object/metadata cleanup, deactivation/history | PRP-002 AC-02-04/05/06 |
| S05 | Existing/custom RFQ without files, required inputs, review/edit preservation, owner/Admin visibility | PRP-003 AC-03-01/02/03/08 |
| S06 | Two-file total and 20 MB boundaries, concurrent uploads, content checks, private preview/download, restart persistence, profile images | PRP-003 AC-03-04/05/06/07; REQ-03 image portion |
| S07 | [Expanded contract and local evidence](S07_VERIFICATION.md): version ordering, immediate superseding, manual provenance, send/reject/change-request behavior | PRP-005 AC-05-01 through AC-05-05; manual part of PRP-004 |
| S08 | Acceptance-time validity, race/rollback/idempotency, immutable commercial snapshots, one order/invoice, unpaid cancellation | PRP-005 AC-05-02/04/06/07/08; PRP-006 AC-06-01/06/07 |
| S09 | Partial/failed/full payment, duplicate key/content mismatch, concurrent overpayment, cancellation race | PRP-006 AC-06-03 through AC-06-08 |
| S10 | Paid assignment, one-job uniqueness, assigned file access, progress limits/history/pause, truthful tracking | PRP-007 AC-07-01 through AC-07-05; PRP-006 AC-06-02 |
| S11 | Admin-only QC, note/progress on rework, resubmission, stale decisions, separate paid/approved delivery/closure | PRP-007 AC-07-05/06/08/09 |
| S12 | Employee issue ownership, optional own-job relation, attachments, Admin status handling | PRP-007 AC-07-07 |
| S13 | Manual stock/reasons/history, no negative stock under concurrency, atomic rollback, threshold display | PRP-008 AC-08-01 through AC-08-06 |
| S14 | Unified ticket/message ownership, valid own-order reference, attachment safety, chronological conversation/status | PRP-009 AC-09-01 through AC-09-06 |
| S15 | Reproducible synthetic held-out evaluation, saved preprocessing/version, no API training, manual fallback/provenance | PRP-004 AC-04-01 through AC-04-07 |
| S16 | Role dashboard isolation, known-data totals/date semantics, complete filtered safe CSV, full release walkthrough | PRP-010 AC-10-01 through AC-10-07; master PRP release gate |

For concurrency cases, two requests must overlap around the relevant state decision, with final database invariants checked. Two sequential clicks are not evidence of race safety. For financial cases, assert decimal amounts and immutable snapshots rather than rounded screenshot totals. For private files, assert authorization and returned bytes, not only a visible download button.

## 13. Reusable slice contract checklist

Each later contract must state:

- Slice ID, requirement portions, PRP AC IDs, dependencies, and exclusions.
- Concrete fixture records and relationships, including a second unrelated user where ownership matters.
- Actual request/UI bindings and precise field/range/format boundaries needed by that slice.
- Success, validation, unauthorized, missing, conflict, dependency-failure, and recovery cases as applicable.
- Persisted before/after expectations; atomicity, uniqueness, retry, concurrency, and history assertions where relevant.
- Browser checks for honest state and permitted actions, plus meaningful backend automation.
- Exact migration/persistence checks introduced by that change.
- Evidence fields, execution status, regression selection, and exit gate.

No later contract may introduce suppliers, real payments, notifications, configurable roles, multiple jobs per order, CAD analysis, or other excluded scope. Return a contradiction to the governing document rather than silently changing its business rule.

## 14. Current status and next document

**Completed:** Shared verification framework and the S01 contract, with 38 named cases plus explicit role/Origin/CSRF/cookie matrices.

**Not performed:** Application coding, account provisioning, migration execution, test runs, browser checks, or hosted checks. No pass rate is reported.

**Next document:** `docs/S01_IMPLEMENTATION_PROMPTS.md` — a bounded prompt chain for implementing S01 against this verification contract. It should carry the approved context, exact slice scope, dependencies, evidence expectations, and stop conditions into each step. It must not expand into S02 or the entire KPC application.

After the prompt chain is prepared, implementation and actual verification can begin. Keep context, PRPs, slice plan, and verification evidence separate and traceable.
