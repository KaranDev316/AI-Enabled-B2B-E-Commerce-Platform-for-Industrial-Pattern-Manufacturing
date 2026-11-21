from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Order, User
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, OrderStatusEvent, SimulatedPayment
from app.schemas.commercial import SimulatedPaymentRequest, SimulatedPaymentResponse
from app.services.commercial_service import AWAITING_PAYMENT_STATUSES, _require_commercial_access


def conflict(code, message):
    raise HTTPException(409, detail={'code': code, 'message': message})


def matching_attempt(db, invoice_id, payload):
    previous = db.scalar(select(SimulatedPayment).where(SimulatedPayment.idempotency_key == str(payload.idempotency_key)))
    if previous is None:
        return None
    if previous.invoice_id != invoice_id or previous.amount != payload.amount or previous.outcome != payload.outcome:
        conflict('IDEMPOTENCY_CONFLICT', 'This payment key was already used with different details.')
    return SimulatedPaymentResponse.model_validate(previous)


def record_simulated_payment(db: Session, invoice_id: int, user: User, payload: SimulatedPaymentRequest):
    invoice = db.get(CommercialInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(404, detail={'code': 'INVOICE_NOT_FOUND', 'message': 'Invoice not found.'})
    _require_commercial_access(user, invoice.customer_id)
    try:
        # Cancellation and every payment lock the same order before reading settlement.
        order = db.scalar(select(Order).where(Order.id == invoice.order_id).with_for_update().execution_options(populate_existing=True))
        invoice = db.scalar(select(CommercialInvoice).where(CommercialInvoice.id == invoice_id).execution_options(populate_existing=True))
        snapshot = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order.id).execution_options(populate_existing=True))
        previous = matching_attempt(db, invoice_id, payload)
        if previous:
            db.commit()
            return previous  # Exact original result, even after settlement/cancellation.
        if snapshot is None or not invoice.is_demo_invoice or order.status not in AWAITING_PAYMENT_STATUSES or invoice.status not in ('unpaid', 'partially_paid'):
            conflict('PAYMENT_NOT_ALLOWED', 'Only an outstanding invoice awaiting payment can receive a new payment.')
        paid = db.scalar(select(func.coalesce(func.sum(SimulatedPayment.amount), 0)).where(SimulatedPayment.invoice_id == invoice_id, SimulatedPayment.outcome == 'succeeded'))
        paid = Decimal(paid)
        if paid != invoice.paid_amount or paid != snapshot.paid_amount:
            conflict('SETTLEMENT_STATE_UNAVAILABLE', 'The saved payment balance needs review before another payment can be recorded.')
        if payload.amount > invoice.total_amount - paid:
            conflict('OVERPAYMENT', 'The payment amount exceeds the outstanding balance. Refresh the invoice.')
        attempt = SimulatedPayment(invoice_id=invoice_id, actor_user_id=user.id,
            idempotency_key=str(payload.idempotency_key), amount=payload.amount.quantize(Decimal('0.01')), outcome=payload.outcome)
        db.add(attempt)
        if payload.outcome == 'succeeded':
            paid += payload.amount
            invoice.paid_amount = snapshot.paid_amount = paid
            snapshot.successful_payment_count += 1
            invoice.status = 'paid' if paid == invoice.total_amount else 'partially_paid'
            if invoice.status == 'paid':
                old_status = order.status
                order.status = 'confirmed'
                db.add(OrderStatusEvent(order_id=order.id, actor_user_id=user.id, event_type='order_confirmed',
                    from_status=old_status, to_status='confirmed', note='Payment completed. Order ready for production assignment.'))
        db.flush()
        result = SimulatedPaymentResponse.model_validate(attempt)
        db.commit()
        return result
    except IntegrityError:
        # A simultaneous request on a different invoice can race for the global key.
        db.rollback()
        previous = matching_attempt(db, invoice_id, payload)
        if previous:
            return previous
        raise
    except Exception:
        db.rollback()
        raise
