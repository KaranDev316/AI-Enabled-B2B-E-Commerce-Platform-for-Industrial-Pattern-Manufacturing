"""Migration 006 → 007 against an explicitly isolated localhost PostgreSQL schema."""
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.models import User, RFQ, Quotation, Order


def test_s08_upgrade_preserves_rfq_and_quotation_records():
    raw=os.getenv('S07_POSTGRES_TEST_URL')
    if not raw:
        pytest.skip('Set S07_POSTGRES_TEST_URL to a dedicated localhost *_test PostgreSQL database.')
    url=make_url(raw)
    assert url.host in ('127.0.0.1','localhost') and url.database.endswith('_test')
    schema='s08_migration_'+uuid4().hex
    root=create_engine(url)
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA {schema}'))
    scoped=url.set(query={**url.query,'options':f'-csearch_path={schema}'})
    env={**os.environ,'DATABASE_URL':scoped.render_as_string(hide_password=False)}
    engine=create_engine(scoped)
    backend=Path(__file__).resolve().parents[1]
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','006'],cwd=backend,env=env,check=True,capture_output=True)
        with Session(engine) as db:
            user=User(email='migration@s08.test',password_hash='fixture-only',role='customer',is_active=True)
            db.add(user);db.flush()
            rfq=RFQ(rfq_number='RFQ-MIGRATION',customer_id=user.id,title='Retained pattern',material='Wood',quantity=2)
            db.add(rfq);db.flush()
            quote=Quotation(rfq_id=rfq.id,version=1,created_by=user.id,tax_percent=0,subtotal=0,tax_amount=0,total=0)
            db.add(quote)
            legacy=Order(order_number='LEGACY-S08-RETAIN',customer_id=user.id,rfq_id=rfq.id,total_amount='1234.56',status='pending_payment')
            db.add(legacy);db.commit()
            user_id,rfq_id,quote_id,order_id=user.id,rfq.id,quote.id,legacy.id
        subprocess.run([sys.executable,'-m','alembic','upgrade','007'],cwd=backend,env=env,check=True,capture_output=True)
        with Session(engine) as db:
            assert db.get(RFQ,rfq_id).title=='Retained pattern'
            assert db.get(Quotation,quote_id).rfq_id==rfq_id
            assert db.get(User,user_id).email=='migration@s08.test'
            retained=db.get(Order,order_id)
            assert retained.order_number=='LEGACY-S08-RETAIN' and str(retained.total_amount)=='1234.56'
            assert retained.status=='pending_payment'
            assert db.scalar(text('SELECT version_num FROM alembic_version'))=='007'
            schema_info=inspect(db.connection())
            assert {'invoices','order_commercial_snapshots','order_status_events'} <= set(schema_info.get_table_names())
            gstin=next(c for c in schema_info.get_columns('invoices') if c['name']=='customer_gstin_snapshot')
            assert gstin['type'].length==50
            assert any(fk['referred_table']=='quotations' for fk in schema_info.get_foreign_keys('order_commercial_snapshots'))
            assert any(i['column_names']==['quotation_id'] and i['unique'] for i in schema_info.get_indexes('order_commercial_snapshots'))
            assert any(i['column_names']==['order_id'] and i['unique'] for i in schema_info.get_indexes('invoices'))
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        root.dispose()
