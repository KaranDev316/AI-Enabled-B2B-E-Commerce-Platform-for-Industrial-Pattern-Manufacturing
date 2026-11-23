"""007 → 008 retains the issued invoice and enables the constrained payment ledger."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import Order, User
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, OrderStatusEvent, SimulatedPayment
from app.schemas.commercial import SimulatedPaymentRequest
from app.services.commercial_service import create_order_and_invoice_atomic
from app.services.payment_service import record_simulated_payment


def test_s09_upgrade_preserves_invoice_and_enforces_payment_constraints():
    raw = os.getenv('S07_POSTGRES_TEST_URL')
    if not raw:
        pytest.skip('Set S07_POSTGRES_TEST_URL to an isolated localhost *_test database.')
    url = make_url(raw)
    assert url.host in ('127.0.0.1', 'localhost') and url.database.endswith('_test')
    schema = 's09_migration_' + uuid4().hex
    root = create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    scoped = url.set(query={**url.query, 'options': f'-csearch_path={schema}'})
    env = {**os.environ, 'DATABASE_URL': scoped.render_as_string(hide_password=False)}
    engine = create_engine(scoped)
    backend = Path(__file__).resolve().parents[1]
    try:
        def upgrade(target):
            subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', target], cwd=backend, env=env, check=True, capture_output=True)
        upgrade('007')
        with Session(engine) as db:
            user = User(email='migration@s09.test', password_hash='fixture-only', role='customer', is_active=True)
            db.add(user); db.flush()
            order, _, invoice = create_order_and_invoice_atomic(db, customer_id=user.id, customer_name='Retained Foundry',
                product_summary='Retained pattern', items=[{'description':'Retained tooling', 'quantity':1, 'unit_price':'100.00'}], tax_rate_percent=0)
            db.commit()
            order_id, invoice_id, user_id, snapshot = order.id, invoice.id, user.id, invoice.items_snapshot_json
        upgrade('008')
        upgrade('head')
        with Session(engine) as db:
            invoice = db.get(CommercialInvoice, invoice_id)
            assert invoice.items_snapshot_json == snapshot and invoice.total_amount == 100 and invoice.paid_amount == 0
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == '009'
            info = inspect(db.connection())
            assert any(item['column_names'] == ['idempotency_key'] for item in info.get_unique_constraints('simulated_payments'))
            checks = {item['name'] for item in info.get_check_constraints('simulated_payments')}
            assert {'ck_simulated_payment_positive', 'ck_simulated_payment_outcome'} <= checks
            assert {fk['referred_table'] for fk in info.get_foreign_keys('simulated_payments')} == {'users', 'invoices'}
            failed_payload = SimulatedPaymentRequest(amount='10', outcome='failed', idempotency_key=uuid4())
            failed = record_simulated_payment(db, invoice_id, db.get(User, user_id), failed_payload)
            paid_payload = SimulatedPaymentRequest(amount='100', idempotency_key=uuid4())
            result = record_simulated_payment(db, invoice_id, db.get(User, user_id), paid_payload)
            assert result.outcome == 'succeeded'
            assert db.get(CommercialInvoice, invoice_id).items_snapshot_json == snapshot
        # New connections after a repeated migration must retain both outcomes and
        # return the original attempts, without another ledger row/confirmation.
        engine.dispose()
        upgrade('head')
        with Session(engine) as db:
            assert record_simulated_payment(db, invoice_id, db.get(User, user_id), failed_payload) == failed
            assert record_simulated_payment(db, invoice_id, db.get(User, user_id), paid_payload) == result
            invoice = db.get(CommercialInvoice, invoice_id)
            assert invoice.items_snapshot_json == snapshot
            assert invoice.paid_amount == 100 and invoice.status == 'paid'
            assert db.get(Order, order_id).status == 'confirmed'
            assert db.scalar(select(func.count()).select_from(SimulatedPayment)) == 2
            assert db.scalar(select(func.count()).select_from(OrderStatusEvent).where(
                OrderStatusEvent.order_id == order_id,
                OrderStatusEvent.event_type == 'order_confirmed')) == 1
            retained = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order_id))
            assert retained.paid_amount == 100 and retained.successful_payment_count == 1
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        root.dispose()
