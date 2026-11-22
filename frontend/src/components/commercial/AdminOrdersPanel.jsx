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
import { useKpcLiveSync, LiveSyncBadge } from '../../utils/kpcLiveSync.jsx';

/**
 * Admin Orders & Production (S08 commercial view).
 * Visual references: docs/ui-ux/admin/orders-and-production.webp and docs/ui-ux/global/ui-kit.webp.
 * S08 boundary: shows persisted commercial orders & snapshots; job assignment activates in S10 after S09 settlement.
 */
export default function AdminOrdersPanel() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

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
      const list = Array.isArray(data) ? data : [];
      setOrders(list);
      setError('');
      if (list.length > 0) setSelectedId(current => current ?? list[0].id);
    } catch (err) {
      if (!quiet) setError(err.message || 'Unable to load orders.');
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [search, statusFilter]);

  const { isLiveSynced } = useKpcLiveSync(async () => {
    await loadOrders({ quiet: true });
    if (!selectedId) return;
    try {
      const response = await fetch(`/api/orders/${selectedId}`);
      if (!response.ok) throw new Error('Unable to refresh order details.');
      const next = await response.json();
      setDetail(current => current?.id === next.id ? next : current);
    } catch (err) { console.warn('Order background refresh failed:', err); }
  }, 4000);


  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    fetch(`/api/orders/${selectedId}`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('Unable to load order details.'))))
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
    const total = orders.length;
    const awaiting = orders.filter((o) => o.status === 'awaiting_payment' || o.status === 'pending_payment').length;
    const confirmed = orders.filter((o) => o.status === 'confirmed').length;
    const cancelled = orders.filter((o) => o.status === 'cancelled').length;
    return { total, awaiting, confirmed, cancelled };
  }, [orders]);

  return (
    <section className="kpc-commercial-panel" aria-label="Admin Orders and Production">


      <div className="kpc-commercial-kpi-grid">
        <div className="kpc-commercial-kpi">
          <span>Total Orders</span>
          <strong>{kpis.total}</strong>
          <small>All customer orders</small>
        </div>
        <div className="kpc-commercial-kpi tone-warn">
          <span>Awaiting Payment</span>
          <strong>{kpis.awaiting}</strong>
          <small>Cannot be assigned until settled</small>
        </div>
        <div className="kpc-commercial-kpi tone-success">
          <span>Confirmed</span>
          <strong>{kpis.confirmed}</strong>
          <small>Ready for production assignment</small>
        </div>
        <div className="kpc-commercial-kpi tone-danger">
          <span>Cancelled</span>
          <strong>{kpis.cancelled}</strong>
          <small>Blocked from payment &amp; assignment</small>
        </div>
      </div>

      <div className="kpc-commercial-split">
        <div className="card">
          <div className="customer-list-toolbar">
            <div className="customer-search">
              <input
                type="search"
                placeholder="Search by Order ID, customer, or product..."
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
          </div>

          {loading ? (
            <div className="kpc-commercial-state-box">
              <h3>Loading orders...</h3>
              <p>Fetching operational order records.</p>
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
              <h3>No orders yet</h3>
              <p>Orders appear here when customers accept an eligible quotation.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Customer</th>
                    <th>Product</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => {
                    const meta = getOrderStatusMeta(order.status);
                    const isSelected = order.id === selectedId;
                    return (
                      <tr
                        key={order.id}
                        className={isSelected ? 'kpc-commercial-row-selected' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedId(order.id)}
                      >
                        <td>
                          <strong>{order.order_number}</strong>
                        </td>
                        <td>{order.customer_name}</td>
                        <td>{order.product_summary}</td>
                        <td>{formatCommercialDate(order.created_at)}</td>
                        <td>
                          <strong>{formatInr(order.total_amount)}</strong>
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
                {detail ? `Order ${detail.order_number}` : 'Order Overview'}
              </h2>
              {detail && <p className="text-muted mb-0">{detail.customer_name}</p>}
            </div>
            {detail && (
              <span className={`badge ${getOrderStatusMeta(detail.status).badgeClass}`}>
                {getOrderStatusMeta(detail.status).label}
              </span>
            )}
          </div>
          <div className="card-body">
            {detailLoading ? (
              <p className="text-muted mb-0">Loading commercial snapshot...</p>
            ) : !detail ? (
              <p className="text-muted mb-0">Select an order from the table to inspect its commercial snapshot.</p>
            ) : (
              <>
                <div className="kpc-commercial-detail-meta">
                  <div>
                    <label>Accepted Total</label>
                    <strong>{formatInr(detail.total_amount)}</strong>
                  </div>
                  <div>
                    <label>Outstanding</label>
                    <strong>{formatInr(detail.outstanding_balance)}</strong>
                  </div>
                  <div>
                    <label>Lead Time Estimate</label>
                    <strong>
                      {detail.estimated_lead_time_days
                        ? `${detail.estimated_lead_time_days} days (est.)`
                        : 'Not specified'}
                    </strong>
                  </div>
                  <div>
                    <label>Production Job</label>
                    <strong>Not assigned</strong>
                  </div>
                </div>

                <div className="alert alert-light border small mb-3">
                  {detail.can_assign
                    ? 'Fully settled and confirmed. Ready for production assignment in S10.'
                    : 'Production assignment is blocked until full settlement confirms the order.'}
                </div>

                {detail.cancellation_reason && (
                  <div className="alert alert-warning small">
                    <strong>Cancelled:</strong> {detail.cancellation_reason}
                  </div>
                )}

                <h6 className="mb-2">Timeline</h6>
                <ul className="kpc-commercial-timeline mb-3">
                  {detail.status_history.map((ev) => (
                    <li key={ev.id}>
                      <strong>{ev.event_type.replace(/_/g, ' ')}</strong>
                      <span>{ev.note || `Status → ${ev.to_status}`}</span>
                      <small>{formatCommercialDateTime(ev.created_at)}</small>
                    </li>
                  ))}
                </ul>

                {detail.invoice && (
                  <ProtectedDownload
                    className="btn btn-outline-primary btn-sm w-100"
                    href={buildDemoInvoiceDownloadUrl(detail.invoice.id)}
                  >
                    Download Invoice ({detail.invoice.invoice_number})
                  </ProtectedDownload>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      <LiveSyncBadge visible={isLiveSynced} />
    </section>
  );
}
