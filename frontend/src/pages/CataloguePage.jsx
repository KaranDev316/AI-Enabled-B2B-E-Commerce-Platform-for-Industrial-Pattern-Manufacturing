import React, { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { PublicHeader } from '../components/PublicHeader';
import { demoProducts, productPrice } from '../data/catalogue';
import './LandingPage.css';
import './CataloguePage.css';
const API = import.meta.env.VITE_API_BASE_URL || '/api';

export function ProductImage({ image, name }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [image]);
  if (!image || failed) return <div className="catalogue-image catalogue-image-empty">Image coming soon</div>;
  const crop = image.crop;
  return <div className="catalogue-image" role="img" aria-label={image.alt || name}><img src={image.src} alt="" onError={() => setFailed(true)} style={crop ? { position: 'absolute', maxWidth: 'none', width: `${crop.sourceWidth / crop.width * 100}%`, left: `${-crop.x / crop.width * 100}%`, top: 0, transform: `translateY(${-crop.y / crop.sourceHeight * 100}%)` } : undefined} /></div>;
}
export function CataloguePage() {
  const { productId } = useParams();
  const [params] = useSearchParams();
  const preview = params.get('preview') === '1';
  const suffix = preview ? '?preview=1' : '';
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState('loading');
  const [retry, setRetry] = useState(0);
  const [search, setSearch] = useState('');
  const [categories, setCategories] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [sort, setSort] = useState('name');
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState('Description');
  const [imageIndex, setImageIndex] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setStatus('loading');
    if (preview) { setProducts(demoProducts); setStatus('ready'); return () => controller.abort(); }
    fetch(`${API}/products`, { signal: controller.signal }).then(r => { if (!r.ok) throw Error(); return r.json(); }).then(data => { if (!Array.isArray(data)) throw Error(); setProducts(data); setStatus('ready'); }).catch(e => { if (e.name !== 'AbortError') setStatus('error'); });
    return () => controller.abort();
  }, [preview, retry]);
  useEffect(() => { setImageIndex(0); setTab('Description'); window.scrollTo(0, 0); }, [productId]);
  const reset = () => { setSearch(''); setCategories([]); setMaterials([]); setPage(1); };
  const toggle = (value, values, setter) => { setter(values.includes(value) ? values.filter(v => v !== value) : [...values, value]); setPage(1); };
  const categoryOptions = [...new Set(products.map(p => p.category_name).filter(Boolean))];
  const materialOptions = [...new Set(products.map(p => p.material_type).filter(Boolean))];
  const filtered = products.filter(p => (!search || `${p.name} ${p.description || ''}`.toLowerCase().includes(search.toLowerCase())) && (!categories.length || categories.includes(p.category_name)) && (!materials.length || materials.includes(p.material_type))).sort((a,b) => sort === 'price' ? (a.indicative_price ?? Infinity) - (b.indicative_price ?? Infinity) : a.name.localeCompare(b.name));
  const product = products.find(p => String(p.id) === productId);
  const rfqLink = product ? `/customer?product=${encodeURIComponent(product.id)}` : '/customer';
  const stateView = status === 'loading' ? <div className="catalogue-state" role="status">Loading patterns…</div> : status === 'error' ? <div className="catalogue-state" role="alert"><h2>Unable to load the catalogue</h2><p>Please try again when the service is available.</p><button className="public-button public-button-outline" onClick={() => setRetry(retry+1)}>Try again</button></div> : null;
  return <div className="kpc-public catalogue-page"><PublicHeader />{preview && <div className="catalogue-preview">Design preview — sample products, images, prices, and specifications. <Link to="/products">View live catalogue</Link></div>}
    {!productId && <section className="catalogue-banner"><h1>Industrial Pattern Catalogue</h1><p>Browse our range of wooden and metallic patterns.</p><div><Link to="/">Home</Link><span>›</span>Products</div></section>}
    <main className="public-container catalogue-main">{stateView || (productId ? product ? <>
      <nav className="catalogue-breadcrumb" aria-label="Breadcrumb"><Link to="/">Home</Link><span>›</span><Link to={`/products${suffix}`}>Products</Link><span>›</span><span>{product.name}</span></nav>
      <div className="product-overview"><section><ProductImage image={product.images?.[imageIndex]} name={product.name} />{product.images?.length > 1 && <div className="product-thumbnails">{product.images.map((img,i) => <button key={i} aria-label={`View product image ${i+1}`} aria-pressed={imageIndex===i} onClick={() => setImageIndex(i)}><ProductImage image={img} name={product.name} /></button>)}</div>}</section><section className="product-summary"><h1>{product.name}</h1>{product.material_type && <span className="material-label">Material: {product.material_type}</span>}<p>{product.description || 'Contact KPC with your drawings and requirements for further product information.'}</p><dl>{(product.specifications || []).map(row => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl><strong className="product-price">{productPrice(product.indicative_price)}</strong><small>Indicative pricing. Official price and lead time are confirmed by quotation.</small></section></div>
      <Link className="public-button public-button-orange product-rfq" to={preview ? '/login' : rfqLink}>Request for Quotation (RFQ) <span aria-hidden="true">↗</span></Link>
      <section className="product-information"><div className="product-tabs" role="tablist" aria-label="Product information">{['Description','Specifications','Material & Process','Applications'].map(name => <button key={name} id={`tab-${name.replaceAll(' ','-')}`} role="tab" aria-selected={tab===name} aria-controls="product-panel" onClick={() => setTab(name)}>{name}</button>)}</div><div id="product-panel" role="tabpanel" aria-labelledby={`tab-${tab.replaceAll(' ','-')}`}>{tab === 'Description' ? product.description || 'Detailed description will be available when provided.' : tab === 'Specifications' ? product.specifications?.length ? <dl>{product.specifications.map(row => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl> : 'Specifications will be confirmed with your requirements.' : tab === 'Material & Process' ? product.process || `Material: ${product.material_type || 'On request'}. Manufacturing process is confirmed during quotation.` : product.applications || 'Contact KPC to discuss suitability for your application.'}</div></section>
    </> : <div className="catalogue-state"><h1>Product unavailable</h1><p>This product may be inactive or no longer available.</p><Link to={`/products${suffix}`}>Back to catalogue</Link></div> : <div className="catalogue-layout"><aside className="catalogue-filters"><h2>Filter By</h2>{[['Category',categoryOptions,categories,setCategories],['Material',materialOptions,materials,setMaterials]].map(([label, options, selected, setter]) => <fieldset key={label}><legend>{label}</legend>{options.length ? options.map(value => <label key={value}><input type="checkbox" checked={selected.includes(value)} onChange={() => toggle(value,selected,setter)}/>{value} <span>({products.filter(p => (label === 'Category' ? p.category_name : p.material_type) === value).length})</span></label>) : <p className="catalogue-muted">No {label.toLowerCase()} data yet.</p>}</fieldset>)}<button className="public-button public-button-outline" onClick={reset}>↻ Clear Filters</button></aside><section><div className="catalogue-toolbar"><input aria-label="Search patterns" placeholder="Search patterns…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}/><label>Sort by: <select value={sort} onChange={e => { setSort(e.target.value); setPage(1); }}><option value="name">Name</option><option value="price">Price: low to high</option></select></label></div><p className="catalogue-count" role="status">{filtered.length ? `Showing ${(page-1)*6+1}–${Math.min(page*6,filtered.length)} of ${filtered.length} patterns` : '0 patterns'}</p>{!filtered.length ? <div className="catalogue-state"><h2>{products.length ? 'No matching patterns' : 'No products available yet'}</h2><p>{products.length ? 'Try another search or clear the filters.' : 'Please check back for catalogue updates.'}</p>{products.length > 0 && <button className="public-button public-button-outline" onClick={reset}>Clear filters</button>}</div> : <><div className="catalogue-grid">{filtered.slice((page-1)*6,page*6).map(p => <article className="catalogue-card" key={p.id}><Link to={`/products/${p.id}${suffix}`} aria-label={`View ${p.name}`}><ProductImage image={p.images?.[0]} name={p.name}/></Link><h2><Link to={`/products/${p.id}${suffix}`}>{p.name}</Link></h2>{p.material_type && <span className="material-label">Material: {p.material_type}</span>}<p>{p.description || 'Share your drawings and requirements for a tailored quotation.'}</p><strong>{productPrice(p.indicative_price)}</strong><small>Indicative price</small><div className="catalogue-card-actions"><Link to={`/products/${p.id}${suffix}`}>View Details</Link><Link className="public-button public-button-orange" to={preview ? '/login' : `/customer?product=${p.id}`}>Request Quote</Link></div></article>)}</div>{filtered.length > 6 && <nav className="catalogue-pagination" aria-label="Catalogue pages">{Array.from({length:Math.ceil(filtered.length/6)},(_,i) => <button key={i} aria-current={page===i+1 ? 'page' : undefined} onClick={() => setPage(i+1)}>{i+1}</button>)}</nav>}</>}</section></div>)}</main></div>;
}
