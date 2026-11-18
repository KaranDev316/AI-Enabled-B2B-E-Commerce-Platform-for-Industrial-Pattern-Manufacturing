import React from 'react';
import { Link } from 'react-router-dom';
import { CustomerIcon } from './CustomerLayout';

export function CustomerDashboard({ rfqs, tickets, loading, error, onRetry, onNavigate, onNewRfq, onOpenRfq }) {
  const review = rfqs.filter(r => ['submitted', 'under_review'].includes(r.status)).length;
  const openTickets = tickets.filter(t => ['open', 'in_progress'].includes(t.status)).length;
  const recent = [...rfqs].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

  return <div className="customer-dashboard">
    {error && <div className="alert alert-danger" role="alert">{error} <button className="btn btn-sm btn-outline-danger" onClick={onRetry}>Try again</button></div>}
    <section className="customer-stat-grid" aria-label="Workspace overview">
      {[
        { label: 'My RFQs', value: rfqs.length, note: 'Requirements submitted to KPC', icon: 'rfqs' },
        { label: 'Awaiting review', value: review, note: 'Submitted or under engineering review', icon: 'orders' },
      ].map((stat, index) => <button className={`customer-stat ${index === 0 ? 'customer-stat-featured' : ''}`} key={stat.label} onClick={() => onNavigate('rfqs')}>
        <span className="customer-stat-icon"><CustomerIcon name={stat.icon} size={36}/></span>
        <span className="customer-stat-copy"><span>{stat.label}</span><strong>{loading || error ? '—' : stat.value.toLocaleString()}</strong><small>{stat.note}</small></span>
        <CustomerIcon name="arrow" size={22}/>
      </button>)}
    </section>

    <div className="customer-dashboard-columns">
      <section className="card customer-recent">
        <div className="customer-section-header"><h2><span className="customer-heading-icon"><CustomerIcon name="rfqs"/></span> Recent RFQs</h2><button className="customer-text-link" onClick={() => onNavigate('rfqs')}>View all RFQs <CustomerIcon name="arrow" size={16}/></button></div>
        <div className="table-responsive"><table className="table mb-0"><thead><tr><th>RFQ REFERENCE</th><th>PATTERN</th><th>DATE</th><th>STATUS</th><th><span className="visually-hidden">Details</span></th></tr></thead><tbody>
          {loading || error || !recent.length ? <tr><td colSpan="5"><div className="customer-empty">
            {loading ? <p role="status">Loading your requests…</p> : error ? <p>Your requests could not be loaded.</p> : <><CustomerIcon name="rfqs" size={30}/><h3>No RFQs submitted yet</h3><p>Create a request for a catalogue pattern or your own design.</p><button className="btn btn-outline-primary" onClick={onNewRfq}>Create an RFQ</button></>}
          </div></td></tr> : recent.map(rfq => <tr key={rfq.id}>
            <td><strong>{rfq.rfq_number}</strong></td><td>{rfq.title}</td>
            <td>{new Date(rfq.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</td>
            <td><span className={`customer-status status-${rfq.status}`}>{rfq.status.replaceAll('_', ' ')}</span></td>
            <td><button className="customer-row-open" aria-label={`View ${rfq.rfq_number}`} onClick={() => onOpenRfq(rfq.id)}><CustomerIcon name="arrow" size={18}/></button></td>
          </tr>)}
        </tbody></table></div>
      </section>
      <aside className="customer-quick-actions">
        <section className="card"><div className="customer-section-header"><h2><span className="customer-heading-icon orange"><CustomerIcon name="plus"/></span> Quick actions</h2></div>
          <div className="customer-action-stack"><button className="btn btn-primary" onClick={onNewRfq}><CustomerIcon name="plus"/> New RFQ</button><Link className="btn btn-outline-primary" to="/products"><CustomerIcon name="orders"/> Browse catalogue</Link></div>
        </section>
        <section className="customer-help-card"><h2><CustomerIcon name="support" size={24}/> Support & Complaints</h2><p>{loading || error ? 'View your conversations with the KPC team.' : `${openTickets} open ${openTickets === 1 ? 'ticket' : 'tickets'}. Get help with your requirements or an existing order.`}</p><button className="customer-text-link" onClick={() => onNavigate('support')}>View support tickets <CustomerIcon name="arrow" size={16}/></button></section>
      </aside>
    </div>

    <section className="card customer-request-tracking">
      <div className="customer-section-header"><h2><span className="customer-heading-icon"><CustomerIcon name="orders"/></span> RFQ status</h2><span>Latest requirements</span></div>
      {loading || error || !recent.length ? <div className="customer-tracking-empty"><p>{loading ? 'Loading request status…' : error ? 'Request status is unavailable.' : 'Once you submit an RFQ, you can follow its review status here.'}</p></div> : <div className="customer-tracking-grid">{recent.slice(0, 2).map(rfq => <button className="customer-tracking-card" onClick={() => onOpenRfq(rfq.id)} key={rfq.id}>
        <strong>{rfq.rfq_number}</strong><span>{rfq.title}</span><div className="customer-tracking-stages">{['submitted', 'under_review', 'quoted'].map(status => <span key={status} className={status === rfq.status ? 'is-current' : ''}>{status.replaceAll('_', ' ')}</span>)}</div><small>Current status: {rfq.status.replaceAll('_', ' ')}</small>
      </button>)}</div>}
    </section>
  </div>;
}

export function CustomerUnavailable({ type, onNewRfq, onSupport }) {
  const orders = type === 'orders';
  return <section className="card customer-records-pending">
    <div className="customer-section-header"><h2><span className="customer-heading-icon"><CustomerIcon name={type}/></span>{orders ? 'Order history' : 'Invoices & payment history'}</h2><button className="customer-text-link" onClick={onSupport}>Contact support <CustomerIcon name="arrow" size={16}/></button></div>
    <div className="table-responsive"><table className="table mb-0"><thead><tr>{(orders ? ['ORDER ID', 'PATTERN', 'ORDER DATE', 'STATUS', 'EXPECTED COMPLETION'] : ['INVOICE', 'ORDER', 'ISSUED', 'TOTAL', 'BALANCE', 'STATUS']).map(label => <th key={label}>{label}</th>)}</tr></thead><tbody><tr><td colSpan={orders ? 5 : 6}><div className="customer-empty"><CustomerIcon name={type} size={35}/><h3>{orders ? 'Order tracking is not available yet' : 'Invoice and payment tracking is not available yet'}</h3><p>{orders ? 'You can submit an RFQ now. For updates about an order, contact KPC support.' : 'For invoice copies or billing questions, contact KPC support.'}</p><button className="btn btn-primary" onClick={orders ? onNewRfq : onSupport}>{orders ? 'New RFQ' : 'Contact support'}</button></div></td></tr></tbody></table></div>
  </section>;
}
