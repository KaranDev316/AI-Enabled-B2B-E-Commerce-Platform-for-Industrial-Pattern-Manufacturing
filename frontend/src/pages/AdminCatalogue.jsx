import { ProtectedPreview } from '../components/ProtectedFiles';
import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { emitKpcSync } from '../utils/kpcLiveSync.jsx';

const API = import.meta.env.VITE_API_BASE_URL || '/api';
const blankProduct = () => ({ name: '', slug: '', category_id: '', material_type: '', description: '', specifications: '', indicative_price: '', is_active: true });
function productForm(p) { return Object.fromEntries(Object.keys(blankProduct()).map(k => [k, p[k] ?? ''])); }
function productBody(form) { return { ...form, category_id: form.category_id === '' ? null : Number(form.category_id), indicative_price: form.indicative_price === '' ? null : form.indicative_price }; }
function slugify(name) { return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 255); }

export function AdminCatalogue() {
  const { csrfToken } = useAuth();
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState({});
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(blankProduct);
  const [categoryId, setCategoryId] = useState(null);
  const [categoryForm, setCategoryForm] = useState({ name: '', description: '' });
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const fileInput = useRef(null);
  const editor = useRef(null);

  async function request(path, options = {}) {
    const response = await fetch(`${API}/admin/catalogue${path}`, {
      ...options, credentials: 'same-origin',
      headers: { ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...(options.method && options.method !== 'GET' ? { 'X-CSRF-Token': csrfToken } : {}), ...options.headers },
    });
    if (!response.ok) {
      let message = `Request failed (${response.status}).`;
      try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map(e => `${e.loc?.slice(1).join('.')}: ${e.msg}`).join('; ') : data.detail?.message || message; } catch {}
      throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
  }
  async function load() {
    setLoading(true);
    try {
      const [p, c] = await Promise.all([request('/products'), request('/categories')]);
      setProducts(p); setCategories(c);
    } catch (e) { setNotice({ error: e.message }); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  useEffect(() => {
    const next = files.map(f => ({ name: f.name, url: URL.createObjectURL(f) }));
    setPreviews(next);
    return () => next.forEach(p => URL.revokeObjectURL(p.url));
  }, [files]);
  function selectProduct(p) {
    setEditing(p?.id ?? 'new'); setForm(p ? productForm(p) : blankProduct()); setFiles([]); setNotice({});
    if (fileInput.current) fileInput.current.value = '';
    setTimeout(() => editor.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  }
  function change(e) {
    const { name, value, type, checked } = e.target;
    setForm(previous => ({ ...previous, [name]: type === 'checkbox' ? checked : value,
      ...(name === 'name' && editing === 'new' && (!previous.slug || previous.slug === slugify(previous.name)) ? { slug: slugify(value) } : {}) }));
  }
  async function saveProduct(e) {
    e.preventDefault(); setBusy(true); setNotice({});
    try {
      const saved = await request(editing === 'new' ? '/products' : `/products/${editing}`, { method: editing === 'new' ? 'POST' : 'PUT', body: JSON.stringify(productBody(form)) });
      setEditing(saved.id); setForm(productForm(saved)); await load();
      setNotice({ success: 'Product details saved. Upload images separately below.' });
      emitKpcSync('CATALOGUE_UPDATED', { id: saved.id });
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  async function toggleProduct(p) {
    if (p.is_active && !window.confirm(`Deactivate “${p.name}”? It will leave the public catalogue. Existing RFQ references will remain.`)) return;
    setBusy(true); setNotice({});
    try {
      const updated = await request(`/products/${p.id}`, { method: 'PUT', body: JSON.stringify(productBody({ ...productForm(p), is_active: !p.is_active })) });
      if (editing === p.id) setForm(productForm(updated));
      await load(); setNotice({ success: updated.is_active ? 'Product activated.' : 'Product deactivated. Historical references were retained.' });
      emitKpcSync('CATALOGUE_UPDATED', { id: p.id, is_active: updated.is_active });
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  async function saveCategory(e) {
    e.preventDefault(); setBusy(true); setNotice({});
    try {
      await request(categoryId ? `/categories/${categoryId}` : '/categories', { method: categoryId ? 'PUT' : 'POST', body: JSON.stringify(categoryForm) });
      setCategoryId(null); setCategoryForm({ name: '', description: '' }); await load(); setNotice({ success: 'Category saved.' });
      emitKpcSync('CATALOGUE_UPDATED');
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  function chooseFiles(e) {
    const selected = [...e.target.files];
    if (selected.length > 2 || selected.some(f => !/\.(jpe?g|png)$/i.test(f.name) || !['image/jpeg', 'image/png'].includes(f.type) || f.size === 0 || f.size > 20 * 1024 * 1024)) {
      setNotice({ error: 'Choose up to two non-empty JPG/PNG files, no larger than 20 MB each.' }); setFiles([]); e.target.value = ''; return;
    }
    setFiles(selected); setNotice({});
  }
  async function upload() {
    if (!files.length) return;
    const body = new FormData(); files.forEach(f => body.append('files', f)); setBusy(true); setNotice({});
    try {
      await request(`/products/${editing}/images`, { method: 'POST', body });
      setFiles([]); if (fileInput.current) fileInput.current.value = '';
      await load(); setNotice({ success: 'Images saved to this product.' });
      emitKpcSync('CATALOGUE_UPDATED', { id: editing });
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  async function removeImage(image) {
    if (!window.confirm('Remove this image from the product?')) return;
    setBusy(true); setNotice({});
    try {
      await request(`/products/${editing}/images/${image.id}`, { method: 'DELETE' }); await load(); setNotice({ success: 'Image removed.' });
      emitKpcSync('CATALOGUE_UPDATED', { id: editing });
    }
    catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  const current = products.find(p => p.id === editing);
  const filtered = products.filter(p => `${p.name} ${p.material_type || ''} ${p.category_name || ''}`.toLowerCase().includes(query.toLowerCase()) && (status === 'all' || p.is_active === (status === 'active')));
  return <section aria-label="Catalogue management">
    <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4"><div><h2 className="h4 mb-1">Products & categories</h2><p className="text-secondary mb-0">Maintain the public catalogue. All prices are indicative.</p></div><div className="d-flex gap-2"><Link to="/catalogue" className="btn btn-outline-primary">View public catalogue ↗</Link><button className="btn btn-primary" disabled={busy} onClick={() => selectProduct(null)}>+ Add product</button></div></div>
    <div aria-live="polite">{notice.error && <div role="alert" className="alert alert-danger">{notice.error}</div>}{notice.success && <div role="status" className="alert alert-success">{notice.success}</div>}</div>
    <div className="row g-4"><div className="col-xl-8"><div className="card p-4 shadow-sm border-0">
      <div className="row g-3 mb-3"><div className="col-md-8"><label htmlFor="admin-product-search" className="form-label">Search products</label><input id="admin-product-search" className="form-control" value={query} onChange={e => setQuery(e.target.value)} /></div><div className="col-md-4"><label htmlFor="product-status" className="form-label">Visibility</label><select id="product-status" className="form-select" value={status} onChange={e => setStatus(e.target.value)}><option value="all">All products</option><option value="active">Active</option><option value="inactive">Inactive</option></select></div></div>
      {loading ? <p role="status">Loading catalogue…</p> : <><p>{filtered.length} products</p><div className="table-responsive"><table className="table align-middle"><thead><tr><th>Product</th><th>Category</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filtered.map(p => <tr key={p.id}><td><strong>{p.name}</strong><div className="small text-secondary">{p.material_type || 'Material on request'}</div></td><td>{p.category_name || 'Uncategorised'}</td><td><span className={`badge ${p.is_active ? 'bg-success' : 'bg-secondary'}`}>{p.is_active ? 'Active' : 'Inactive'}</span></td><td><div className="d-flex gap-2 flex-wrap"><button className="btn btn-sm btn-outline-primary" disabled={busy} onClick={() => selectProduct(p)}>Edit</button><button className="btn btn-sm btn-outline-secondary" disabled={busy} onClick={() => toggleProduct(p)}>{p.is_active ? 'Deactivate' : 'Activate'}</button></div></td></tr>)}</tbody></table>{!filtered.length && <p>No matching products. Add a product or change the filters.</p>}</div></>}
      <button className="btn btn-sm btn-outline-secondary align-self-start" disabled={busy || loading} onClick={load}>Refresh records</button>
    </div></div><aside className="col-xl-4"><div className="card p-4 shadow-sm border-0"><h3 className="h5">Categories</h3><form onSubmit={saveCategory}><fieldset disabled={busy}><label htmlFor="category-name" className="form-label">Category name</label><input id="category-name" className="form-control mb-3" required maxLength={100} value={categoryForm.name} onChange={e => setCategoryForm({ ...categoryForm, name: e.target.value })}/><label htmlFor="category-description" className="form-label">Description</label><textarea id="category-description" className="form-control mb-3" maxLength={5000} value={categoryForm.description} onChange={e => setCategoryForm({ ...categoryForm, description: e.target.value })}/><button className="btn btn-primary" type="submit">{categoryId ? 'Save category' : 'Add category'}</button>{categoryId && <button type="button" className="btn btn-link" onClick={() => { setCategoryId(null); setCategoryForm({ name: '', description: '' }); }}>Cancel</button>}</fieldset></form><ul className="list-group list-group-flush mt-3">{categories.map(c => <li className="list-group-item d-flex justify-content-between align-items-center gap-2" key={c.id}><span>{c.name}</span><button className="btn btn-sm btn-outline-secondary" disabled={busy} onClick={() => { setCategoryId(c.id); setCategoryForm({ name: c.name, description: c.description || '' }); }}>Edit</button></li>)}</ul></div></aside></div>
    {editing !== null && <div className="card p-4 mt-4 shadow-sm border-0" ref={editor}><h3 className="h4">{editing === 'new' ? 'New product' : 'Edit product'}</h3><form onSubmit={saveProduct}><fieldset disabled={busy}><div className="row g-3">
      {[['name', 'Product name', 255], ['slug', 'URL slug (lowercase words separated by hyphens)', 255], ['material_type', 'Material', 100]].map(([key, label, limit]) => <div className="col-md-6" key={key}><label className="form-label" htmlFor={`product-${key}`}>{label}</label><input id={`product-${key}`} name={key} value={form[key]} onChange={change} className="form-control" required={key !== 'material_type'} maxLength={limit} minLength={key === 'material_type' ? undefined : 2} pattern={key === 'slug' ? '[a-z0-9]+(-[a-z0-9]+)*' : undefined}/></div>)}
      <div className="col-md-6"><label className="form-label" htmlFor="product-category">Category</label><select id="product-category" name="category_id" value={form.category_id} onChange={change} className="form-select"><option value="">Uncategorised</option>{categories.map(c => <option value={c.id} key={c.id}>{c.name}</option>)}</select></div>
      <div className="col-md-6"><label htmlFor="product-price" className="form-label">Indicative price (₹; leave blank for on request)</label><input id="product-price" name="indicative_price" type="number" min="0" max="9999999999.99" step="0.01" className="form-control" value={form.indicative_price} onChange={change}/></div>
      <div className="col-md-6 d-flex align-items-end"><div className="form-check mb-2"><input id="product-active" className="form-check-input" type="checkbox" name="is_active" checked={form.is_active} onChange={change}/><label className="form-check-label" htmlFor="product-active">Active in public catalogue</label></div></div>
      {['description','specifications'].map(key => <div className="col-md-6" key={key}><label className="form-label text-capitalize" htmlFor={`product-${key}`}>{key}</label><textarea id={`product-${key}`} name={key} className="form-control" rows={4} maxLength={10000} value={form[key]} onChange={change}/></div>)}
    </div><div className="d-flex gap-2 mt-4"><button type="submit" className="btn btn-primary">{busy ? 'Saving…' : 'Save product details'}</button><button type="button" className="btn btn-outline-secondary" onClick={() => { setEditing(null); setFiles([]); }}>Close editor</button></div></fieldset></form>
    {editing !== 'new' && <section className="border-top mt-4 pt-4"><h4 className="h5">Product images</h4><p className="small text-secondary">JPG/PNG only · 20 MB per image · up to two files per submission. Private Supabase Storage must be configured. Existing images stay until explicitly removed.</p><div className="d-flex gap-3 flex-wrap mb-3">{current?.images?.map(image => <div key={image.id} className="border rounded p-2" style={{width:180}}><ProtectedPreview href={`${API}/admin/catalogue/products/${editing}/images/${image.id}`} fileName={image.file_name} className="w-100" style={{height:120,objectFit:'contain'}}/><button className="btn btn-sm btn-outline-danger mt-2" disabled={busy} onClick={() => removeImage(image)}>Remove image</button></div>)}</div><label htmlFor="product-images" className="form-label">Choose product photos</label><input ref={fileInput} id="product-images" className="form-control" type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" multiple disabled={busy} onChange={chooseFiles}/><div className="d-flex flex-wrap gap-3 mt-3">{previews.map((p,i) => <figure key={i} style={{width:160}}><img src={p.url} alt={`Selected preview: ${p.name}`} style={{width:'100%',height:100,objectFit:'contain'}}/><figcaption className="small text-break">{p.name}</figcaption></figure>)}</div><button className="btn btn-primary mt-3" disabled={busy || !files.length} onClick={upload}>{busy ? 'Please wait…' : 'Upload selected images'}</button></section>}
    </div>}
  </section>;
}
