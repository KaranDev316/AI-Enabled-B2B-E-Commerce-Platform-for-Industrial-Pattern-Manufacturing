"""S08 integration against the actual create_app routes and persisted quotations."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import Base, get_db
from app.models import User, CustomerProfile
from app.services.security import hash_password
from app.models import RFQ, Quotation, Order, Product
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot

ORIGIN = 'http://127.0.0.1:5173'


def sign_in(client, role='customer'):
    names = {'customer': ('customer.one', 'Customer'), 'other': ('customer.two', 'Customer'),
             'admin': ('admin.one', 'Admin'), 'employee': ('employee.one', 'Employee')}
    email, password = names[role]
    response = client.post('/api/auth/login', json={'email': email+'@example.test', 'password': password+'@12345'}, headers={'Origin': ORIGIN})
    assert response.status_code == 200
    return {'Origin': ORIGIN, 'X-CSRF-Token': response.json()['csrf_token']}


def create_offer(client, product_id=None):
    customer = sign_in(client)
    rfq = client.post('/api/rfqs', json={'title':'Engine core box', 'rfq_type':'standard' if product_id else 'custom', 'product_id':product_id, 'material':'Wood', 'quantity':3}, headers=customer).json()
    admin = sign_in(client, 'admin')
    quote = client.post(f"/api/admin/rfqs/{rfq['id']}/quotations", json={
        'expected_version':0, 'items':[{'description':'Tooling', 'quantity':3, 'unit_price':'10.05'}, {'description':'Drawing review', 'quantity':1, 'unit_price':'0.00'}],
        'tax_percent':'18.00', 'lead_time_days':12,
    }, headers=admin).json()
    sent = client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision':quote['revision']}, headers=admin)
    assert sent.status_code == 200, sent.text
    return sent.json()


@pytest.fixture
def offer(client, test_users, db_session):
    product=Product(name='Core box',slug='s08-core-box',material_type='Wood',indicative_price=999,is_active=True)
    db_session.add(product);db_session.commit()
    return create_offer(client,product.id)


def test_accept_once_real_app_snapshot_access_and_cancellation(client, offer, db_session, test_users):
    customer = sign_in(client)
    endpoint = f"/api/quotations/{offer['id']}/accept"
    first = client.post(endpoint, headers=customer)
    assert first.status_code == 200, first.text
    ids = first.json()
    assert client.post(endpoint, headers=customer).json() == ids
    assert db_session.query(Order).count() == db_session.query(CommercialInvoice).count() == 1
    quote = db_session.get(Quotation, offer['id'])
    assert quote.status == 'accepted'
    order = client.get(f"/api/orders/{ids['order_id']}").json()
    invoice = client.get(f"/api/invoices/{ids['invoice_id']}").json()
    assert order['status'] == 'awaiting_payment' and order['production_status'] is None
    assert order['quantity'] == 3
    assert order['quotation_id'] == quote.id and order['rfq_id'] == offer['rfq_id']
    assert invoice['subtotal_amount'] == offer['subtotal']
    assert invoice['tax_rate_percent'] == offer['tax_percent']
    assert invoice['tax_amount'] == offer['tax_amount']
    assert invoice['total_amount'] == offer['total']
    assert invoice['items'][0]['line_total'] == offer['items'][0]['amount']
    profile = test_users['customer_1'].customer_profile
    old_company = profile.company_name
    profile.company_name = 'Edited after acceptance'
    source=db_session.get(RFQ, offer['rfq_id'])
    source.title='Edited requirement'
    product=db_session.get(Product,source.product_id)
    product.name='Renamed catalogue pattern'
    product.indicative_price=Decimal('99999.99')
    product.is_active=False
    db_session.commit()
    retained=client.get(f"/api/invoices/{ids['invoice_id']}").json()
    assert retained['customer_name']==old_company
    assert retained['total_amount']==offer['total'] and retained['tax_amount']==offer['tax_amount']
    assert client.get(f"/api/orders/{ids['order_id']}").json()['product_summary'] == 'Engine core box'
    assert client.get(f"/api/invoices/{ids['invoice_id']}/download").status_code == 200
    other = sign_in(client, 'other')
    assert client.get('/api/orders').json() == []
    assert client.get('/api/invoices').json() == []
    assert client.get(f"/api/orders/{ids['order_id']}").status_code == 403
    assert client.get(f"/api/invoices/{ids['invoice_id']}/download").status_code == 403
    assert client.post(endpoint, headers=other).status_code == 404
    sign_in(client, 'admin')
    assert len(client.get('/api/orders').json()) == len(client.get('/api/invoices').json()) == 1
    assert client.get(f"/api/invoices/{ids['invoice_id']}/download").status_code == 200
    customer = sign_in(client)
    cancelled = client.post(f"/api/orders/{ids['order_id']}/cancel", json={'reason':'Project postponed'}, headers=customer)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['order']['status'] == 'cancelled'
    assert cancelled.json()['order']['invoice']['status'] == 'cancelled'
    assert [e['event_type'] for e in cancelled.json()['order']['status_history']] == ['order_created', 'order_cancelled']
    assert client.post(endpoint, headers=customer).json() == ids
    assert db_session.query(Order).count() == 1


@pytest.mark.parametrize('state', ['draft', 'expired', 'superseded', 'rejected'])
def test_ineligible_acceptance_creates_no_commercial_records(client, offer, db_session, state):
    if state == 'superseded':
        admin = sign_in(client, 'admin')
        assert client.post(f"/api/admin/rfqs/{offer['rfq_id']}/quotations", json={'expected_version':1}, headers=admin).status_code == 201
    else:
        record = db_session.get(Quotation, offer['id'])
        if state == 'expired':
            record.valid_until = datetime.now(timezone.utc)-timedelta(seconds=1)
        else:
            record.status = state
        db_session.commit()
    customer = sign_in(client)
    assert client.post(f"/api/quotations/{offer['id']}/accept", headers=customer).status_code == 409
    assert db_session.query(Order).count() == db_session.query(CommercialInvoice).count() == 0


def test_acceptance_csrf_origin_roles_and_accepted_immutability(client, offer):
    endpoint = f"/api/quotations/{offer['id']}/accept"
    customer = sign_in(client)
    assert client.post(endpoint, headers={'Origin':ORIGIN}).status_code == 403
    assert client.post(endpoint, headers={**customer,'Origin':'https://untrusted.example'}).status_code == 403
    admin = sign_in(client, 'admin')
    assert client.post(endpoint, headers=admin).status_code == 403
    employee = sign_in(client, 'employee')
    assert client.post(endpoint, headers=employee).status_code == 403
    customer = sign_in(client)
    assert client.post(endpoint, headers=customer).status_code == 200
    admin = sign_in(client, 'admin')
    assert client.post(f"/api/admin/rfqs/{offer['rfq_id']}/quotations", json={'expected_version':1}, headers=admin).status_code == 409
    assert client.put(f"/api/admin/quotations/{offer['id']}", json={'expected_revision':offer['revision']}, headers=admin).status_code == 409


def test_invoice_insert_failure_rolls_back_acceptance_and_order(tmp_path):
    # Independent committed transactions: the shared test fixture's outer rollback
    # would erase its setup as well, masking the actual request boundary.
    engine = create_engine(f'sqlite:///{tmp_path / "rollback.db"}', connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        customer=User(email='customer.one@example.test',password_hash=hash_password('Customer@12345'),role='customer',is_active=True)
        admin=User(email='admin.one@example.test',password_hash=hash_password('Admin@12345'),role='admin',is_active=True)
        db.add_all([customer,admin]);db.flush()
        db.add(CustomerProfile(user_id=customer.id,company_name='Test Foundry',contact_person='Test',phone='0000000000'));db.commit()
    app=create_app()
    def isolated_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db]=isolated_db
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        offer=create_offer(client)
        customer=sign_in(client)
        def fail_invoice(*args):
            raise RuntimeError('Simulated invoice persistence failure')
        event.listen(CommercialInvoice,'before_insert',fail_invoice)
        try:
            with pytest.raises(RuntimeError,match='Simulated invoice'):
                client.post(f"/api/quotations/{offer['id']}/accept",headers=customer)
        finally:
            event.remove(CommercialInvoice,'before_insert',fail_invoice)
        with Session(engine) as db:
            assert db.get(Quotation,offer['id']).status=='sent'
            assert db.query(Order).count()==db.query(OrderCommercialSnapshot).count()==db.query(CommercialInvoice).count()==0
        assert client.post(f"/api/quotations/{offer['id']}/accept",headers=customer).status_code==200
    engine.dispose()


@pytest.mark.parametrize('order_status,payment_count,paid', [('confirmed',0,'0.00'),('awaiting_payment',1,'0.00'),('awaiting_payment',0,'1.00')])
def test_cancellation_checks_status_and_both_settlement_guards(client, offer, db_session, order_status, payment_count, paid):
    customer=sign_in(client)
    ids=client.post(f"/api/quotations/{offer['id']}/accept",headers=customer).json()
    order=db_session.get(Order,ids['order_id'])
    snapshot=db_session.query(OrderCommercialSnapshot).filter_by(order_id=order.id).one()
    order.status=order_status
    snapshot.successful_payment_count=payment_count
    snapshot.paid_amount=Decimal(paid)
    db_session.commit()
    response=client.post(f'/api/orders/{order.id}/cancel',json={'reason':'Controlled fixture'},headers=customer)
    assert response.status_code==409
    assert db_session.get(Order,order.id).status==order_status
    assert db_session.get(CommercialInvoice,ids['invoice_id']).status=='unpaid'


def test_invoice_download_failure_is_retryable_without_mutating_snapshot(client, offer, db_session, monkeypatch):
    customer=sign_in(client)
    ids=client.post(f"/api/quotations/{offer['id']}/accept",headers=customer).json()
    import app.api.invoices as invoice_api
    original=invoice_api.render_demo_invoice_html
    def fail_download(detail):
        raise RuntimeError('Simulated generation failure')
    monkeypatch.setattr(invoice_api,'render_demo_invoice_html',fail_download)
    endpoint=f"/api/invoices/{ids['invoice_id']}/download"
    failed=client.get(endpoint)
    assert failed.status_code==503 and failed.json()['detail']['code']=='INVOICE_DOWNLOAD_UNAVAILABLE'
    assert db_session.query(CommercialInvoice).count()==1
    assert db_session.get(CommercialInvoice,ids['invoice_id']).total_amount==Decimal(offer['total'])
    monkeypatch.setattr(invoice_api,'render_demo_invoice_html',original)
    assert client.get(endpoint).status_code==200
