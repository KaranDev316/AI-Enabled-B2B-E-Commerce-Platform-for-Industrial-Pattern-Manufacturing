# Merge main into Samonta integration

Source: feature/samonta-integration at 193e823. Merged main: 36d7369.

- Catalogue API retains categories, specifications, images and active-only image delivery.
- Product details support canonical slugs and existing numeric product links.
- Samonta's public UI and hamburger menu remain the live pages. Both /catalogue and /products
  open the shared live catalogue. Main's alternate page source remains in the repository.
- Main's legal pages and global footer, hash scrolling, login/registration, RFQ product handoff,
  Vercel rewrites, build updates and audit/reference files remain.
- Product detail passes its ID to the existing protected customer RFQ handoff.
- Company/contact links target real anchors, and the global footer avoids duplicate portal footers.
- Local Vite proxy remains on backend port 8001 as configured by main.

No environment files, credentials, database records or migration ordering changed.

Validation: 79 backend tests passed; 1 PostgreSQL connection test skipped (no isolated test database configured). Frontend production build and Git whitespace/conflict-marker checks passed. Live browser walkthrough not performed.
