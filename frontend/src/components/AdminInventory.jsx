import { emitKpcSync, useCrossTabSync } from '../utils/crossTabSync';
import React, { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { CustomerIcon as Icon } from './CustomerLayout';
import '../pages/AdminInventory.css';

const API = import.meta.env.VITE_API_BASE_URL || '/api';
const categories = ['Raw Material', 'Consumable', 'Tool'];
const units = ['kg', 'g', 'litre', 'metre', 'piece'];
const labels = { in_stock: 'In Stock', low_stock: 'Low Stock', out_of_stock: 'Out of Stock' };
const blank = () => ({ code: '', name: '', category: 'Raw Material', unit: 'kg', minimum_stock: '', location: '', description: '' });
const adjustmentForm = () => ({ request_id: crypto.randomUUID(), direction: 'addition', amount: '', reason: '' });
const quantity = value => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 3 }).format(Number(value));
const timestamp = value => new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value.endsWith('Z') || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`));

export function AdminInventory() {
  const { csrfToken } = useAuth();
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [notice, setNotice] = useState({});
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState('name');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState(null);
  const [editorId, setEditorId] = useState(null);
  const [form, setForm] = useState(blank);
  const [detailTab, setDetailTab] = useState('details');
  const [adjusting, setAdjusting] = useState(false);
  const [adjustment, setAdjustment] = useState(adjustmentForm);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyVersion, setHistoryVersion] = useState(0);
  const detailPanel = useRef(null);
  const selected = materials.find(m => m.id === selectedId);

  async function request(path, options = {}) {
    const response = await fetch(`${API}/admin/inventory${path}`, { ...options, credentials: 'same-origin', headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.method ? { 'X-CSRF-Token': csrfToken } : {}),
    } });
    if (!response.ok) {
      let message = `Inventory request failed (${response.status}).`;
      try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail) ? body.detail.map(e => `${e.loc?.slice(1).join('.')}: ${e.msg}`).join('; ') : body.detail?.message || message; } catch {}
      throw new Error(message);
    }
    const result = await response.json();
    if (options.method) emitKpcSync('INVENTORY_UPDATED');
    return result;
  }
  useCrossTabSync(async () => {try {setMaterials(await request('/materials'));} catch {}}, 5000);
  async function reload(signal) {
    setLoading(true); setLoadError('');
    try { const data = await request('/materials', { signal }); if (!signal?.aborted) setMaterials(data); }
    catch (e) { if (e.name !== 'AbortError') setLoadError(e.message); }
    finally { if (!signal?.aborted) setLoading(false); }
  }
  useEffect(() => { const c = new AbortController(); reload(c.signal); return () => c.abort(); }, []);
  useEffect(() => {
    if (!selectedId) return;
    const c = new AbortController(); setHistoryLoading(true); setHistoryError(''); setHistory([]);
    request(`/materials/${selectedId}/adjustments`, { signal: c.signal }).then(records => { if (!c.signal.aborted) setHistory(records); }).catch(e => { if (e.name !== 'AbortError') setHistoryError(e.message); }).finally(() => { if (!c.signal.aborted) setHistoryLoading(false); });
    return () => c.abort();
  }, [selectedId, historyVersion]);
  useEffect(() => setPage(1), [query, category, status, sort]);
  function openDetails(material) {
    setSelectedId(material.id); setEditorId(null); setDetailTab('details'); setAdjusting(false); setNotice({});
    detailPanel.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function edit(material) {
    setEditorId(material ? material.id : 'new');
    setForm(material ? Object.fromEntries(Object.keys(blank()).map(k => [k, material[k] ?? ''])) : blank());
    if (material) setSelectedId(material.id);
    setAdjusting(false); setNotice({});
    setTimeout(() => detailPanel.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 0);
  }
  async function saveMaterial(e) {
    e.preventDefault(); setBusy(true); setNotice({});
    try {
      const data = await request(editorId === 'new' ? '/materials' : `/materials/${editorId}`, { method: editorId === 'new' ? 'POST' : 'PUT', body: JSON.stringify({ ...form, minimum_stock: form.minimum_stock || '0' }) });
      setMaterials(previous => [...previous.filter(m => m.id !== data.id), data]); setSelectedId(data.id); setEditorId(null); setDetailTab('details');
      setNotice({ success: 'Material saved. Opening stock is recorded using Update Stock with a reason.' });
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  function startAdjustment() { setAdjusting(true); setAdjustment(adjustmentForm()); setNotice({}); }
  async function saveAdjustment(e) {
    e.preventDefault(); setBusy(true); setNotice({});
    try {
      await request(`/materials/${selectedId}/adjustments`, { method: 'POST', body: JSON.stringify(adjustment) });
      setAdjusting(false); setAdjustment(adjustmentForm()); setHistoryVersion(v => v + 1); await reload();
      setNotice({ success: 'Stock adjustment saved with its reason and history entry.' });
    } catch (e) { setNotice({ error: e.message }); } finally { setBusy(false); }
  }
  const filtered = materials.filter(m => (!category || m.category === category) && (!status || m.stock_status === status) && `${m.code} ${m.name} ${m.category}`.toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === 'quantity' ? Number(a.quantity) - Number(b.quantity) : a[sort].localeCompare(b[sort]));
  const pages = Math.max(1, Math.ceil(filtered.length / 10));
  const currentPage = Math.min(page, pages);
  const rows = filtered.slice((currentPage - 1) * 10, currentPage * 10);
  const counts = { total: materials.length, ...Object.fromEntries(Object.keys(labels).map(s => [s, materials.filter(m => m.stock_status === s).length])) };
  return <section className="inventory-screen" aria-label="Inventory management">
    <div className="inventory-toolbar"><div className="inventory-section-label"><Icon name="orders" size={20}/> Inventory</div><button className="btn btn-primary" disabled={busy} onClick={() => edit(null)}><Icon name="plus" size={16}/> Add Inventory Item</button></div>
    {notice.error && <div className="alert alert-danger" role="alert">{notice.error}</div>}{notice.success && <div className="alert alert-success" role="status">{notice.success}</div>}
    {loadError && <div className="alert alert-danger" role="alert">Inventory could not be loaded: {loadError} <button className="btn btn-sm btn-outline-danger" disabled={busy} onClick={() => reload()}>Retry</button></div>}
    <div className="inventory-grid"><section className="card inventory-list-panel">
      <div className="inventory-summary">{[['total','Total Items','orders'],['in_stock','In Stock','company'],['low_stock','Low Stock','rfqs'],['out_of_stock','Out of Stock','support']].map(([key,label,icon]) => <button type="button" key={key} className={`inventory-stat inventory-stat-${key}`} onClick={() => setStatus(key === 'total' ? '' : key)} disabled={loading || !!loadError || busy} aria-label={`Filter ${label}`}><span><Icon name={icon} size={23}/></span><div><strong>{loading || loadError ? '—' : counts[key]}</strong><small>{label}</small></div></button>)}</div>
      <div className="inventory-filters"><label className="inventory-search"><span className="visually-hidden">Search by item name, code or category</span><Icon name="search" size={17}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search by name, code or category…"/></label><label>Category<select value={category} onChange={e => setCategory(e.target.value)}><option value="">All Categories</option>{categories.map(c => <option key={c}>{c}</option>)}</select></label><label>Stock Status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All Statuses</option>{Object.entries(labels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Sort By<select value={sort} onChange={e => setSort(e.target.value)}><option value="name">Item Name (A–Z)</option><option value="code">Item Code</option><option value="quantity">Quantity (low first)</option></select></label></div>
      <div className="table-responsive"><table className="table inventory-table"><thead><tr><th>Item Code</th><th>Item Name</th><th>Category</th><th>Unit</th><th>In Stock</th><th>Min. Stock</th><th>Status</th><th>Action</th></tr></thead><tbody>{loading || loadError || !rows.length ? <tr><td colSpan={8} className="inventory-empty" role={loading ? 'status' : undefined}>{loading ? 'Loading inventory…' : loadError ? 'Inventory is unavailable. Use Retry above.' : materials.length ? 'No matching materials. Change or clear the filters.' : 'No materials yet. Add an inventory item to get started.'}</td></tr> : rows.map(m => <tr key={m.id} className={m.id === selectedId ? 'inventory-selected' : ''}><td>{m.code}</td><td><button className="inventory-material-name" disabled={busy} onClick={() => openDetails(m)}>{m.name}</button></td><td>{m.category}</td><td>{m.unit}</td><td>{quantity(m.quantity)}</td><td>{quantity(m.minimum_stock)}</td><td><span className={`inventory-badge ${m.stock_status}`}>{labels[m.stock_status]}</span></td><td><button className="inventory-edit-button" aria-label={`Edit ${m.name}`} disabled={busy} onClick={() => edit(m)}>Edit</button></td></tr>)}</tbody></table></div>
      <div className="inventory-pagination"><span>{loading || loadError ? '—' : `Showing ${filtered.length ? (currentPage-1)*10+1 : 0}–${Math.min(currentPage*10,filtered.length)} of ${filtered.length} items`}</span><div><button disabled={currentPage <= 1 || loading} onClick={() => setPage(currentPage-1)} aria-label="Previous inventory page">‹</button><span>{currentPage} / {pages}</span><button disabled={currentPage >= pages || loading} onClick={() => setPage(currentPage+1)} aria-label="Next inventory page">›</button></div></div>
    </section>
    <aside className="card inventory-detail-panel" ref={detailPanel} aria-label="Material details">
      {editorId !== null ? <><div className="inventory-panel-heading"><h2>{editorId === 'new' ? 'Add Inventory Item' : 'Edit Material'}</h2><button aria-label="Close material editor" disabled={busy} onClick={() => setEditorId(null)}>×</button></div><form onSubmit={saveMaterial}><fieldset disabled={busy} className="inventory-form">
        {[['code','Item Code',40],['name','Item Name',150],['location','Location',150]].map(([key,label,max]) => <label key={key}>{label}<input value={form[key]} maxLength={max} minLength={key === 'location' ? undefined : 2} required={key !== 'location'} onChange={e => setForm({...form,[key]:e.target.value})}/></label>)}
        <div className="inventory-form-pair"><label>Category<select value={form.category} onChange={e => setForm({...form,category:e.target.value})}>{categories.map(c => <option key={c}>{c}</option>)}</select></label><label>Unit<select value={form.unit} disabled={editorId !== 'new'} onChange={e => setForm({...form,unit:e.target.value})}>{units.map(u => <option key={u}>{u}</option>)}</select></label></div><label>Minimum Stock<input type="number" min="0" max="99999999999.999" step={form.unit === 'piece' ? '1' : '0.001'} value={form.minimum_stock} onChange={e => setForm({...form,minimum_stock:e.target.value})}/></label><label>Description<textarea rows={3} maxLength={5000} value={form.description} onChange={e => setForm({...form,description:e.target.value})}/></label><p>New materials start at zero. Record opening stock through a reasoned stock addition. Units cannot change after creation.</p><button type="submit" className="btn btn-primary">{busy ? 'Saving…' : 'Save Material'}</button></fieldset></form></> : !selected || loadError ? <div className="inventory-detail-empty"><Icon name="orders" size={35}/><h2>{loadError ? 'Details unavailable' : 'Select a material'}</h2><p>{loadError ? 'Retry loading inventory before using stock information.' : 'Open an item from the table to inspect its balance, update stock or review its movement history.'}</p></div> : <><div className="inventory-panel-heading"><div><h2>{selected.name}</h2><p>{selected.code} · {selected.category}</p><span className={`inventory-badge ${selected.stock_status}`}>{labels[selected.stock_status]}</span></div><button aria-label="Close material details" disabled={busy} onClick={() => setSelectedId(null)}>×</button></div><div className="inventory-detail-tabs" aria-label="Material sections"><button aria-pressed={detailTab === 'details'} className={detailTab === 'details' ? 'active' : ''} onClick={() => setDetailTab('details')}>Details</button><button aria-pressed={detailTab === 'history'} className={detailTab === 'history' ? 'active' : ''} onClick={() => setDetailTab('history')}>Stock Movement</button></div>
      {detailTab === 'details' ? <dl className="inventory-facts">{[['Item Code',selected.code],['Item Name',selected.name],['Category',selected.category],['Unit',selected.unit],['Current Stock',`${quantity(selected.quantity)} ${selected.unit}`],['Minimum Stock',`${quantity(selected.minimum_stock)} ${selected.unit}`],['Location',selected.location || 'Not specified'],['Description',selected.description || 'Not specified']].map(([name,value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl> : <div className="inventory-history">{historyLoading ? <p role="status">Loading stock history…</p> : historyError ? <div role="alert"><p>{historyError}</p><button onClick={() => setHistoryVersion(v => v+1)} className="btn btn-outline-danger">Retry history</button></div> : !history.length ? <p>No movements yet. Record opening stock using Update Stock.</p> : history.map(entry => <article key={entry.id}><div><strong className={entry.direction === 'addition' ? 'inventory-addition' : 'inventory-deduction'}>{entry.direction === 'addition' ? '+' : '−'}{quantity(entry.amount)} {entry.unit}</strong><time>{timestamp(entry.created_at)}</time></div><p>{entry.reason}</p><small>{quantity(entry.quantity_before)} → {quantity(entry.quantity_after)} {entry.unit} · {entry.material_code}</small><small>By {entry.actor_email}</small></article>)}</div>}
      {adjusting ? <form className="inventory-adjustment" onSubmit={saveAdjustment}><fieldset disabled={busy} className="inventory-form"><h3>Update Stock</h3><p>Available: {quantity(selected.quantity)} {selected.unit}. Corrections must be recorded as new movements.</p><label>Direction<select value={adjustment.direction} onChange={e => setAdjustment({...adjustment,direction:e.target.value,request_id:crypto.randomUUID()})}><option value="addition">Add stock</option><option value="deduction">Deduct stock</option></select></label><label>Quantity ({selected.unit})<input type="number" min={selected.unit === 'piece' ? '1' : '0.001'} max="99999999999.999" step={selected.unit === 'piece' ? '1' : '0.001'} required value={adjustment.amount} onChange={e => setAdjustment({...adjustment,amount:e.target.value,request_id:crypto.randomUUID()})}/></label><label>Reason<textarea rows={3} minLength={3} maxLength={1000} required value={adjustment.reason} onChange={e => setAdjustment({...adjustment,reason:e.target.value,request_id:crypto.randomUUID()})} placeholder="Opening stock, production usage or explained correction…"/></label><div className="inventory-actions"><button type="submit" className="btn btn-primary">{busy ? 'Saving…' : 'Save Adjustment'}</button><button type="button" className="btn btn-outline-secondary" onClick={() => setAdjusting(false)}>Cancel</button></div></fieldset></form> : <div className="inventory-actions"><button className="btn btn-outline-primary" disabled={busy || loading || !!loadError} onClick={startAdjustment}>Update Stock</button><button className="btn btn-outline-secondary" disabled={busy} onClick={() => edit(selected)}>Edit Details</button></div>}
      </>}
    </aside></div>
    {(query || category || status) && <button className="customer-text-link mt-3" onClick={() => {setQuery('');setCategory('');setStatus('');}}>Clear filters</button>}
  </section>;
}
