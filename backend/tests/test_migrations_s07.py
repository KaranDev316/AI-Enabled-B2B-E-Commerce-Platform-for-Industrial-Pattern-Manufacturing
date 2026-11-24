"""Run the actual S07 migration chain and retain quotation history on reconnect."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import RFQ, Quotation, QuotationDecision, QuotationItem, User


def test_s07_migrations_retain_quotation_items_and_rejected_history():
    raw = os.getenv('S07_POSTGRES_TEST_URL')
    if not raw:
        pytest.skip('Set S07_POSTGRES_TEST_URL to an isolated localhost *_test database.')
    url = make_url(raw)
    assert url.host in ('127.0.0.1', 'localhost') and url.database.endswith('_test')
    schema = 's07_migration_' + uuid4().hex
    root = create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    scoped = url.set(query={**url.query, 'options': f'-csearch_path={schema}'})
    env = {**os.environ, 'DATABASE_URL': scoped.render_as_string(hide_password=False)}
    engine = create_engine(scoped)
    backend = Path(__file__).resolve().parents[1]
    def upgrade(target):
        subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', target], cwd=backend,
                       env=env, check=True, capture_output=True)
    try:
        for revision in ('001', '002', '003', '004', '005', '006'):
            upgrade(revision)
        with Session(engine) as db:
            admin = User(email='admin@s07.test', password_hash='fixture-only', role='admin', is_active=True)
            customer = User(email='owner@s07.test', password_hash='fixture-only', role='customer', is_active=True)
            db.add_all([admin, customer]); db.flush()
            rfq = RFQ(rfq_number='RFQ-MIGRATION-S07', customer_id=customer.id, title='Retained pattern', material='Wood', quantity=2)
            db.add(rfq); db.flush()
            quote = Quotation(rfq_id=rfq.id, version=1, revision=2, created_by=admin.id, status='rejected',
                tax_percent=18, subtotal=100, tax_amount=18, total=118, lead_time_days=10)
            quote.items = [QuotationItem(position=0, description='Retained tooling', quantity=2, unit_price=50, amount=100)]
            quote.decisions = [QuotationDecision(customer_id=customer.id, action='reject', message='Revise lead time')]
            db.add(quote); db.commit()
            quote_id = quote.id
        engine.dispose()
        upgrade('006')
        with Session(engine) as db:
            retained = db.get(Quotation, quote_id)
            assert retained.status == 'rejected' and retained.revision == 2
            assert retained.total == 118 and retained.tax_amount == 18
            assert retained.items[0].description == 'Retained tooling' and retained.items[0].amount == 100
            assert retained.decisions[0].message == 'Revise lead time'
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == '006'
            info = inspect(db.connection())
            assert any(c['column_names'] == ['rfq_id', 'version'] for c in info.get_unique_constraints('quotations'))
            assert {'ck_quotation_status', 'ck_quotation_manual_source', 'ck_quotation_versions'} <= {
                c['name'] for c in info.get_check_constraints('quotations')}
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        root.dispose()
