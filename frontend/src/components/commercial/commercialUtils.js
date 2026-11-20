export function formatInr(amount) {
  const num = Number(amount ?? 0);
  if (Number.isNaN(num)) return '₹0.00';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatCommercialDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatCommercialDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const ORDER_STATUS_META = {
  awaiting_payment: { label: 'Awaiting Payment', badgeClass: 'bg-warning' },
  pending_payment: { label: 'Awaiting Payment', badgeClass: 'bg-warning' },
  confirmed: { label: 'Confirmed', badgeClass: 'bg-primary' },
  cancelled: { label: 'Cancelled', badgeClass: 'bg-danger' },
};

const INVOICE_STATUS_META = {
  unpaid: { label: 'Unpaid', badgeClass: 'bg-warning' },
  partially_paid: { label: 'Partially Paid', badgeClass: 'bg-info' },
  paid: { label: 'Paid', badgeClass: 'bg-success' },
  cancelled: { label: 'Cancelled', badgeClass: 'bg-danger' },
};

export function getOrderStatusMeta(status) {
  return ORDER_STATUS_META[status] || {
    label: String(status || 'Unknown').replace(/_/g, ' '),
    badgeClass: 'bg-secondary',
  };
}

export function getInvoiceStatusMeta(status) {
  return INVOICE_STATUS_META[status] || {
    label: String(status || 'Unknown').replace(/_/g, ' '),
    badgeClass: 'bg-secondary',
  };
}

export function buildDemoInvoiceDownloadUrl(invoiceId) {
  return `/api/invoices/${invoiceId}/download`;
}
