export const paymentStorageKey = (userId, invoiceId) => `kpc_demo_payment:${userId}:${invoiceId}`;

export function readPendingPayment(key) {
  try {
    const value = JSON.parse(sessionStorage.getItem(key));
    return value?.idempotency_key && value?.amount && ['succeeded', 'failed'].includes(value.outcome) ? value : null;
  } catch {
    return null;
  }
}

export function preparePayment(key, amount, outcome) {
  const pending = readPendingPayment(key);
  if (pending) return pending;
  if (!/^\d+(\.\d{1,2})?$/.test(amount) || !/[1-9]/.test(amount)) throw new Error('Enter a positive INR amount with at most two decimal places.');
  const attempt = { amount, outcome, idempotency_key: crypto.randomUUID() };
  // Persist before sending: a lost response or page reload must reuse this key.
  sessionStorage.setItem(key, JSON.stringify(attempt));
  return attempt;
}

export async function sendPaymentAttempt(invoiceId, attempt) {
  const response = await fetch(`/api/invoices/${invoiceId}/payments`, {
    method: 'POST', credentials: 'omit',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(attempt),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(body?.detail?.message || 'Unable to record the payment.');
    // Auth/access failures cannot establish whether an earlier lost-response attempt committed.
    error.definitive = [400, 409, 422].includes(response.status);
    throw error;
  }
  if (!body?.id || !['succeeded', 'failed'].includes(body.outcome)) throw new Error('The payment result could not be confirmed.');
  return body;
}
