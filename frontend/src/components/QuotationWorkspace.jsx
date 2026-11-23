import { ProtectedDownload } from './ProtectedFiles';
import React, { useEffect, useRef, useState } from 'react';
import './QuotationWorkspace.css';
import { emitKpcSync } from '../utils/kpcLiveSync.jsx';

const API = import.meta.env.VITE_API_BASE_URL || '/api';
const money = value => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value));
const date = value => value ? new Date(value).toLocaleString('en-IN') : 'No expiry';
const blank = { items: [], tax_percent: '0', lead_time_days: '', valid_until: '', notes: '' };
function editValues(quote) {
  return quote ? { items: quote.items.map(({ description, quantity, unit_price }) => ({ description, quantity, unit_price })), tax_percent: quote.tax_percent,
    lead_time_days: quote.lead_time_days ?? '', valid_until: quote.valid_until ? localDate(quote.valid_until) : '', notes: quote.notes } : blank;
}
function localDate(value) {
  const d = new Date(value);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}
function payload(form) {
  return { ...form, lead_time_days: form.lead_time_days === '' ? null : Number(form.lead_time_days),
    valid_until: form.valid_until ? new Date(form.valid_until).toISOString() : null,
    items: form.items.map(item => ({ ...item, quantity: Number(item.quantity) })) };
}

export function QuotationWorkspace({ rfq, admin = false, csrfToken, onBack, onIssued, onAccepted }) {
  const [quotes, setQuotes] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState(blank);
  const [dirty, setDirty] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [acceptedOrder, setAcceptedOrder] = useState(null);
  const [decision, setDecision] = useState('');
  const [message, setMessage] = useState('');
  const heading = useRef(null);
  const quote = quotes.find(q => q.id === selectedId);
  const latest = quotes[0];
  const editable = admin && quote?.is_latest && quote.status === 'draft';
  const prefix = admin ? '/admin' : '';

  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, { credentials: 'include', ...options,
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken, ...options.headers } });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || 'Check the quotation fields and try again.');
    return data;
  }
  async function load(id, { keepError = false } = {}) {
    setLoading(true); if (!keepError) setError('');
    try {
      const records = await request(`${prefix}/rfqs/${rfq.id}/quotations`);
      setQuotes(records); setLoaded(true);
      const selected = records.find(q => q.id === id) || records[0];
      setSelectedId(selected?.id ?? null); setForm(editValues(selected)); setDirty(false);
      return true;
    } catch (err) { setError(err.message); return false; }
    finally { setLoading(false); }
  }
  function reload() {
    if (dirty && !window.confirm('Discard your unsaved draft edits and load the latest saved version?')) return;
    load(selectedId);
  }
  useEffect(() => { load(); heading.current?.focus(); }, [rfq.id]);
  function change(values) { setForm(current => ({ ...current, ...values })); setDirty(true); setSuccess(''); }
  function changeItem(index, values) { change({ items: form.items.map((item, i) => i === index ? { ...item, ...values } : item) }); }
  async function mutate(path, body, method = 'POST', notice = 'Quotation saved.') {
    setBusy(true); setError(''); setSuccess('');
    let saved;
    try {
      saved = await request(path, { method, body: JSON.stringify(body) });
    } catch (err) { setError(err.message); setBusy(false); return; }
    setDecision(''); setMessage('');
    if (saved.status === 'sent' || saved.status === 'rejected') onIssued?.();
    emitKpcSync(saved.status === 'sent' ? 'QUOTATION_SENT' : 'QUOTATION_UPDATED', { rfq_id: rfq.id, id: saved.id });
    const refreshed = await load(saved.id);
    if (refreshed) setSuccess(notice);
    else setError('Your change was saved, but the latest quotation could not be loaded. Use Reload to see the saved version.');
    setBusy(false);
  }
  async function accept() {
    setBusy(true); setError(''); setSuccess('');
    try {
      const result = await request(`/quotations/${quote.id}/accept`, { method: 'POST' });
      setAcceptedOrder(result); await load(quote.id);
      setSuccess('Quotation accepted. Your order and invoice are ready, awaiting payment.');
      emitKpcSync('QUOTATION_DECIDED', { quote_id: quote.id, order_id: result.order_id });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  function selectVersion(id) {
    const selected = quotes.find(q => q.id === Number(id));
    setSelectedId(selected.id); setForm(editValues(selected)); setDirty(false); setDecision(''); setError(''); setSuccess('');
  }

  const requestDetails = admin && <section className="card quotation-request"><h3>Customer’s submitted requirement</h3><p className="quotation-caption">Source: {rfq.rfq_number}. Quotation pricing below stays linked to this request.</p><dl className="quotation-request-details">{[
      ['Pattern', rfq.title], ['Material', rfq.material], ['Requested quantity', `${rfq.quantity} pcs`],
      ['Dimensions', rfq.dimensions || 'Not specified'], ['Specifications', rfq.specifications || 'Not specified'],
      ['Target delivery', rfq.target_delivery_date || 'Not specified'], ['Description', rfq.description || 'Not provided'], ['Customer notes', rfq.notes || 'Not provided'],
    ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><h3>Submitted drawings</h3>{rfq.files?.length ? rfq.files.map(file => <ProtectedDownload className="quotation-file" key={file.id} href={`${API}/rfqs/${rfq.id}/files/${file.id}?disposition=attachment`}>{file.file_name} ↓</ProtectedDownload>) : <p className="quotation-caption">No drawings attached.</p>}</section>;

  return <section className="quotation-workspace" aria-busy={loading || busy}>
    <div className="quotation-toolbar"><button className="btn btn-outline-primary" onClick={onBack} disabled={busy}>← Back to RFQs</button><button className="btn btn-outline-primary" onClick={reload} disabled={busy || loading}>Refresh</button></div>
    <div className="quotation-heading"><div><h2 ref={heading} tabIndex={-1}>{admin ? 'Prepare quotation' : 'Quotation review & decision'}</h2><p>{rfq.rfq_number} · {rfq.title}</p></div>{quote && <span className={`quotation-status status-${quote.status}`}>{quote.status.replaceAll('_', ' ')} · v{quote.version}</span>}</div>
    {error && <div className="alert alert-danger" role="alert">{error} <button type="button" className="btn btn-sm btn-outline-danger" onClick={reload} disabled={busy || loading}>{dirty ? 'Discard edits & reload' : 'Reload'}</button></div>}
    {success && <div className="alert alert-success" role="status">{success}</div>}
    {!quote && requestDetails}
    {loading ? <div className="card p-4" role="status">Loading quotations…</div> : <>
      {quotes.length > 0 && <div className="quotation-version"><label htmlFor="quote-version">Version history</label><select id="quote-version" className="form-select" value={selectedId ?? ''} onChange={e => selectVersion(e.target.value)} disabled={busy || dirty}>{quotes.map(q => <option key={q.id} value={q.id}>Version {q.version} · {q.status}{q.is_latest ? ' · latest' : ''}</option>)}</select>{dirty && <span>Save your draft before changing versions.</span>}</div>}
      {!loaded ? null : !quote ? <div className="card p-4"><h3>{admin ? 'No quotation yet' : 'No issued quotation yet'}</h3><p>{admin ? 'Prepare an itemized manual offer for this RFQ.' : 'KPC will make your offer available here after reviewing your requirement.'}</p>{admin && <div className="quotation-actions"><button type="button" className="btn btn-primary" disabled={busy || !!error} onClick={() => mutate(`/admin/rfqs/${rfq.id}/quotations`, { expected_version: 0, from_rfq: true }, 'POST', 'Draft created from the submitted RFQ. Enter unit prices and lead time, then save.')}>Create quotation from this RFQ</button><button type="button" className="btn btn-outline-primary" disabled={busy || !!error} onClick={() => mutate(`/admin/rfqs/${rfq.id}/quotations`, { expected_version: 0 }, 'POST', 'Blank draft created for this RFQ.')}>Create blank quotation</button></div>}</div> : <div className="quotation-grid">
        <div className="quotation-main">
          <section className="card quotation-official"><h3>{editable ? 'Manual quotation draft' : 'Final official quote'}</h3><div className="quotation-official-content"><strong>{money(quote.total)}</strong><p>Lead time: {quote.lead_time_days ? `${quote.lead_time_days} days` : 'Not set'}</p><span>Valid until: {date(quote.valid_until)}</span><small>Manual pricing · INR · Includes the sample tax shown below (academic demonstration)</small></div></section>
          <section className="card quotation-items"><h3>Quotation details</h3>
            {editable ? <form id="quotation-draft" onSubmit={e => { e.preventDefault(); mutate(`/admin/quotations/${quote.id}`, { ...payload(form), expected_revision: quote.revision }, 'PUT', 'Draft saved. Review the saved totals before issuing.'); }}>
              <fieldset disabled={busy}>
                {form.items.length === 0 && <div className="quotation-from-request"><p>No line items yet. Start with the customer’s requested pattern and quantity, or add items manually.</p><button type="button" className="btn btn-outline-primary" disabled={rfq.quantity > 100000} onClick={() => change({ items: [{ description: rfq.title, quantity: rfq.quantity, unit_price: '0.00' }] })}>Use submitted requirement</button></div>}
                {form.items.map((item, i) => <div className="quotation-edit-item" key={i}>
                  <label>Description<input className="form-control" aria-label={`Item ${i+1} description`} required maxLength={500} value={item.description} onChange={e => changeItem(i, { description: e.target.value })}/></label>
                  <label>Qty<input className="form-control" aria-label={`Item ${i+1} quantity`} type="number" min="1" max="100000" step="1" required value={item.quantity} onChange={e => changeItem(i, { quantity: e.target.value })}/></label>
                  <label>Unit price (₹)<input className="form-control" aria-label={`Item ${i+1} unit price`} type="number" min="0" max="999999999.99" step="0.01" required value={item.unit_price} onChange={e => changeItem(i, { unit_price: e.target.value })}/></label>
                  <button className="btn btn-outline-danger" type="button" aria-label={`Remove item ${i+1}`} onClick={() => change({ items: form.items.filter((_, n) => n !== i) })}>×</button>
                </div>)}
                <button type="button" className="btn btn-outline-primary" disabled={form.items.length >= 50} onClick={() => change({ items: [...form.items, { description: '', quantity: 1, unit_price: '0.00' }] })}>+ Add line item</button>
                <div className="quotation-fields"><label>Sample tax (%)<input className="form-control" type="number" min="0" max="100" step="0.01" required value={form.tax_percent} onChange={e => change({ tax_percent: e.target.value })}/></label><label>Lead time (days)<input className="form-control" type="number" min="1" max="3650" step="1" value={form.lead_time_days} onChange={e => change({ lead_time_days: e.target.value })}/></label><label>Valid until (optional, local time)<input className="form-control" type="datetime-local" value={form.valid_until} onChange={e => change({ valid_until: e.target.value })}/></label></div>
                <label className="quotation-notes">Commercial notes<textarea className="form-control" rows="3" maxLength={4000} value={form.notes} onChange={e => change({ notes: e.target.value })}/></label>
                <button className="btn btn-outline-primary" type="submit">{busy ? 'Saving…' : 'Save draft'}</button>
              </fieldset>
            </form> : <div className="table-responsive"><table className="table"><thead><tr><th>#</th><th>Description</th><th>Qty</th><th>Unit price</th><th>Amount (₹)</th></tr></thead><tbody>{quote.items.map((item, i) => <tr key={i}><td>{i+1}</td><td>{item.description}</td><td>{item.quantity}</td><td>{money(item.unit_price)}</td><td>{money(item.amount)}</td></tr>)}</tbody></table></div>}
            <dl className="quotation-totals"><div><dt>Subtotal</dt><dd>{money(quote.subtotal)}</dd></div><div><dt>{quote.tax_label || 'Sample tax (academic demonstration)'} ({quote.tax_percent}%)</dt><dd>{money(quote.tax_amount)}</dd></div><div><dt>Grand total</dt><dd>{money(quote.total)}</dd></div></dl><p className="quotation-caption">{dirty ? 'Totals show the last saved draft.' : 'Prices and tax are included in the total shown above.'}</p>
          </section>
          {!editable && quote.notes && <section className="card p-3"><h3>Commercial notes</h3><p className="quotation-message">{quote.notes}</p></section>}
          <div className="quotation-actions">
            {admin ? <>{editable ? <><button className="btn btn-primary" disabled={busy || dirty || !quote.items.length || !quote.lead_time_days || Number(quote.total) <= 0} onClick={() => mutate(`/admin/quotations/${quote.id}/send`, { expected_revision: quote.revision }, 'POST', 'Quotation issued to the customer portal.')}>Issue quotation</button><span>Save and review the draft before issuing.</span></> : latest?.status !== 'accepted' && <button className="btn btn-primary" disabled={busy || !quote.is_latest} onClick={() => mutate(`/admin/rfqs/${rfq.id}/quotations`, { ...payload(editValues(latest)), expected_version: latest.version }, 'POST', 'New draft created. The previous version is now superseded.')}>Create revised draft</button>}</> : <><button className="btn btn-outline-danger" disabled={busy || !quote.can_respond} onClick={() => setDecision('reject')}>Reject quotation</button><button className="btn btn-outline-primary" disabled={busy || !quote.can_respond} onClick={() => setDecision('request_changes')}>Request changes</button><button className="btn btn-primary" disabled={busy || (!quote.can_respond && quote.status !== 'accepted')} onClick={accept}>{quote.status === 'accepted' ? 'Retrieve order & invoice' : 'Accept & place order'}</button></>}
          </div>
          {!admin && <p className="quotation-caption">{quote.can_respond ? 'Accept this offer to create an awaiting-payment order, or reject it or request changes.' : quote.status === 'accepted' ? 'This quotation has been accepted. Retrieve its existing order and invoice below.' : 'This version is no longer available for a decision. KPC may be preparing a revised offer.'}</p>}
          {acceptedOrder && <div className="quotation-actions"><button className="btn btn-primary" onClick={() => onAccepted?.(acceptedOrder)}>View my orders</button><ProtectedDownload className="btn btn-outline-primary" href={`${API}/invoices/${acceptedOrder.invoice_id}/download`}>Download invoice</ProtectedDownload></div>}
          {decision && <form className="card p-3" onSubmit={e => { e.preventDefault(); mutate(`/quotations/${quote.id}/decisions`, { action: decision, message }, 'POST', decision === 'reject' ? 'Quotation rejected. KPC can review your response.' : 'Change request saved for KPC review. Official prices are unchanged.'); }}><h3>{decision === 'reject' ? 'Reject quotation' : 'Request changes'}</h3><label htmlFor="quote-response">{decision === 'reject' ? 'Reason for rejection' : 'What would you like changed?'}</label><textarea id="quote-response" className="form-control mb-3" required maxLength={4000} value={message} onChange={e => setMessage(e.target.value)} disabled={busy}/><div className="d-flex gap-2"><button className="btn btn-primary" disabled={busy || !message.trim()}>Submit response</button><button type="button" className="btn btn-outline-primary" disabled={busy} onClick={() => setDecision('')}>Cancel</button></div></form>}
          {!!quote.decisions.length && <section className="card p-3"><h3>Customer responses</h3>{quote.decisions.map(d => <article className="quotation-response" key={d.id}><strong>{d.action === 'reject' ? 'Rejected' : 'Change requested'}</strong><small>{date(d.created_at)}</small><p className="quotation-message">{d.message}</p></article>)}</section>}
        </div>
        <aside>{requestDetails}<section className="card p-3"><h3>Quotation summary</h3><dl className="quotation-summary">{[['RFQ', rfq.rfq_number], ['Quotation', `QT-${quote.id} · v${quote.version}`], ['Status', quote.status], ['Created', date(quote.created_at)], ['Issued', quote.sent_at ? date(quote.sent_at) : 'Not issued'], ['Valid until', date(quote.valid_until)], ['Pricing source', 'Manual']].map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl><h3>Reference drawings</h3>{rfq.files?.length ? rfq.files.map(file => <ProtectedDownload className="quotation-file" key={file.id} href={`${API}/rfqs/${rfq.id}/files/${file.id}?disposition=attachment`}>{file.file_name} ↓</ProtectedDownload>) : <p>No drawings attached.</p>}</section><section className="card p-3"><h3>Payment terms</h3><p>Full settlement is required before order confirmation.</p><p className="quotation-caption">Your order is confirmed once the outstanding balance is fully paid.</p></section></aside>
      </div>}
    </>}
  </section>;
}
