// Temporary design-preview content. Replace images with image URLs and edit
// specification arrays here. Never used as a fallback for API errors/empty data.
import reference from '../assets/catalogue-reference.webp';
export const demoProducts = ['Metallic Housing Pattern', 'Metallic Plate Pattern', 'Core Box Pattern', 'Gear Housing Pattern', 'Complex Casting Pattern', 'Base Plate Pattern'].map((name, i) => ({
  id: `preview-${i + 1}`, name, slug: `preview-${i + 1}`, category_name: 'Metallic Patterns', material_type: ['Aluminium', 'Cast Iron', 'Aluminium', 'Cast Iron', 'Aluminium', 'Steel'][i], indicative_price: [18500,22000,16000,28000,24500,12500][i],
  description: 'Illustrative industrial pattern for the catalogue design preview. Final product information will replace this sample content.',
  images: [{ src: reference, crop: { x: 880, y: 127, width: 408, height: 302, sourceWidth: 1695, sourceHeight: 928 }, alt: name }],
  specifications: [{ label: 'Max dimensions', value: '500 × 400 × 120 mm' }, { label: 'Tolerance', value: '±0.05 mm' }, { label: 'Standard', value: 'IS/ISO 8062' }, { label: 'Material grade', value: 'CI FG 260' }, { label: 'Surface finish', value: 'Ra 3.2–6.3 μm' }],
  applications: 'Sample applications: foundry and industrial machinery components.', process: 'Sample process: sand casting.',
}));
export function productPrice(value) { return value == null ? 'Price on request' : new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value); }
