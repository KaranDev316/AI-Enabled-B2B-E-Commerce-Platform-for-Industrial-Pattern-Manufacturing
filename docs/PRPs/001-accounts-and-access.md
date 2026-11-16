# PRP-001 — Accounts, profiles, and access

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and the shared rules in [PRP.md](../PRP.md) first. This file owns REQ-01–REQ-04. Priority is **Must** for every requirement. All acceptance scenarios are expected behavior and remain **NOT VERIFIED** until implemented and exercised.

## Goal and users

Visitors become customers. Customers, employees, and Admin use accounts appropriate to their work and see only permitted records. One customer login owns one business profile.

## Requirements

### REQ-01 — Visitor can register a customer account

- **Actor** — Visitor.
- **Trigger** — Submits registration with personal, login, and business-profile information.
- **Success** — A customer account and its associated business profile are saved together. The customer can then sign in.
- **Failure** — Invalid or duplicate login information gives actionable feedback without creating an incomplete account/profile pair. A submitted privileged role does not grant access.
- **Constraints** — Public registration creates Customer accounts only. Supplier registration, shared-business invitations, and email notification/verification workflows are outside scope.
- **Source** — CONTEXT §§3, 5, 8, 11 and the supplied Registration sequence diagram.

### REQ-02 — User can sign in and end a protected session

- **Actor** — Customer, Employee, Admin.
- **Trigger** — Submits login, opens a protected view, or logs out.
- **Success** — Valid credentials for an active account establish a session and show the appropriate portal. Logout ends access. Normal navigation retains the session until configured expiry or invalidation.
- **Failure** — Wrong credentials or inactive accounts show a generic login failure. Expired sessions require login again without silently repeating an unfinished mutation. Unauthorized navigation exposes no protected content.
- **Constraints** — PostgreSQL sessions, Argon2id, cookie properties, Origin checks, and CSRF rules follow CONTEXT §8. Session lifetime is configuration through SESSION_TTL_SECONDS. The three fixed roles govern access.
- **Source** — CONTEXT §§4–5, 8 and Login sequence diagram.

### REQ-03 — User can maintain their own profile and password

- **Actor** — Signed-in Customer, Employee, Admin.
- **Trigger** — Opens profile, saves permitted changes, or changes password.
- **Success** — Valid edits persist and appear after refresh. Customer business details stay associated with the same account. Employee employment facts remain distinct from editable personal information. Password changes invalidate existing sessions and require fresh login.
- **Failure** — Invalid edits preserve current stored information and identify the affected fields. A user cannot change their own role, account activation, or another person's profile through this flow.
- **Constraints** — Use customer/employee profiles under the canonical User model. Profile images follow the shared image-upload rules. Two-factor authentication and performance Quick Info cards are excluded.
- **Source** — CONTEXT §§3, 5, 8, 10–11 and Customer Business Profile / Employee My Profile screens.

### REQ-04 — Admin can manage customer and employee account access

- **Actor** — Admin.
- **Trigger** — Creates an employee, changes account status, or resets a customer/employee password.
- **Success** — Employee creation permits the employee portal. Deactivation immediately invalidates affected sessions. Reset requires a password change at next login. Operational records remain linked to the same account.
- **Failure** — An unauthorized actor cannot perform these actions. Failed updates leave existing account state intact. A deactivated employee cannot continue editing an assigned job.
- **Constraints** — Initial Admin is provisioned through the setup command. Fixed roles replace the mockup Roles & Permissions interface. No role editor, Sales/Finance roles, supplier accounts, or email reset delivery.
- **Source** — CONTEXT §§3, 5, 8, 10–11 and Users & Roles screen, adapted to Users.

## Journeys

- Visitor registers, signs in, updates business details, and reaches RFQs.
- Admin creates an employee. Employee signs in and sees assigned work when available.
- Admin deactivates an account. Its open browser session loses protected access on the next request.
- Admin resets a password. The next login enters the mandatory password-change flow before normal work resumes.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-01-01 | REQ-01 | Valid registration creates exactly one Customer and one owned business profile |
| AC-01-02 | REQ-01 | Invalid/duplicate registration leaves no orphan profile and grants no privileged role |
| AC-01-03 | REQ-02 | Customer, Employee, and Admin each reach their own portal with an active session |
| AC-01-04 | REQ-02 | Logout, expiry, reset, and deactivation invalidate protected access |
| AC-01-05 | REQ-02 | Missing/invalid CSRF token or untrusted Origin rejects a protected mutation without changes |
| AC-01-06 | REQ-03 | Valid self-profile changes survive reload. Role/employment privilege tampering fails |
| AC-01-07 | REQ-04 | Admin-created employee can sign in. Customer cannot create or deactivate accounts |
| AC-01-08 | REQ-04 | Reset forces password change. Pre-reset sessions cannot perform new actions |

## Dependencies, risks, and exclusions

Depends on canonical user/profile/session records and the approved initial Admin setup. A shared computer must not retain a logged-out user's access. Credentials and session material stay out of screenshots, logs, and demo exports. Detailed permission evidence belongs to the slice verification contract. Backend authorization applies even if a page link is hidden.

The approved fixed-role boundary is complete. No additional identity provider, user invitation flow, configurable permission editor, or supplier portal is required.

## UI references

- `Business Profile with Orange Save Changes Button(1).png`
- `Modern Employee Portal Profile Dashboard(1).png`
- `KPC Users & Roles Dashboard(1).png`, with the excluded role-editor controls removed
- Registration and Login sequence diagrams supply flows where no approved full-page mockup was supplied.
