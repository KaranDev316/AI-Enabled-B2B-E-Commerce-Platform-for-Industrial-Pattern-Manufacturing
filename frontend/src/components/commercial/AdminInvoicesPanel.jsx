import DemoPaymentForm, { PaymentHistory } from './DemoPaymentForm';
import { ProtectedDownload } from '../ProtectedFiles';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  buildDemoInvoiceDownloadUrl,
  formatCommercialDate,
  formatInr,
  getInvoiceStatusMeta,
} from './commercialUtils';
import './commercial.css';
import { useKpcLiveSync, LiveSyncBadge } from '../../utils/kpcLiveSync.jsx';

/**
 * Admin Invoices & Payments (S08/S09 commercial view).
 * Visual references: docs/ui-ux/admin/invoices-and-payments.webp and docs/ui-ux/global/ui-kit.webp.
 * S09: immutable invoices, simulated settlement and payment history.
 */
export default function AdminInvoicesPanel() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadInvoices = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (search.trim()) params.set('search', search.trim());
      const query = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(`/api/invoices${query}`, { credentials: 'include' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail?.message || 'Unable to load invoices.');
      }
      const data = await res.json();
      const list = Array.isArray(data) ? data : [];
      setInvoices(list);
      if (list.length > 0 && !selectedId) {
        setSelectedId(list[0].id);
      }
    } catch (err) {
      setError(err.message || 'Unable to load invoices.');
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, selectedId]);

  async function refreshDetail() {
    if (!selectedId) return;
    const response = await fetch(`/api/invoices/${selectedId}`);
    if (!response.ok) throw new Error('Unable to refresh invoice details.');
    setDetail(await response.json());
  }
  const { isLiveSynced } = useKpcLiveSync(async () => {
    await loadInvoices();
    try { await refreshDetail(); } catch (err) { setError(err.message); }
  }, 4000);


  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    fetch(`/api/invoices/${selectedId}`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('Unable to load invoice details.'))))
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const kpis = useMemo(() => {
    const active = invoices.filter((inv) => inv.status !== 'cancelled');
    const totalInvoiced = active.reduce((acc, inv) => acc + Number(inv.total_amount || 0), 0);
    const totalPaid = active.reduce((acc, inv) => acc + Number(inv.paid_amount || 0), 0);
    const totalPending = active.reduce((acc, inv) => acc + Number(inv.outstanding_balance || 0), 0);
    const cancelledCount = invoices.filter((inv) => inv.status === 'cancelled').length;
    return { totalInvoiced, totalPaid, totalPending, cancelledCount };
  }, [invoices]);

  return (
    <section className="kpc-commercial-panel" aria-label="Admin Invoices and Payments">


      <div className="kpc-commercial-kpi-grid">
        <div className="kpc-commercial-kpi">
          <span>Total Invoiced (Active)</span>
          <strong>{formatInr(kpis.totalInvoiced)}</strong>
          <small>Excludes cancelled orders</small>
        </div>
        <div className="kpc-commercial-kpi tone-success">
          <span>Paid</span>
          <strong>{formatInr(kpis.totalPaid)}</strong>
          <small>Payments received</small>
        </div>
        <div className="kpc-commercial-kpi tone-warn">
          <span>Pending Balance</span>
          <strong>{formatInr(kpis.totalPending)}</strong>
          <small>Awaiting settlement</small>
        </div>
        <div className="kpc-commercial-kpi tone-danger">
          <span>Cancelled Invoices</span>
          <strong>{kpis.cancelledCount}</strong>
          <small>Zero-payment cancellations</small>
        </div>
      </div>

      <div className="kpc-commercial-split">
        <div className="card">
          <div className="customer-list-toolbar">
            <div className="customer-search">
              <input
                type="search"
                placeholder="Search by invoice no., customer, or order..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search invoices"
              />
            </div>
            <select
              className="form-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter invoices by status"
            >
              <option value="all">All Statuses</option>
              <option value="unpaid">Unpaid</option>
              <option value="partially_paid">Partially Paid</option>
              <option value="paid">Paid</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {loading ? (
            <div className="kpc-commercial-state-box">
              <h3>Loading invoices...</h3>
              <p>Fetching issued invoices.</p>
            </div>
          ) : error ? (
            <div className="kpc-commercial-state-box">
              <h3>Unable to load invoices</h3>
              <p>{error}</p>
              <button type="button" className="btn btn-outline-primary btn-sm" onClick={loadInvoices}>
                Retry
              </button>
            </div>
          ) : invoices.length === 0 ? (
            <div className="kpc-commercial-state-box">
              <h3>No invoices issued yet</h3>
              <p>Invoices are created automatically when customers accept quotations.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>Invoice No.</th>
                    <th>Customer</th>
                    <th>Order No.</th>
                    <th>Issue Date</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => {
                    const meta = getInvoiceStatusMeta(inv.status);
                    const isSelected = inv.id === selectedId;
                    return (
                      <tr
                        key={inv.id}
                        className={isSelected ? 'kpc-commercial-row-selected' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedId(inv.id)}
                      >
                        <td>
                          <strong>{inv.invoice_number}</strong>
                        </td>
                        <td>{inv.customer_name}</td>
                        <td>{inv.order_number}</td>
                        <td>{formatCommercialDate(inv.issued_at)}</td>
                        <td>
                          <strong>{formatInr(inv.total_amount)}</strong>
                        </td>
                        <td>
                          <span className={`badge ${meta.badgeClass}`}>{meta.label}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header d-flex justify-content-between align-items-center">
            <div>
              <h2 className="card-title mb-0">
                {detail ? `Invoice ${detail.invoice_number}` : 'Invoice Snapshot'}
              </h2>
              {detail && <p className="text-muted mb-0">Order {detail.order_number}</p>}
            </div>
            {detail && (
              <span className={`badge ${getInvoiceStatusMeta(detail.status).badgeClass}`}>
                {getInvoiceStatusMeta(detail.status).label}
              </span>
            )}
          </div>
          <div className="card-body">
            {detailLoading ? (
              <p className="text-muted mb-0">Loading invoice details...</p>
            ) : !detail ? (
              <p className="text-muted mb-0">Select an invoice to inspect its immutable commercial snapshot.</p>
            ) : (
              <>

                <div className="kpc-commercial-detail-meta">
                  <div>
                    <label>Customer</label>
                    <strong>{detail.customer_name}</strong>
                  </div>
                  <div>
                    <label>Balance Due</label>
                    <strong>{formatInr(detail.outstanding_balance)}</strong>
                  </div>
                  <div>
                    <label>Issued</label>
                    <strong>{formatCommercialDate(detail.issued_at)}</strong>
                  </div>
                  <div>
                    <label>Due Date</label>
                    <strong>{formatCommercialDate(detail.due_at)}</strong>
                  </div>
                </div>

                <div className="table-responsive mb-3">
                  <table className="table table-sm mb-0">
                    <thead>
                      <tr>
                        <th>Description</th>
                        <th className="text-end">Qty</th>
                        <th className="text-end">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.items.map((item, idx) => (
                        <tr key={`${item.description}-${idx}`}>
                          <td>{item.description}</td>
                          <td className="text-end">
                            {item.quantity} {item.unit}
                          </td>
                          <td className="text-end">{formatInr(item.line_total)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="kpc-commercial-totals mb-3">
                  <div className="kpc-commercial-totals-row">
                    <span>Subtotal</span>
                    <span>{formatInr(detail.subtotal_amount)}</span>
                  </div>
                  <div className="kpc-commercial-totals-row">
                    <span>Tax ({Number(detail.tax_rate_percent).toFixed(2)}%)</span>
                    <span>{formatInr(detail.tax_amount)}</span>
                  </div>
                  <div className="kpc-commercial-totals-row is-total">
                    <span>Total</span>
                    <span>{formatInr(detail.total_amount)}</span>
                  </div>
                  <div className="kpc-commercial-totals-row"><span>Paid</span><span>{formatInr(detail.paid_amount)}</span></div>
                  <div className="kpc-commercial-totals-row"><strong>Outstanding Balance</strong><strong>{formatInr(detail.outstanding_balance)}</strong></div>
                </div>

                <div className="d-flex gap-2 flex-wrap">
                  <ProtectedDownload
                    className="btn btn-outline-primary btn-sm flex-grow-1"
                    href={buildDemoInvoiceDownloadUrl(detail.id)}
                  >
                    Download Invoice
                  </ProtectedDownload>

                </div>
                <PaymentHistory payments={detail.payments} />
                <DemoPaymentForm key={detail.id} invoice={detail} onRecorded={async () => {
                  await refreshDetail();
                  await loadInvoices();
                }} />
              </>
            )}
          </div>
        </div>
      </div>
      <LiveSyncBadge visible={isLiveSynced} />
    </section>
  );
}
