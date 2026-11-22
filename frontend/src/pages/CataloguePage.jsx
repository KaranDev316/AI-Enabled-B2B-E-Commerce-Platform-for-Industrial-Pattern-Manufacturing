import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { PublicHeader } from '../components/PublicHeader';
import { demoProducts, productPrice } from '../data/catalogue';
import { downloadSpecifications } from '../data/downloadSpecifications';
import './LandingPage.css';
import './CataloguePage.css';
import { useKpcLiveSync, LiveSyncBadge } from '../utils/kpcLiveSync.jsx';
const API = import.meta.env.VITE_API_BASE_URL || '/api';

export function ProductImage({ image, name }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [image]);
  if (!image || failed) return <div className="catalogue-image catalogue-image-empty">Image coming soon</div>;
  const crop = image.crop;
  return <div className="catalogue-image" role="img" aria-label={image.alt || name}><img src={image.src || image.url} alt="" onError={() => setFailed(true)} style={crop ? { position: 'absolute', maxWidth: 'none', width: `${crop.sourceWidth / crop.width * 100}%`, left: `${-crop.x / crop.width * 100}%`, top: 0, transform: `translateY(${-crop.y / crop.sourceHeight * 100}%)` } : undefined} /></div>;
}
function ProductDetails({ product, preview }) {
  const [imageIndex, setImageIndex] = useState(0);
  const rows = [
    ['Material', product.material_type || 'To be confirmed during quotation'],
    ['Dimensions', 'Confirmed against your drawings'],
    ['Tolerance', 'To be confirmed during quotation'],
    ['Surface finish', 'To be confirmed during quotation'],
    ['Pattern weight', 'Depends on the agreed design'],
    ['Price and lead time', 'Provided in the official quotation'],
  ];
  const specifications = Array.isArray(product.specifications) ? product.specifications : [];
  const displayRows = rows.map(([label, fallback]) => [label, specifications.find(row => row.label?.toLowerCase() === label.toLowerCase())?.value || fallback]);
  const additionalRows = specifications.filter(row => !rows.some(([label]) => label.toLowerCase() === row.label?.toLowerCase()));
  const allRows = [...displayRows, ...additionalRows.map(row => [row.label, row.value])];
  return <>
    <div className="public-detail-overview">
      <div><ProductImage image={product.images?.[imageIndex]} name={product.name}/>
        {product.images?.length > 1 && <div className="product-thumbnails">{product.images.map((image, index) => <button key={image.id || index} aria-label={`View product image ${index + 1}`} aria-pressed={imageIndex === index} onClick={() => setImageIndex(index)}><ProductImage image={image} name={product.name}/></button>)}</div>}
        <p className="public-detail-caption">{product.images?.length ? 'Product image' : 'Product image not provided'}</p>
      </div>
      <section><p className="public-eyebrow">Pattern details</p><h2 id="product-detail-title">{product.name}</h2><p>{product.description || 'Share your drawings and requirements with KPC for product information.'}</p><dl>{allRows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
    </div>
    {typeof product.specifications === 'string' && product.specifications.trim() && <p className="product-specification-text">{product.specifications}</p>}
    <p className="public-detail-description">Tell us about the part, required tolerances, quantity, and casting process. Include technical drawings so the team can review the specification.</p>
    <Link className="public-button public-button-orange public-detail-action" to={preview ? '/login' : `/customer?product=${encodeURIComponent(product.id)}`}>Request for Quotation (RFQ) <span aria-hidden="true">→</span></Link>
    <button type="button" className="public-button public-button-outline public-detail-action" onClick={() => downloadSpecifications(product.name, [['Pattern', product.name], ...allRows, ...(typeof product.specifications === 'string' && product.specifications.trim() ? [['Additional specifications', product.specifications]] : [])])}>Download PDF Specifications <span aria-hidden="true">↓</span></button>
    <p className="public-detail-caption">The PDF is a capability summary. Final specifications require confirmation in your quotation.</p>
  </>;
}

export function CataloguePage() {
  const { productId } = useParams();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const suffix = preview ? '?preview=1' : '';
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState('loading');
  const requestRef = useRef(null);
  const loadProducts = useCallback(async (options = {}) => {
    if (requestRef.current) return;
    const controller = new AbortController();
    requestRef.current = controller;
    const quiet = options.quiet === true;
    if (!quiet) setStatus('loading');
    try {
      if (preview) { setProducts(demoProducts); setStatus('ready'); return; }
      const response = await fetch(`${API}/products`, { signal: controller.signal });
      if (!response.ok) throw new Error('Unable to load products.');
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error('Invalid product response.');
      if (!controller.signal.aborted) { setProducts(data); setStatus('ready'); }
    } catch (err) {
      if (!controller.signal.aborted && !quiet) setStatus('error');
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }, [preview]);
  const { isLiveSynced } = useKpcLiveSync(() => loadProducts({ quiet: true }), 4000);
  const [search, setSearch] = useState('');
  const [categories, setCategories] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [sort, setSort] = useState('name');
  const [page, setPage] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const dialogRef = useRef(null);
  useEffect(() => {
    if (!selectedProduct) return;
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.showModal();
    return () => {
      if (dialog.open) dialog.close();
      document.body.style.overflow = previousOverflow;
    };
  }, [selectedProduct]);
  useEffect(() => {
    loadProducts();
    return () => { requestRef.current?.abort(); requestRef.current = null; };
  }, [loadProducts]);
  useEffect(() => { if (productId) window.scrollTo(0, 0); }, [productId]);
  const reset = () => { setSearch(''); setCategories([]); setMaterials([]); setPage(1); };
  const toggle = (value, values, setter) => { setter(values.includes(value) ? values.filter(v => v !== value) : [...values, value]); setPage(1); };
  const categoryOptions = [...new Set(products.map(p => p.category_name).filter(Boolean))];
  const materialOptions = [...new Set(products.map(p => p.material_type).filter(Boolean))];
  const filtered = products.filter(p => (!search || `${p.name} ${p.description || ''}`.toLowerCase().includes(search.toLowerCase())) && (!categories.length || categories.includes(p.category_name)) && (!materials.length || materials.includes(p.material_type))).sort((a,b) => sort === 'price' ? (a.indicative_price ?? Infinity) - (b.indicative_price ?? Infinity) : a.name.localeCompare(b.name));
  const product = products.find(p => (String(p.id) === productId || p.slug === productId));
  const stateView = status === 'loading' ? <div className="catalogue-state" role="status">Loading patterns…</div> : status === 'error' ? <div className="catalogue-state" role="alert"><h2>Unable to load the catalogue</h2><p>Please try again when the service is available.</p><button className="public-button public-button-outline" onClick={() => loadProducts()}>Try again</button></div> : null;
  return <div className="kpc-public catalogue-page"><PublicHeader />{preview && <div className="catalogue-preview">Design preview — sample products, images, prices, and specifications. <Link to="/products">View live catalogue</Link></div>}
    {!productId && <section className="catalogue-banner"><h1>Industrial Pattern Catalogue</h1><p>Browse our range of wooden and metallic patterns.</p><div><Link to="/">Home</Link><span>›</span>Products</div></section>}
    <main className="public-container catalogue-main">{stateView || (productId ? product ? <>
      <nav className="catalogue-breadcrumb" aria-label="Breadcrumb"><Link to="/">Home</Link><span>›</span><Link to={`/products${suffix}`}>Products</Link><span>›</span><span>{product.name}</span></nav>
      <ProductDetails product={product} preview={preview} />
    </> : <div className="catalogue-state"><h1>Product unavailable</h1><p>This product may be inactive or no longer available.</p><Link to={`/products${suffix}`}>Back to catalogue</Link></div> : <div className="catalogue-layout"><aside className="catalogue-filters"><h2>Filter By</h2>{[['Category',categoryOptions,categories,setCategories],['Material',materialOptions,materials,setMaterials]].map(([label, options, selected, setter]) => <fieldset key={label}><legend>{label}</legend>{options.length ? options.map(value => <label key={value}><input type="checkbox" checked={selected.includes(value)} onChange={() => toggle(value,selected,setter)}/>{value} <span>({products.filter(p => (label === 'Category' ? p.category_name : p.material_type) === value).length})</span></label>) : <p className="catalogue-muted">No {label.toLowerCase()} data yet.</p>}</fieldset>)}<button className="public-button public-button-outline" onClick={reset}>↻ Clear Filters</button></aside><section><div className="catalogue-toolbar"><input aria-label="Search patterns" placeholder="Search patterns…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}/><label>Sort by: <select value={sort} onChange={e => { setSort(e.target.value); setPage(1); }}><option value="name">Name</option><option value="price">Price: low to high</option></select></label></div><p className="catalogue-count" role="status">{filtered.length ? `Showing ${(page-1)*6+1}–${Math.min(page*6,filtered.length)} of ${filtered.length} patterns` : '0 patterns'}</p>{!filtered.length ? <div className="catalogue-state"><h2>{products.length ? 'No matching patterns' : 'No products available yet'}</h2><p>{products.length ? 'Try another search or clear the filters.' : 'Please check back for catalogue updates.'}</p>{products.length > 0 && <button className="public-button public-button-outline" onClick={reset}>Clear filters</button>}</div> : <><div className="catalogue-grid">{filtered.slice((page-1)*6,page*6).map(p => <article className="catalogue-card" key={p.id}><button type="button" className="catalogue-image-button" aria-label={`View ${p.name}`} onClick={() => setSelectedProduct(p)}><ProductImage image={p.images?.[0]} name={p.name}/></button><h2><button type="button" className="catalogue-detail-link" onClick={() => setSelectedProduct(p)}>{p.name}</button></h2>{p.material_type && <span className="material-label">Material: {p.material_type}</span>}<p>{p.description || 'Share your drawings and requirements for a tailored quotation.'}</p><strong>{productPrice(p.indicative_price)}</strong><small>Indicative price</small><div className="catalogue-card-actions"><button type="button" className="catalogue-detail-link" onClick={() => setSelectedProduct(p)}>View Details</button><Link className="public-button public-button-orange" to={preview ? '/login' : `/customer?product=${p.id}`}>Request Quote</Link></div></article>)}</div>{filtered.length > 6 && <nav className="catalogue-pagination" aria-label="Catalogue pages">{Array.from({length:Math.ceil(filtered.length/6)},(_,i) => <button key={i} aria-current={page===i+1 ? 'page' : undefined} onClick={() => setPage(i+1)}>{i+1}</button>)}</nav>}</>}</section></div>)}</main>
    <dialog ref={dialogRef} className="public-pattern-dialog public-expanded-details catalogue-detail-dialog" aria-labelledby="product-detail-title" onClose={() => setSelectedProduct(null)} onClick={event => {
      if (event.target !== event.currentTarget) return;
      const rect = event.currentTarget.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.currentTarget.close();
    }}>
      <button type="button" className="public-dialog-close catalogue-dialog-close" aria-label="Close product details" autoFocus onClick={() => dialogRef.current.close()}><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="m5 5 14 14M5 19 19 5"/></svg></button>
      {selectedProduct && <ProductDetails key={selectedProduct.id} product={selectedProduct} preview={preview} />}
    </dialog>
    <LiveSyncBadge visible={isLiveSynced} />
  </div>;
}
