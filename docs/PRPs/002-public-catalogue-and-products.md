# PRP-002 — Public catalogue and product management

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-05–REQ-07. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Visitors and customers understand KPC's manufacturing capabilities and find relevant products. Admin maintains the catalogue used by the RFQ journey.

## Requirements

### REQ-05 — Visitor or customer can browse company and product information

- **Actor** — Visitor, Customer.
- **Trigger** — Opens the landing page/catalogue, searches or filters, or selects a product.
- **Success** — Company information appears on the landing page. Active products have consistent names, categories, material/specification details, images, and indicative pricing where provided. Product selection leads to its correct details and an RFQ entry point.
- **Failure** — Loading, empty catalogue, no matching results, unavailable data, and unavailable/inactive product are distinguishable. An unauthenticated RFQ attempt leads to login without submitting a request automatically.
- **Constraints** — Catalogue prices are indicative. A missing price is displayed as on request. Official prices come from Admin quotations. There is one shared public catalogue for visitors/customers.
- **Source** — CONTEXT §§3, 6, 10 and Public Landing/Catalogue/Details screens.

### REQ-06 — Admin can maintain catalogue products and categories

- **Actor** — Admin.
- **Trigger** — Adds/edits a product or category, or activates/deactivates a product.
- **Success** — Valid details persist and are reflected in the catalogue. Deactivated products disappear from new public selection while historical RFQs, accepted quotations, and orders retain their record references and snapshots.
- **Failure** — Invalid values, missing category references, or unauthorized changes preserve stored data and provide feedback. A form save failure retains the user's input for correction.
- **Constraints** — Use the categories/specifications needed by the demonstration catalogue. Activation controls replace destructive removal of products referenced by business records. Supplier and procurement facts are excluded.
- **Source** — CONTEXT §§3, 8, 11 and Product Management screen.

### REQ-07 — Admin can associate product images and users can view them

- **Actor** — Admin writes, Visitor/Customer reads active catalogue imagery.
- **Trigger** — Uploads/selects a product image or opens a product view.
- **Success** — JPG/JPEG or PNG images appear for the correct product and retain their aspect ratio. Product-image permission is distinct from private customer-document permission.
- **Failure** — Oversized/unsupported/invalid images are rejected with no broken saved association. Missing imagery has a clear fallback. Storage failure does not create a successful upload claim.
- **Constraints** — 20 MB per image and at most two files per upload submission, backend validation, generated storage keys, and private persistent storage follow CONTEXT §7. No image generation or image-processing product feature is required.
- **Source** — CONTEXT §§3, 7–8 and catalogue/product-management images.

## Journeys

- Visitor opens company information, filters products, inspects a selected product, and proceeds to customer login to start an RFQ.
- Admin edits a product. Public views show the saved change. Existing accepted order/invoice snapshots retain the earlier agreed details.
- Admin deactivates a product. It is unavailable for new public selection, while related historical records remain inspectable by their authorized users.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-02-01 | REQ-05 | Catalogue and product details identify the same product and its persisted specifications |
| AC-02-02 | REQ-05 | Search/filter results reflect active records. Empty search can be cleared |
| AC-02-03 | REQ-05 | Missing price says on request, and a catalogue amount is clearly indicative |
| AC-02-04 | REQ-06 | Valid Admin changes survive refresh and unauthorized writes fail |
| AC-02-05 | REQ-06 | Deactivation prevents new selection without changing historical snapshots |
| AC-02-06 | REQ-07 | Valid image displays for its product. Unsupported or oversized image leaves no saved broken association |

## Dependencies, risks, and exclusions

Admin writes depend on PRP-001. RFQ handoff depends on PRP-003. Public reads do not require a customer session. Source product pictures and catalogue numbers are demonstration content, not a requirement to fabricate product capabilities.

Company information remains within the landing page. No cart, instant checkout, customer recommendations, separate supplier catalogue, or specification-PDF generation capability is added by this PRP.

## UI references

- `LANDING PAGE.png`, retaining desktop/mobile intent
- `PRODUCT CATALOGUE AND DETAILS.png`
- `KPC Product Management Dashboard(1).png`
