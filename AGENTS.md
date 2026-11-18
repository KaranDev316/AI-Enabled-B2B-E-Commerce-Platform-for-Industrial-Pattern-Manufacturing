# KPC repository instructions for AI coding tools

These instructions apply to the entire repository. Read them before making changes.

## Mandatory UI design rules

1. **Follow the supplied designs. Do not invent a replacement visual design.** Start with `docs/ui-ux/README.md`, open the actual reference images for the screen being changed, and inspect `docs/ui-ux/global/ui-kit.webp`. Reading filenames or the index alone is insufficient.
2. Use `docs/ui-ux/public/`, `customer/`, `admin/`, or `employee/` for the relevant screen. Preserve the reference's main layout, section order, sidebar/header structure, color palette, typography hierarchy, card proportions, tables, forms, and primary actions.
3. Preserve the existing approved implementation. Extend its components and styles; do not replace page routes, page components, navigation, or shared layouts with an alternative design merely to add a feature.
4. **A feature request, backend integration, bug fix, refactor, or merge is not permission to redesign the UI.** A different visual direction requires an explicit redesign instruction from the task owner. Personal taste, AI-generated suggestions, or another framework's default template are not design authority.
5. Small practical adaptations are allowed for responsive layouts, accessibility, actual supported fields, and real application states. Keep the screen recognizably aligned with its reference. Do not add promotional banners, decorative sections, new navigation systems, dashboards, or controls that the task and references do not call for.
6. `docs/CONTEXT.md`, `docs/PRP.md`, and the applicable PRP govern functionality. Historical mockups cannot introduce excluded features or override access controls. Use real persisted records; never copy sample companies, amounts, counts, dates, notifications, verification badges, progress percentages, or AI recommendations into the live application as facts.
7. Missing backend capabilities do not justify a new layout. Keep the relevant reference structure and show an honest empty, unavailable, loading, or error state. Do not invent endpoints or present an unavailable operation as working.
8. Keep changes focused and simple. Do not introduce a new UI framework, parallel design system, generic layout abstraction, or dependencies unless the actual task needs them. Do not change unrelated portals.
9. Do not overwrite reference images to make them match an implementation. Keep the original design assets intact unless the task explicitly requests updating them.

## Existing UI to preserve

- Public home: `frontend/src/pages/LandingPage.jsx` and `LandingPage.css`.
- Public catalogue/details: `frontend/src/pages/CataloguePage.jsx` and `CataloguePage.css`.
- Public navigation: `frontend/src/components/PublicHeader.jsx`.
- Customer shell: `frontend/src/components/CustomerLayout.jsx`.
- Customer dashboard/profile: `CustomerDashboard.jsx` and `CustomerProfile.jsx` in that directory.
- Customer workflows/styles: `frontend/src/pages/CustomerPortal.jsx` and `CustomerPortal.css`.
- Preserve these route bindings in `frontend/src/main.jsx` when integrating backend changes. The presence of another page implementation in the repository does not make it the approved replacement.
- Keep public pages and portals visually consistent with their own references. Do not impose an Admin/shared sidebar on the public site or replace the customer sidebar with another shell.

## Integration and merge rules

- Inspect the working tree before editing or pulling. Preserve teammates' unrelated work and the task owner's uncommitted changes.
- Resolve conflicts by combining functional changes with the approved UI. Do not blindly select an entire incoming or local file. A newer commit is not automatically a design decision.
- Keep useful backend, schema, image-upload, and Admin changes while adapting data contracts to the approved frontend. Do not revert unrelated functionality to restore a design.
- The local frontend runs on `127.0.0.1:5173`; its API proxy targets `127.0.0.1:8001`. Do not silently change those ports during unrelated work.
- Hosted frontend requests use relative `/api` URLs and `frontend/vercel.json` proxies them to Render. Preserve this arrangement unless deployment changes are explicitly requested.
- Never commit `.env` files, database URLs containing credentials, passwords, session cookies, or private tokens.

## Required verification for UI work

1. State which reference screens guide the change before implementation.
2. Compare the implemented screen visually with those references at desktop and a narrow/mobile size. Check navigation, spacing, hierarchy, overflow, and the relevant loading/empty/error states.
3. Exercise the affected controls and run `npm --prefix frontend run build`. Run additional checks appropriate to any functional changes.
4. Review the diff for unrelated route, shared-style, layout, configuration, or dependency changes.
5. In the completion report, name the references used, describe any intentional adaptations and their reason, and report checks actually performed. If browser verification is unavailable, state that limitation; do not claim visual verification passed.

## When a design decision is missing

Use the closest existing reference and established component for small details. If a requested change would materially depart from the approved design and the task does not authorize that departure, explain the conflict and ask for direction before replacing the design. Continue any independent work that does not depend on that decision.
