"""S09 ledger verification, called while assignment holds the order row lock."""
from decimal import Decimal
from sqlalchemy import select, func
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, SimulatedPayment

class SettlementGate:
    available = True
    message = 'Full settlement must match the invoice and successful payment ledger.'

    def is_fully_settled(self, db, order):
        invoice = db.scalar(select(CommercialInvoice).where(CommercialInvoice.order_id == order.id).execution_options(populate_existing=True))
        snapshot = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order.id).execution_options(populate_existing=True))
        if not invoice or not snapshot or order.status != 'confirmed':
            return False
        if invoice.customer_id != order.customer_id or invoice.status != 'paid' or snapshot.cancelled_at:
            return False
        paid, count = db.execute(select(func.coalesce(func.sum(SimulatedPayment.amount), 0), func.count(SimulatedPayment.id)).where(SimulatedPayment.invoice_id == invoice.id, SimulatedPayment.outcome == 'succeeded')).one()
        return (invoice.is_demo_invoice and invoice.currency == snapshot.currency == 'INR'
                and invoice.total_amount > 0 and count > 0
                and invoice.total_amount == snapshot.total_amount == Decimal(paid)
                and invoice.paid_amount == snapshot.paid_amount == Decimal(paid)
                and snapshot.successful_payment_count == count)

def get_settlement_gate():
    return SettlementGate()
