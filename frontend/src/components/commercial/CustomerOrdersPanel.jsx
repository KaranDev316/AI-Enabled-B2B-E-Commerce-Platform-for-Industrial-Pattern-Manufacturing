import { ProtectedDownload } from '../ProtectedFiles';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  buildDemoInvoiceDownloadUrl,
  formatCommercialDate,
  formatCommercialDateTime,
  formatInr,
  getOrderStatusMeta,
} from './commercialUtils';
import './commercial.css';
import { useKpcLiveSync, emitKpcSync, LiveSyncBadge } from '../../utils/kpcLiveSync.jsx';

/**
 * Customer Orders screen (S08).
 * Visual references: docs/ui-ux/customer/orders.webp and docs/ui-ux/global/ui-kit.webp.
 * S08 boundaries: no invented production/job history, no payment controls until S09.
 */
export default function CustomerOrdersPanel({ csrfToken, onNewRfq, onOpenInvoices }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [orderDetail, setOrderDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const [cancelTarget, setCancelTarget] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelSubmitting, setCancelSubmitting] = useState(false);
  const [cancelError, setCancelError] = useState('');
  const [toastMessage, setToastMessage] = useState('');

  const loadOrders = useCallback(async (options = {}) => {
    const quiet = options.quiet === true;
    if (!quiet) { setLoading(true); setError(''); }
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (search.trim()) params.set('search', search.trim());
      const query = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(`/api/orders${query}`, { credentials: 'include' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail?.message || 'Unable to load orders.');
      }
      const data = await res.json();
      setOrders(Array.isArray(data) ? data : []);
      setError('');
    } catch (err) {
      if (!quiet) setError(err.message || 'Unable to load orders.');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [search, statusFilter]);


  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const openOrderDetail = useCallback(async (orderId, quiet = false) => {
    if (!quiet) setSelectedOrderId(orderId);
    if (!quiet) setDetailLoading(true);
    if (!quiet) setDetailError('');
    try {
      const res = await fetch(`/api/orders/${orderId}`, { credentials: 'include' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail?.message || 'Unable to load order details.');
      }
      const next = await res.json();
      setOrderDetail(current => quiet && current?.id !== orderId ? current : next);
    } catch (err) {
      if (!quiet) { setDetailError(err.message || 'Unable to load order details.'); setOrderDetail(null); }
    } finally {
      if (!quiet) setDetailLoading(false);
    }
  }, []);

  const { isLiveSynced } = useKpcLiveSync(async () => {
    await loadOrders({ quiet: true });
    if (selectedOrderId) await openOrderDetail(selectedOrderId, true);
  }, 4000);

  const handleConfirmCancel = async (e) => {
    e.preventDefault();
    if (!cancelTarget) return;
    setCancelSubmitting(true);
    setCancelError('');
    try {
      const res = await fetch(`/api/orders/${cancelTarget.id}/cancel`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        body: JSON.stringify({ reason: cancelReason.trim() || null }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body?.detail?.message || 'Unable to cancel this order.');
      }
      setToastMessage(body?.message || 'Unpaid order cancelled.');
      setCancelTarget(null);
      setCancelReason('');
      await loadOrders({ quiet: true });
      emitKpcSync('ORDER_CANCELLED', { order_id: cancelTarget.id });
      if (selectedOrderId === cancelTarget.id) {
        setOrderDetail(body.order);
      }
    } catch (err) {
      setCancelError(err.message || 'Unable to cancel this order.');
    } finally {
      setCancelSubmitting(false);
    }
  };

  const kpis = useMemo(() => {
    const total = orders.length;
    const awaiting = orders.filter((o) => o.status === 'awaiting_payment' || o.status === 'pending_payment').length;
    const confirmed = orders.filter((o) => o.status === 'confirmed').length;
    const cancelled = orders.filter((o) => o.status === 'cancelled').length;
    return { total, awaiting, confirmed, cancelled };
  }, [orders]);

  return (
    <section className="kpc-commercial-panel" aria-label="My Orders">
      {onNewRfq && <div className="quotation-toolbar"><button type="button" className="btn btn-primary" onClick={onNewRfq}>+ New RFQ</button></div>}

      {toastMessage && (
        <div className="alert alert-success d-flex justify-content-between align-items-center" role="status">
          <span>{toastMessage}</span>
          <button type="button" className="btn-close" aria-label="Dismiss" onClick={() => setToastMessage('')} />
        </div>
      )}

      <div className="kpc-commercial-kpi-grid">
        <div className="kpc-commercial-kpi">
          <span>Total Orders</span>
          <strong>{kpis.total}</strong>
          <small>Persisted orders</small>
        </div>
        <div className="kpc-commercial-kpi tone-warn">
          <span>Awaiting Payment</span>
          <strong>{kpis.awaiting}</strong>
          <small>Eligible for cancellation if unpaid</small>
        </div>
        <div className="kpc-commercial-kpi tone-success">
          <span>Confirmed</span>
          <strong>{kpis.confirmed}</strong>
          <small>Settled commercial orders</small>
        </div>
        <div className="kpc-commercial-kpi tone-danger">
          <span>Cancelled</span>
          <strong>{kpis.cancelled}</strong>
          <small>History preserved</small>
        </div>
      </div>

      <div className="card">
        <div className="customer-list-toolbar">
          <div className="customer-search">
            <input
              type="search"
              placeholder="Search by Order ID, product, or invoice..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search orders"
            />
          </div>
          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter orders by status"
          >
            <option value="all">All Statuses</option>
            <option value="awaiting_payment">Awaiting Payment</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={() => {
              setSearch('');
              setStatusFilter('all');
            }}
          >
            Reset
          </button>
        </div>

        {loading ? (
          <div className="kpc-commercial-state-box">
            <h3>Loading orders...</h3>
            <p>Fetching your persisted commercial orders.</p>
          </div>
        ) : error ? (
          <div className="kpc-commercial-state-box">
            <h3>Unable to load orders</h3>
            <p>{error}</p>
            <button type="button" className="btn btn-outline-primary btn-sm" onClick={loadOrders}>
              Retry
            </button>
          </div>
        ) : orders.length === 0 ? (
          <div className="kpc-commercial-state-box">
            <h3>No orders found</h3>
            <p>Orders appear here after you accept an eligible quotation.</p>
            {onNewRfq && (
              <button type="button" className="btn btn-primary btn-sm" onClick={onNewRfq}>
                + Request Quotation
              </button>
            )}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Product / Requirement</th>
                  <th>Order Date</th>
                  <th>Quantity</th>
                  <th>Accepted Total</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const meta = getOrderStatusMeta(order.status);
                  return (
                    <tr key={order.id}>
                      <td>
                        <strong>{order.order_number}</strong>
                      </td>
                      <td>
                        <div>
                          <strong>{order.product_summary}</strong>
                        </div>
                        {order.invoice_number && (
                          <small className="text-muted">Invoice: {order.invoice_number}</small>
                        )}
                      </td>
                      <td>{formatCommercialDate(order.created_at)}</td>
                      <td>{order.quantity}</td>
                      <td>
                        <strong>{formatInr(order.total_amount)}</strong>
                      </td>
                      <td>
                        <span className={`badge ${meta.badgeClass}`}>{meta.label}</span>
                      </td>
                      <td>
                        <div className="d-flex gap-2 flex-wrap">
                          <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={() => openOrderDetail(order.id)}
                          >
                            View Details
                          </button>
                          {order.can_cancel && (
                            <button
                              type="button"
                              className="btn btn-outline-danger btn-sm"
                              onClick={() => {
                                setCancelTarget(order);
                                setCancelReason('');
                                setCancelError('');
                              }}
                            >
                              Cancel Order
                            </button>
                          )}
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

      {selectedOrderId !== null && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(6, 26, 55, 0.45)' }} role="dialog" aria-modal="true">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  {orderDetail ? `Order ${orderDetail.order_number}` : 'Order Details'}
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  aria-label="Close"
                  onClick={() => {
                    setSelectedOrderId(null);
                    setOrderDetail(null);
                  }}
                />
              </div>
              <div className="modal-body">
                {detailLoading ? (
                  <p className="text-muted mb-0">Loading order commercial snapshot...</p>
                ) : detailError ? (
                  <div className="alert alert-danger mb-0">{detailError}</div>
                ) : orderDetail ? (
                  <>
                    <div className="kpc-commercial-detail-meta">
                      <div>
                        <label>Order Status</label>
                        <strong>{getOrderStatusMeta(orderDetail.status).label}</strong>
                      </div>
                      <div>
                        <label>Production Tracking</label>
                        <strong>{orderDetail.status === 'cancelled' ? 'Cancelled — production will not start' : 'Not started (requires settled confirmation)'}</strong>
                      </div>
                      <div>
                        <label>Estimated Lead Time</label>
                        <strong>
                          {orderDetail.estimated_lead_time_days
                            ? `${orderDetail.estimated_lead_time_days} days (estimate)`
                            : 'Not specified'}
                        </strong>
                      </div>
                      <div>
                        <label>Outstanding Balance</label>
                        <strong>{formatInr(orderDetail.outstanding_balance)}</strong>
                      </div>
                    </div>

                    <h6 className="mb-2">Accepted Commercial Snapshot</h6>
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
                          {orderDetail.items.map((item, idx) => (
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

                    <div className="kpc-commercial-totals mb-3">
                      <div className="kpc-commercial-totals-row">
                        <span>Subtotal</span>
                        <span>{formatInr(orderDetail.subtotal_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row">
                        <span>Tax ({Number(orderDetail.tax_rate_percent).toFixed(2)}%)</span>
                        <span>{formatInr(orderDetail.tax_amount)}</span>
                      </div>
                      <div className="kpc-commercial-totals-row is-total">
                        <span>Total</span>
                        <span>{formatInr(orderDetail.total_amount)}</span>
                      </div>
                    </div>

                    {orderDetail.cancellation_reason && (
                      <div className="alert alert-warning">
                        <strong>Cancellation Reason:</strong> {orderDetail.cancellation_reason}
                      </div>
                    )}

                    <h6 className="mb-2">Recorded Order History</h6>
                    <ul className="kpc-commercial-timeline">
                      {orderDetail.status_history.map((ev) => (
                        <li key={ev.id}>
                          <strong>{ev.event_type.replace(/_/g, ' ')}</strong>
                          <span>{ev.note || `Status changed to ${ev.to_status}`}</span>
                          <small>{formatCommercialDateTime(ev.created_at)}</small>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </div>
              <div className="modal-footer">
                {orderDetail?.invoice && (
                  <ProtectedDownload
                    className="btn btn-outline-primary btn-sm"
                    href={buildDemoInvoiceDownloadUrl(orderDetail.invoice.id)}
                  >
                    Download Invoice
                  </ProtectedDownload>
                )}
                {onOpenInvoices && (
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => {
                      setSelectedOrderId(null);
                      onOpenInvoices();
                    }}
                  >
                    Open Invoices
                  </button>
                )}
                {orderDetail?.can_cancel && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => {
                      setCancelTarget(orderDetail);
                      setCancelReason('');
                      setCancelError('');
                    }}
                  >
                    Cancel Unpaid Order
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {cancelTarget && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(6, 26, 55, 0.55)' }} role="dialog" aria-modal="true">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <form onSubmit={handleConfirmCancel}>
                <div className="modal-header">
                  <h5 className="modal-title">Cancel Unpaid Order {cancelTarget.order_number}?</h5>
                  <button
                    type="button"
                    className="btn-close"
                    aria-label="Close"
                    onClick={() => setCancelTarget(null)}
                  />
                </div>
                <div className="modal-body">
                  <p className="small text-muted">
                    This action marks the order and its invoice as cancelled while preserving commercial history.
                    Cancelled orders cannot receive payments or be assigned to production.
                  </p>
                  {cancelError && <div className="alert alert-danger">{cancelError}</div>}
                  <label className="form-label" htmlFor="kpc-cancel-reason">
                    Reason for cancellation (optional)
                  </label>
                  <textarea
                    id="kpc-cancel-reason"
                    className="form-control"
                    rows={3}
                    maxLength={500}
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    placeholder="e.g., Requirement postponed or revising specifications"
                  />
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setCancelTarget(null)}
                    disabled={cancelSubmitting}
                  >
                    Keep Order
                  </button>
                  <button type="submit" className="btn btn-danger btn-sm" disabled={cancelSubmitting}>
                    {cancelSubmitting ? 'Cancelling...' : 'Confirm Cancellation'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      <LiveSyncBadge visible={isLiveSynced} />
    </section>
  );
}
