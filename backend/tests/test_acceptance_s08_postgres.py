"""Real PostgreSQL races; reuse the guarded disposable-schema fixture."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_quotations_s07_postgres import pg_engine
from app.api.quotations import accept_quote, create_draft
from app.models import User, CustomerProfile, RFQ, Quotation, QuotationItem, Order
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, OrderStatusEvent
from app.schemas.quotation import QuoteCreateInput
from app.services.commercial_service import cancel_unpaid_order


def seed(engine):
    with Session(engine) as db:
        customer=User(email='owner@s08.test',password_hash='fixture-only',role='customer',is_active=True)
        admin=User(email='admin@s08.test',password_hash='fixture-only',role='admin',is_active=True)
        db.add_all([customer,admin]);db.flush()
        db.add(CustomerProfile(user_id=customer.id,company_name='Test Foundry',contact_person='Test',phone='0000000000'))
        rfq=RFQ(rfq_number='RFQ-RACE',customer_id=customer.id,title='Core box',material='Wood',quantity=3)
        db.add(rfq);db.flush()
        quote=Quotation(rfq_id=rfq.id,version=1,revision=2,status='sent',pricing_source='manual',
                        created_by=admin.id,tax_percent=Decimal('18.00'),subtotal=Decimal('30.15'),
                        tax_amount=Decimal('5.43'),total=Decimal('35.58'),lead_time_days=12,sent_at=datetime.now(timezone.utc),
                        items=[QuotationItem(position=0,description='Core box',quantity=3,unit_price=Decimal('10.05'),amount=Decimal('30.15'))])
        db.add(quote);db.commit()
        return customer.id,admin.id,rfq.id,quote.id


def test_concurrent_acceptance_returns_same_records(pg_engine):
    customer_id,_,_,quote_id=seed(pg_engine)
    barrier=Barrier(2)
    def attempt(_):
        with Session(pg_engine) as db:
            user=db.get(User,customer_id)
            barrier.wait(timeout=10)
            return accept_quote(quote_id,user,db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(attempt,range(2)))
    assert results[0] == results[1]
    with Session(pg_engine) as db:
        assert len(list(db.scalars(select(Order)))) == len(list(db.scalars(select(CommercialInvoice)))) == 1
        assert db.get(Quotation,quote_id).status == 'accepted'
        assert db.scalar(select(CommercialInvoice)).total_amount == Decimal('35.58')


def test_acceptance_and_revision_share_one_parent_lock(pg_engine):
    customer_id,admin_id,rfq_id,quote_id=seed(pg_engine)
    barrier=Barrier(2)
    def attempt(action):
        with Session(pg_engine) as db:
            user=db.get(User,customer_id if action=='accept' else admin_id)
            barrier.wait(timeout=10)
            try:
                if action=='accept':
                    accept_quote(quote_id,user,db)
                else:
                    create_draft(rfq_id,QuoteCreateInput(expected_version=1),user,db)
                return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt,['accept','revise'])) == [200,409]
    with Session(pg_engine) as db:
        quotes=list(db.scalars(select(Quotation).order_by(Quotation.version)))
        orders=list(db.scalars(select(Order)))
        invoices=list(db.scalars(select(CommercialInvoice)))
        if orders:
            assert len(quotes)==len(orders)==len(invoices)==1
            assert quotes[0].status=='accepted'
        else:
            assert len(quotes)==2 and quotes[0].status=='superseded' and quotes[1].status=='draft'
            assert invoices==[]


def test_duplicate_cancellation_has_one_history_event(pg_engine):
    customer_id,_,_,quote_id=seed(pg_engine)
    with Session(pg_engine) as db:
        ids=accept_quote(quote_id,db.get(User,customer_id),db)
    barrier=Barrier(2)
    def attempt(_):
        with Session(pg_engine) as db:
            user=db.get(User,customer_id)
            barrier.wait(timeout=10)
            try:
                cancel_unpaid_order(db,ids['order_id'],user)
                db.commit()
                return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt,range(2)))==[200,200]  # retry returns saved state
    with Session(pg_engine) as db:
        assert db.get(Order,ids['order_id']).status=='cancelled'
        assert db.get(CommercialInvoice,ids['invoice_id']).status=='cancelled'
        assert len(list(db.scalars(select(OrderStatusEvent).where(OrderStatusEvent.event_type=='order_cancelled'))))==1
