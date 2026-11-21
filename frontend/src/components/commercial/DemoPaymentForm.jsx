import React, { useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { paymentStorageKey, preparePayment, readPendingPayment, sendPaymentAttempt } from '../../utils/demoPayments.js';
import { emitKpcSync } from '../../utils/kpcLiveSync.jsx';
import { formatCommercialDateTime, formatInr } from './commercialUtils';

export function PaymentHistory({ payments = [] }) {
  return <section className="mt-3" aria-label="Simulated payment history">
    <h3 className="h6">Payment History — Demo</h3>
    {!payments.length ? <p className="small text-muted">No simulated payments recorded.</p> :
      <div className="table-responsive"><table className="table table-sm">
        <thead><tr><th>Reference / Date</th><th>Outcome</th><th className="text-end">Amount</th></tr></thead>
        <tbody>{payments.map(payment => <tr key={payment.id}>
          <td>DEMO-{payment.id}<small className="d-block text-muted">{formatCommercialDateTime(payment.created_at)} · User #{payment.actor_user_id}</small></td>
          <td><span className={`badge ${payment.outcome === 'succeeded' ? 'bg-success' : 'bg-danger'}`}>{payment.outcome === 'succeeded' ? 'Succeeded' : 'Failed'}</span></td>
          <td className="text-end">{formatInr(payment.amount)}</td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}

export default function DemoPaymentForm({ invoice, onRecorded }) {
  const { user } = useAuth();
  const storageKey = paymentStorageKey(user.id, invoice.id);
  const [pending, setPending] = useState(() => readPendingPayment(storageKey));
  const [amount, setAmount] = useState(() => readPendingPayment(storageKey)?.amount || String(invoice.outstanding_balance));
  const [outcome, setOutcome] = useState(() => readPendingPayment(storageKey)?.outcome || 'succeeded');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const sending = useRef(false);
  const canPay = ['unpaid', 'partially_paid'].includes(invoice.status) && Number(invoice.outstanding_balance) > 0;

  async function submit(event) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setBusy(true); setError(''); setMessage('');
    let attempt;
    try {
      attempt = pending || preparePayment(storageKey, amount, outcome);
      setPending(attempt);
      const result = await sendPaymentAttempt(invoice.id, attempt);
      sessionStorage.removeItem(storageKey);
      setPending(null);
      setAmount('');
      setMessage(result.outcome === 'succeeded'
        ? `Simulated payment DEMO-${result.id} recorded: ${formatInr(result.amount)}.`
        : `Demo attempt DEMO-${result.id} failed as selected. The balance was not reduced.`);
      emitKpcSync('PAYMENT_RECORDED', { invoice_id: invoice.id, order_id: invoice.order_id });
      try { await onRecorded(); } catch { setError('Payment result saved. Refresh the invoice to see its current balance.'); }
    } catch (err) {
      if (err.definitive) {
        sessionStorage.removeItem(storageKey);
        setPending(null);
        setError(err.message);
      } else {
        setError(attempt ? `${err.message} The result is unconfirmed. Retry the same attempt to retrieve or finish it safely.` : err.message);
      }
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  return <section className="border-top pt-3 mt-3" aria-label="Record simulated payment">
    <h3 className="h6">{user.role === 'admin' ? 'Record Demo Payment' : 'Make a Demo Payment'}</h3>
    <p className="small text-muted">Simulation only. No money is collected. Full settlement confirms the order.</p>
    {message && <p className="alert alert-info py-2" role="status">{message}</p>}
    {error && <p className="alert alert-danger py-2" role="alert">{error}</p>}
    {pending && <p className="small">An unfinished attempt is saved in this tab. Its amount and outcome stay unchanged when retried.</p>}
    {(canPay || pending) ? <form onSubmit={submit}>
      <div className="row g-2 mb-3">
        <div className="col-sm-6"><label htmlFor={`demo-amount-${invoice.id}`} className="form-label">Amount (INR)</label>
          <input id={`demo-amount-${invoice.id}`} className="form-control" type="number" min="0.01" step="0.01" max={pending ? undefined : invoice.outstanding_balance}
            value={pending?.amount || amount} onChange={event => setAmount(event.target.value)} disabled={busy || !!pending} required /></div>
        <div className="col-sm-6"><label htmlFor={`demo-outcome-${invoice.id}`} className="form-label">Demo outcome</label>
          <select id={`demo-outcome-${invoice.id}`} className="form-select" value={pending?.outcome || outcome} onChange={event => setOutcome(event.target.value)} disabled={busy || !!pending}>
            <option value="succeeded">Simulate success</option><option value="failed">Simulate failure</option>
          </select></div>
      </div>
      <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>{busy ? 'Recording…' : pending ? 'Retry Same Demo Attempt' : 'Confirm Demo Payment'}</button>
    </form> : <p className="small text-muted">{invoice.status === 'cancelled' ? 'This invoice is cancelled.' : 'No outstanding balance to pay.'}</p>}
  </section>;
}
