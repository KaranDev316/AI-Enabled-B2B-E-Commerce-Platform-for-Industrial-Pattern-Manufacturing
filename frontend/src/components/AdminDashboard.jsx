import React, { useEffect, useState } from 'react';
import { CustomerIcon as Icon } from './CustomerLayout';
const API = import.meta.env.VITE_API_BASE_URL || '/api';

export function AdminDashboard({ onNavigate, onOpenRfq, onOpenTicket, search }) {
  const [data, setData] = useState({ rfqs: [], tickets: [], orders: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    async function load() {
      try {
        const responses = await Promise.all(['/admin/rfqs', '/admin/support/tickets', '/orders'].map(path => fetch(`${API}${path}`, { credentials: 'same-origin', signal: controller.signal })));
        if (responses.some(r => !r.ok)) throw new Error('Unable to load the dashboard. Please try again.');
        const [rfqs, tickets, orders] = await Promise.all(responses.map(r => r.json()));
        if (!controller.signal.aborted) setData({ rfqs, tickets, orders });
      } catch (err) { if (!controller.signal.aborted) setError('Unable to load the dashboard. Please try again.'); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }
    load(); return () => controller.abort();
  }, [retry]);
  const pending = data.rfqs.filter(r => ['submitted', 'under_review'].includes(r.status));
  const query = search.trim().toLowerCase();
  const queue = [...pending].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).filter(r => `${r.rfq_number} ${r.title} ${r.customer_company || ''} ${r.customer_email || ''}`.toLowerCase().includes(query));
  const orders = data.orders.filter(o => `${o.order_number} ${o.customer_name} ${o.product_summary}`.toLowerCase().includes(query));
  const tickets = [...data.tickets].filter(t => ['open', 'in_progress'].includes(t.status) && `${t.subject} ${t.ticket_number} ${t.customer_name || ''}`.toLowerCase().includes(query)).sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  const empty = loading ? 'Loading dashboard records…' : error ? 'Records are unavailable.' : query ? 'No matching records.' : 'No pending RFQs. New customer requests will appear here.';
  return <div className="admin-dashboard">
    {error && <div className="alert alert-danger" role="alert">{error} <button className="btn btn-sm btn-outline-danger" onClick={() => setRetry(value => value + 1)}>Try again</button></div>}
    <section className="admin-summary-grid" aria-label="Operations overview">
      <button className="admin-summary-card" onClick={() => onNavigate('rfqs')}><span className="admin-summary-icon"><Icon name="rfqs" size={27}/></span><div><span>Pending RFQs</span><strong>{loading || error ? '—' : pending.length}</strong><small>Requests awaiting a quotation</small></div></button>
      <button className="admin-summary-card" onClick={() => onNavigate('orders')}><span className="admin-summary-icon orange"><Icon name="orders" size={27}/></span><div><span>Active Orders</span><strong>{loading || error ? '—' : data.orders.filter(o => o.status !== 'cancelled').length}</strong><small>Accepted orders awaiting settlement or confirmed</small></div></button>
      <button className="admin-summary-card admin-stock-card" onClick={() => onNavigate('inventory')}><span className="admin-summary-icon red"><Icon name="company" size={27}/></span><div><span>Low Stock Alerts</span><strong>—</strong><small>Stock monitoring is not available yet</small></div></button>
    </section>
    <div className="admin-dashboard-grid">
      <section className="card admin-pending"><div className="customer-section-header"><h2>Pending RFQs</h2><button className="customer-text-link" onClick={() => onNavigate('rfqs')}>View all RFQs ›</button></div><div className="table-responsive"><table className="table mb-0"><thead><tr><th>RFQ ID</th><th>CUSTOMER</th><th>PRODUCT / REQUEST</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{loading || error || !queue.length ? <tr><td colSpan="5" className="admin-table-empty" role={loading ? 'status' : undefined}>{empty}</td></tr> : queue.slice(0, 4).map(rfq => <tr key={rfq.id}><td><strong>{rfq.rfq_number}</strong></td><td>{rfq.customer_company || rfq.customer_email || 'Not provided'}</td><td>{rfq.title}</td><td><span className={`customer-status status-${rfq.status}`}>{rfq.status.replaceAll('_', ' ')}</span></td><td><button className={`btn btn-sm ${rfq.status === 'submitted' ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => onOpenRfq(rfq)}>{rfq.status === 'submitted' ? 'Review' : 'Open'}</button></td></tr>)}</tbody></table></div></section>
      <section className="card admin-attention"><div className="customer-section-header"><h2>Needs Attention</h2><button className="customer-text-link" onClick={() => onNavigate('support')}>View all ›</button></div><div className="admin-attention-list">{loading || error ? <p className="admin-panel-empty">{loading ? 'Loading open tickets…' : 'Support records are unavailable.'}</p> : !tickets.length ? <p className="admin-panel-empty">{query ? 'No matching open tickets.' : 'No open support tickets requiring attention.'}</p> : tickets.slice(0, 3).map(ticket => <button key={ticket.id} className="admin-attention-item" onClick={() => onOpenTicket(ticket.id)}><span className={`admin-summary-icon ${ticket.ticket_type === 'complaint' ? 'red' : 'orange'}`}><Icon name="support" size={20}/></span><span><strong>{ticket.subject}</strong><small>{ticket.ticket_number} · {ticket.status.replaceAll('_', ' ')}</small></span><span aria-hidden="true">›</span></button>)}</div></section>
      <section className="card admin-recent-orders"><div className="customer-section-header"><h2>Recent Orders</h2><button className="customer-text-link" onClick={() => onNavigate('orders')}>View all orders ›</button></div><div className="table-responsive"><table className="table mb-0"><thead><tr><th>ORDER ID</th><th>CUSTOMER</th><th>PRODUCT</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{loading || error || !orders.length ? <tr><td colSpan="5" className="admin-table-empty">{loading ? 'Loading orders…' : error ? 'Order records are unavailable.' : 'No matching orders.'}</td></tr> : orders.slice(0,4).map(order => <tr key={order.id}><td><strong>{order.order_number}</strong></td><td>{order.customer_name}</td><td>{order.product_summary}</td><td>{order.status.replaceAll('_',' ')}</td><td><button className="btn btn-sm btn-outline-primary" onClick={() => onNavigate('orders')}>Open</button></td></tr>)}</tbody></table></div></section>
      <section className="card admin-quick-actions"><div className="customer-section-header"><h2>Quick Actions</h2></div><div className="customer-action-stack"><button className="btn btn-primary" onClick={() => onNavigate('rfqs')}><Icon name="plus" size={17}/> Review RFQs</button><button className="btn btn-outline-primary" onClick={() => onNavigate('catalogue')}><Icon name="orders" size={17}/> Manage Products</button><button className="btn btn-outline-primary" onClick={() => onNavigate('users')}><Icon name="profile" size={17}/> Manage Users</button></div></section>
    </div>
  </div>;
}

export function AdminUnavailable({ title, onSupport }) {
  return <section className="card admin-unavailable"><h2>{title}</h2><p>This part of the workspace is not available yet. Existing RFQ, product, user, and support tools remain available from the sidebar.</p><button className="btn btn-outline-primary" onClick={onSupport}>View support tickets</button></section>;
}
