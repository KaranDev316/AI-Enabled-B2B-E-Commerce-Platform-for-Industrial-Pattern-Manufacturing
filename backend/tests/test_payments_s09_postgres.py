"""Real PostgreSQL serialization: payments share the cancellation order lock."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Order, User
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, OrderStatusEvent, SimulatedPayment
from app.schemas.commercial import SimulatedPaymentRequest
from app.services.commercial_service import cancel_unpaid_order, create_order_and_invoice_atomic
from app.services.payment_service import record_simulated_payment
from test_quotations_s07_postgres import pg_engine


def seed(engine, count=1):
    with Session(engine) as db:
        owner = User(email='owner@s09.test', password_hash='fixture-only', role='customer', is_active=True)
        db.add(owner); db.flush()
        ids = []
        for _ in range(count):
            order, _, invoice = create_order_and_invoice_atomic(db, customer_id=owner.id, customer_name='S09 Foundry',
                product_summary='Test pattern', items=[{'description':'Tooling', 'quantity':1, 'unit_price':'100.00'}], tax_rate_percent=0)
            ids.append((order.id, invoice.id))
        db.commit()
        return owner.id, ids


def race(engine, user_id, operations):
    barrier = Barrier(len(operations))
    def run(operation):
        with Session(engine) as db:
            user = db.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                return 200, operation(db, user)
            except HTTPException as exc:
                db.rollback()
                return exc.status_code, None
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(run, operations))


def payment(invoice_id, amount='60', key=None):
    payload = SimulatedPaymentRequest(amount=amount, idempotency_key=key or uuid4())
    return lambda db, user: record_simulated_payment(db, invoice_id, user, payload).model_dump(mode='json')


def test_concurrent_overpayment_is_blocked(pg_engine):
    owner, [(order_id, invoice_id)] = seed(pg_engine)
    results = race(pg_engine, owner, [payment(invoice_id), payment(invoice_id)])
    assert sorted(status for status, _ in results) == [200, 409]
    with Session(pg_engine) as db:
        assert db.scalar(select(func.sum(SimulatedPayment.amount))) == Decimal('60')
        assert db.get(CommercialInvoice, invoice_id).paid_amount == Decimal('60')
        assert db.get(Order, order_id).status == 'awaiting_payment'


def test_concurrent_installments_confirm_once(pg_engine):
    owner, [(order_id, invoice_id)] = seed(pg_engine)
    assert [status for status, _ in race(pg_engine, owner, [payment(invoice_id, '40'), payment(invoice_id, '60')])] == [200, 200]
    with Session(pg_engine) as db:
        assert db.get(Order, order_id).status == 'confirmed'
        assert db.get(CommercialInvoice, invoice_id).paid_amount == Decimal('100')
        assert db.scalar(select(func.count()).select_from(OrderStatusEvent).where(OrderStatusEvent.event_type == 'order_confirmed')) == 1


def test_concurrent_same_key_returns_original(pg_engine):
    owner, [(_, invoice_id)] = seed(pg_engine)
    key = uuid4()
    results = race(pg_engine, owner, [payment(invoice_id, '100', key), payment(invoice_id, '100', key)])
    assert results[0] == results[1] and results[0][0] == 200
    with Session(pg_engine) as db:
        assert db.scalar(select(func.count()).select_from(SimulatedPayment)) == 1


def test_global_key_reuse_across_invoices_conflicts(pg_engine):
    owner, ids = seed(pg_engine, count=2)
    key = uuid4()
    results = race(pg_engine, owner, [payment(ids[0][1], '10', key), payment(ids[1][1], '10', key)])
    assert sorted(status for status, _ in results) == [200, 409]
    with Session(pg_engine) as db:
        assert db.scalar(select(func.sum(CommercialInvoice.paid_amount))) == Decimal('10')
        assert db.scalar(select(func.count()).select_from(SimulatedPayment)) == 1


def test_payment_cancellation_race_has_one_consistent_outcome(pg_engine):
    owner, [(order_id, invoice_id)] = seed(pg_engine)
    def cancel(db, user):
        detail = cancel_unpaid_order(db, order_id, user)
        db.commit()
        return detail.model_dump(mode='json')
    results = race(pg_engine, owner, [payment(invoice_id, '25'), cancel])
    assert sorted(status for status, _ in results) == [200, 409]
    with Session(pg_engine) as db:
        order = db.get(Order, order_id)
        invoice = db.get(CommercialInvoice, invoice_id)
        snapshot = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order_id))
        if order.status == 'cancelled':
            assert invoice.status == 'cancelled' and invoice.paid_amount == 0 and snapshot.successful_payment_count == 0
            assert db.scalar(select(func.count()).select_from(SimulatedPayment)) == 0
        else:
            assert order.status == 'awaiting_payment' and invoice.status == 'partially_paid'
            assert invoice.paid_amount == Decimal('25') and snapshot.successful_payment_count == 1
