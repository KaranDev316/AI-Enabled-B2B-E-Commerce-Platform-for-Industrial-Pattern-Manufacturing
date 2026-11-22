# S12 — Employee production issues

Employee Report Issue retains the two-column reference: a new-issue form and the
employee's reported issues, with a status filter, issue details and handling history.
Admin reviews issues under Orders & Production → Production Issues.

Fields: optional own assigned job, production/machine/material/drawing type,
3–200 character title, 10–10000 character description, high/medium/low priority.
Admin records a handling note and open/in_review/in_progress/resolved status.
Resolved issues may be reopened by Admin with a new note. Status updates use an
expected version to reject stale changes. History is append-only through the API.

Attachments are optional: at most two JPG/JPEG, PNG or PDF files, 20 MB each,
validated on the server by extension, signature, non-empty contents and size.
Uploads use private persistent Supabase Storage; reports without attachments do not
require storage configuration. Generated object names are never returned to the browser.
If storage or a database write fails, metadata rolls back and uploaded objects are
submitted for cleanup. Cleanup failures are logged; an administrator may need to remove
an orphan if the storage service is unavailable. No partial association is reported as success.

Only Admin or the original reporting Employee can list/read/download/preview an issue.
An Employee cannot link someone else's job, update handling status, or inspect another
Employee's issue. Customers have no issue access. Mutations require session, role,
CSRF and trusted Origin checks. Reporting does not automatically pause a job, consume
stock, send notifications, or create a new production job.

Migration 011 follows 010. Models are separate from support tickets. The implementation
adds no new dependency. Reference: employee/report-issue.webp and global/ui-kit.webp;
the documented 20 MB limit overrides the old mockup's 10 MB label.
