# Catalogue content

Normal `/products` and `/products/:id` routes use `/api/products`. They never substitute demo records for empty/error responses.

Open `/products?preview=1` for the UI reference preview. Sample products and detail fields live in `catalogue.js`; the preview banner labels them as illustrative. Preview RFQ actions go to sign-in without selecting a fake product.

Replace an image entry with `{ src: '/images/your-product.jpg', alt: 'Product description' }`. Multiple entries display selectable gallery thumbnails. Crop coordinates are only for the supplied reference artwork; omit `crop` for real images.

Optional product fields consumed by the UI:

- `images`: image objects as above
- `specifications`: `{ label, value }` rows
- `process`, `applications`, `description`: text
- `category_name`, `material_type`, `indicative_price`

The current persisted product model supplies description, category, material and indicative price. Images, extended specifications, process and applications are not persisted yet: their display slots show fallbacks until a later product-management/schema change supplies them. Editing the preview dataset does not alter real products.

No specification PDF download is added: it is excluded by PRP-002.
