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
 * Customer Invoices screen (S08/S09).
 * Visual references: docs/ui-ux/customer/invoices-and-payments.webp and docs/ui-ux/global/ui-kit.webp.
 * Partial simulated settlement and history; no real UPI/card/bank credential fields.
 */
export default function CustomerInvoicesPanel() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [staleWarning, setStaleWarning] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const loadInvoices = useCallback(async (options = {}) => {
    const quiet = options.quiet === true;
    if (!quiet) { setLoading(true); setError(''); }
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
      setInvoices(Array.isArray(data) ? data : []);
      setError('');
      setStaleWarning(false);
    } catch (err) {
      if (!quiet) setError(err.message || 'Unable to load invoices.'); else setStaleWarning(true);
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [search, statusFilter]);




  useEffect(() => {
    loadInvoices();
  }, [loadInvoices]);

  const openInvoiceDetail = async (invoiceId, quiet = false) => {
    if (!quiet) setDetailLoading(true);
    if (!quiet) setDetailError('');
    try {
      const res = await fetch(`/api/invoices/${invoiceId}`, { credentials: 'include' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail?.message || 'Unable to load invoice details.');
      }
      const next = await res.json();
      setSelectedInvoice(current => quiet && current?.id !== invoiceId ? current : next);
    } catch (err) {
      if (!quiet) setDetailError(err.message || 'Unable to load invoice details.');
    } finally {
      if (!quiet) setDetailLoading(false);
    }
  };

  const { isLiveSynced } = useKpcLiveSync(async () => {
    await loadInvoices({ quiet: true });
    if (selectedInvoice) await openInvoiceDetail(selectedInvoice.id, true);
  }, 4000);

  const summary = useMemo(() => {
    const active = invoices.filter((inv) => inv.status !== 'cancelled');
    const outstanding = active.reduce((acc, inv) => acc + Number(inv.outstanding_balance || 0), 0);
    const paid = active.reduce((acc, inv) => acc + Number(inv.paid_amount || 0), 0);
    return {
      outstanding,
      paid,
      activeCount: active.length,
    };
  }, [invoices]);

  return (
    <section className="kpc-commercial-panel" aria-label="My Invoices and Payments">


      <div className="kpc-commercial-demo-banner">
        View your invoices, track payments, and settle outstanding balances.
      </div>

      {staleWarning && !error && (

        <div className="alert alert-warning" role="status">Latest updates could not be loaded. The records shown may be out of date; they will refresh automatically when the connection recovers.</div>

      )}

      <div className="kpc-commercial-kpi-grid cols-3">
        <div className="kpc-commercial-kpi tone-danger">
          <span>Outstanding Balance</span>
          <strong>{formatInr(summary.outstanding)}</strong>
          <small>Across {summary.activeCount} active invoice(s)</small>
        </div>
        <div className="kpc-commercial-kpi tone-success">
          <span>Paid</span>
          <strong>{formatInr(summary.paid)}</strong>
          <small>Recorded payments</small>
        </div>
        <div className="kpc-commercial-kpi">
          <span>Issued Invoices</span>
          <strong>{invoices.length}</strong>
          <small>One invoice per order</small>
        </div>
      </div>

      <div className="card">
        <div className="customer-list-toolbar">
          <div className="customer-search">
            <input
              type="search"
              placeholder="Search by Invoice No. or Order ID..."
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
            <p>Fetching your issued invoices.</p>
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
            <p>A invoice is generated automatically when you accept an eligible quotation.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Invoice No.</th>
                  <th>Order ID</th>
                  <th>Issue Date</th>
                  <th>Due Date</th>
                  <th>Total</th>
                  <th>Outstanding</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => {
                  const meta = getInvoiceStatusMeta(inv.status);
                  return (
                    <tr key={inv.id}>
                      <td>
                        <strong>{inv.invoice_number}</strong>
                      </td>
                      <td>{inv.order_number}</td>
                      <td>{formatCommercialDate(inv.issued_at)}</td>
                      <td>{formatCommercialDate(inv.due_at)}</td>
                      <td>
                        <strong>{formatInr(inv.total_amount)}</strong>
                      </td>
                      <td>{formatInr(inv.outstanding_balance)}</td>
                      <td>
                        <span className={`badge ${meta.badgeClass}`}>{meta.label}</span>
                      </td>
                      <td>
                        <div className="d-flex gap-2 flex-wrap">
                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={() => openInvoiceDetail(inv.id)}
                          >
                            Inspect
                          </button>
                          <ProtectedDownload
                            className="btn btn-outline-secondary btn-sm"
                            href={buildDemoInvoiceDownloadUrl(inv.id)}
                          >
                            Download PDF
                          </ProtectedDownload>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            disabled={inv.status === 'cancelled'}
                            onClick={() => openInvoiceDetail(inv.id)}
                          >
                            Payment
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(selectedInvoice || detailLoading || detailError) && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(6, 26, 55, 0.45)' }} role="dialog" aria-modal="true">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {selectedInvoice ? `Invoice ${selectedInvoice.invoice_number}` : 'Invoice Details'}
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Close"
                  onClick={() => {
                    setSelectedInvoice(null);
                    setDetailError('');
                  }}
                />
              </div>
              <div className="modal-body">
                {detailLoading ? (
                  <p className="text-muted mb-0">Loading invoice snapshot...</p>
                ) : detailError ? (
                  <div className="alert alert-danger mb-0">{detailError}</div>
                ) : selectedInvoice ? (
                  <>

                    <div className="kpc-commercial-detail-meta">
                      <div>
                        <label>Order Number</label>
                        <strong>{selectedInvoice.order_number}</strong>
                      </div>
                      <div>
                        <label>Invoice Status</label>
                        <strong>{getInvoiceStatusMeta(selectedInvoice.status).label}</strong>
                      </div>
                      <div>
                        <label>Billed To</label>
                        <strong>{selectedInvoice.customer_name}</strong>
                      </div>
                      <div>
                        <label>Issued / Due</label>
                        <strong>
                          {formatCommercialDate(selectedInvoice.issued_at)} /{' '}
                          {formatCommercialDate(selectedInvoice.due_at)}
                        </strong>
                      </div>
                    </div>

                    <div className="table-responsive mb-3">
                      <table className="table table-sm mb-0">
                        <thead>
                          <tr>
                            <th>Description</th>
                            <th className="text-end">Qty</th>
                            <th className="text-end">Unit Price</th>
                            <th className="text-end">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedInvoice.items.map((item, idx) => (
                            <tr key={`${item.description}-${idx}`}>
                              <td>{item.description}</td>
                              <td className="text-end">
                                {item.quantity} {item.unit}
                              </td>
                              <td className="text-end">{formatInr(item.unit_price)}</td>
                              <td className="text-end">{formatInr(item.line_total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="kpc-commercial-totals">
                      <div className="kpc-commercial-totals-row">
                        <span>Subtotal</span>
                        <span>{formatInr(selectedInvoice.subtotal_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row">
                        <span>Tax ({Number(selectedInvoice.tax_rate_percent).toFixed(2)}%)</span>
                        <span>{formatInr(selectedInvoice.tax_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row is-total">
                        <span>Total</span>
                        <span>{formatInr(selectedInvoice.total_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row">
                        <span>Paid</span>
                        <span>{formatInr(selectedInvoice.paid_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row">
                        <strong>Outstanding Balance</strong>
                        <strong>{formatInr(selectedInvoice.outstanding_balance)}</strong>
                      </div>
                    </div>
                    <PaymentHistory payments={selectedInvoice.payments} />
                    <DemoPaymentForm key={selectedInvoice.id} invoice={selectedInvoice} onRecorded={async () => {
                      await openInvoiceDetail(selectedInvoice.id, true);
                      await loadInvoices({ quiet: true });
                    }} />
                  </>
                ) : null}
              </div>
              <div className="modal-footer">
                {selectedInvoice && (
                  <ProtectedDownload
                    className="btn btn-primary btn-sm"
                    href={buildDemoInvoiceDownloadUrl(selectedInvoice.id)}
                  >
                    Download Invoice
                  </ProtectedDownload>
                )}
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setSelectedInvoice(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <LiveSyncBadge visible={isLiveSynced} />
    </section>
  );
}
