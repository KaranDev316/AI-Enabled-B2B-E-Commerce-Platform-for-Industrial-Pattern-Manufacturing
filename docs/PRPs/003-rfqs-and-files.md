# PRP-003 — RFQ submission, review, and files

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-08–REQ-10. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Customers provide a standard-product or custom manufacturing requirement with drawings. Admin can inspect the saved request and its files before quoting.

## Requirements

### REQ-08 — Customer can submit a three-step RFQ

- **Actor** — Customer.
- **Trigger** — Starts an RFQ from the catalogue or Customer Portal.
- **Success** — Step 1 captures product/custom requirement, material, quantity, and description. Step 2 captures dimensions/specifications/notes and optional files. Step 3 reviews those details and business contact information. Submission saves an owned RFQ with an identifier and visible status.
- **Failure** — Invalid/missing required values identify the relevant fields. Back/edit preserves entered values. Failed submission preserves recoverable input and never reports a stored RFQ that does not exist.
- **Constraints** — Collect each input once and reuse it in review. Standard-product selection refers to an active catalogue product. Custom requirements do not require a catalogue product. File submission follows REQ-09. No separate direct custom-order flow bypasses quotation and payment.
- **Source** — CONTEXT §§3, 5–7 and the three RFQ wizard images.

### REQ-09 — Authorized user can upload, preview, and download RFQ files

- **Actor** — Owning Customer, Admin, and the assigned Employee after order/job assignment.
- **Trigger** — Adds/removes a permitted RFQ attachment before submission, previews an image/PDF, or downloads an authorized drawing.
- **Success** — The RFQ holds at most two files of at most 20 MB each. Original names are visible, generated storage keys are private, and downloads return the correct bytes. JPG/JPEG/PNG/PDF have previews. STEP/STP, IGES/IGS, STL, and DWG are downloadable.
- **Failure** — Extra, oversize, invalid, or unsupported files are rejected server-side. Unrelated users cannot access files by guessing an identifier or object key. Storage/metadata failure leaves no false success, inaccessible saved attachment, or intentionally abandoned object.
- **Constraints** — Enforce the limit across the RFQ, including concurrent submissions. Use private Supabase Storage. Validate content appropriately for the claimed type without CAD manufacturing analysis. Browser filenames/MIME alone are insufficient. Preview/download permission follows the parent record.
- **Source** — CONTEXT §§5, 7–8 and user amendment of two 20 MB RFQ files.

### REQ-10 — Customer and Admin can inspect saved RFQs and status

- **Actor** — Owning Customer and Admin.
- **Trigger** — Opens an RFQ list, selects an RFQ, or Admin reviews its contents.
- **Success** — Saved requirements, contact facts, attachments, and current review/quotation status refer to the same RFQ. Admin can proceed to estimation or quotation. Customer can distinguish a submitted request from an available quotation.
- **Failure** — Unknown/unavailable RFQs and an empty list have clear feedback. Another customer cannot retrieve the RFQ. A missing file does not remove the request or fabricate its contents.
- **Constraints** — Customer-visible status follows persisted actions. Email, WhatsApp, SMS, notifications, and a separate Customer Inquiry page are excluded.
- **Source** — CONTEXT §§3, 5–6 and Admin RFQs & Quotations screen / View RFQ Status sequence.

## Journeys

- Customer enters a custom requirement, uploads an image and CAD file, reviews, edits a field, and submits. Admin sees the final saved values and can download both files.
- Customer submits a valid requirement without attachments. Admin reviews the stated specification.
- A third file or a file over the limit is rejected. The remaining valid form data stays available.
- Storage fails partway through submission. The UI reports failure and the system reconciles saved metadata/objects before a successful retry.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-03-01 | REQ-08 | Existing-product and custom RFQs both complete the three-step flow |
| AC-03-02 | REQ-08 | Review shows the entered values once, and back/edit preserves input |
| AC-03-03 | REQ-08 | Optional-file omission succeeds. Missing required manufacturing inputs fails clearly |
| AC-03-04 | REQ-09 | Exactly two allowed files at the size boundary succeed. A third or oversized file fails |
| AC-03-05 | REQ-09 | Concurrent uploads cannot exceed two files for one RFQ |
| AC-03-06 | REQ-09 | Image/PDF preview and CAD download work. A second customer's file access fails |
| AC-03-07 | REQ-09 | Content/extension mismatch and storage failure produce no successful broken attachment |
| AC-03-08 | REQ-10 | Admin and owner see the saved RFQ; unrelated customers and unassigned employees cannot |

## Dependencies, risks, and exclusions

PRP-001 owns access and customer profiles. PRP-002 owns active product selection. PRP-007 owns employee assignment. PRP-004 and PRP-005 consume the saved RFQ. File storage and database updates can fail independently and require the consistency behavior above.

No CAD viewer, automated CAD analysis, saved-draft management feature, or requirement to upload five files is introduced.

## UI references

- `Custom Product RFQ Wizard Dashboard(1).png`
- `RFQ CAD Upload Wizard Interface(1).png`
- `RFQ Review and Submit Dashboard(1).png`
- `KPC RFQs and Quotations Dashboard(1).png`

Apply the shared Customer sidebar, two-file limit, and approved catalogue/custom flow instead of inconsistent example labels, filenames, or upload limits.
