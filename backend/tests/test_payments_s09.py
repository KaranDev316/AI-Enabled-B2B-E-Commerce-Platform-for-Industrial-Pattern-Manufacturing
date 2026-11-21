"""S09 actual-app contract: no external payment service or shared business data."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base

from app.models import Order
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, OrderStatusEvent, SimulatedPayment
from test_acceptance_s08 import offer, sign_in


@pytest.fixture
def db_session():
    # Independently committed fixtures: a service rollback must not roll back seed data.
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        yield db
    engine.dispose()


@pytest.fixture
def invoice(client, offer):
    headers = sign_in(client)
    response = client.post(f"/api/quotations/{offer['id']}/accept", headers=headers)
    assert response.status_code == 200
    return response.json()


def pay(client, invoice_id, headers, amount='10.00', outcome='succeeded', key=None, **extra):
    return client.post(f'/api/invoices/{invoice_id}/payments', headers=headers,
        json={'amount': amount, 'outcome': outcome, 'idempotency_key': key or str(uuid4()), **extra})


def test_partial_failed_final_settlement_and_download(client, invoice, db_session):
    headers = sign_in(client)
    invoice_id, order_id = invoice['invoice_id'], invoice['order_id']
    assert pay(client, invoice_id, headers, outcome='failed').status_code == 200
    detail = client.get(f'/api/invoices/{invoice_id}').json()
    assert detail['paid_amount'] == '0.00' and detail['outstanding_balance'] == '35.58'
    assert detail['payments'][0]['outcome'] == 'failed'
    assert client.get(f'/api/orders/{order_id}').json()['can_cancel'] is True
    first = pay(client, invoice_id, headers, amount='10.01')
    assert first.status_code == 200, first.text
    detail = client.get(f'/api/invoices/{invoice_id}').json()
    assert detail['status'] == 'partially_paid' and detail['outstanding_balance'] == '25.57'
    order = client.get(f'/api/orders/{order_id}').json()
    assert order['status'] == 'awaiting_payment' and not order['can_cancel'] and not order['can_assign']
    assert client.post(f'/api/orders/{order_id}/cancel', headers=headers).status_code == 409
    admin = sign_in(client, 'admin')
    assert not client.get(f'/api/orders/{order_id}').json()['can_assign']
    last = pay(client, invoice_id, admin, amount='25.57')
    assert last.status_code == 200, last.text
    detail = client.get(f'/api/invoices/{invoice_id}').json()
    assert detail['paid_amount'] == '35.58' and detail['outstanding_balance'] == '0.00' and detail['status'] == 'paid'
    order = client.get(f'/api/orders/{order_id}').json()
    assert order['status'] == 'confirmed' and order['can_assign'] and order['successful_payment_count'] == 2
    assert len([ev for ev in order['status_history'] if ev['event_type'] == 'order_confirmed']) == 1
    assert len(detail['payments']) == 3
    assert detail['total_amount'] == '35.58' and detail['tax_amount'] == '5.43'
    html = client.get(f'/api/invoices/{invoice_id}/download').text
    assert 'Simulated payment history' in html and 'Failed' in html and 'INR 35.58' in html and 'INR 0.00' in html
    assert db_session.query(CommercialInvoice).count() == 1
    owner = sign_in(client)
    assert client.get(f'/api/invoices/{invoice_id}').json() == detail
    assert pay(client, invoice_id, owner, amount='0.01').status_code == 409


def test_matching_retries_and_different_payload_conflicts(client, invoice, db_session):
    headers = sign_in(client)
    invoice_id = invoice['invoice_id']
    key = str(uuid4())
    first = pay(client, invoice_id, headers, amount='35.58', key=key)
    assert first.status_code == 200
    assert pay(client, invoice_id, headers, amount='35.580', key=key).json() == first.json()
    assert pay(client, invoice_id, headers, amount='10', key=key).status_code == 409
    assert pay(client, invoice_id, headers, amount='35.58', outcome='failed', key=key).status_code == 409
    assert db_session.query(SimulatedPayment).count() == 1
    assert db_session.query(OrderStatusEvent).filter_by(event_type='order_confirmed').count() == 1


@pytest.mark.parametrize('amount', ['0', '-1', '0.001', 'NaN', 'Infinity', '1000000000000000000.00'])
def test_invalid_amounts(client, invoice, db_session, amount):
    headers = sign_in(client)
    assert pay(client, invoice['invoice_id'], headers, amount=amount).status_code == 422
    assert db_session.query(SimulatedPayment).count() == 0


def test_overpayment_ownership_auth_csrf_origin_and_no_credentials(client, invoice, db_session):
    headers = sign_in(client)
    target = invoice['invoice_id']
    assert pay(client, target, headers, amount='35.59').status_code == 409
    assert pay(client, target, headers, card_number='should-not-be-collected').status_code == 422
    assert pay(client, target, headers, key='not-a-uuid').status_code == 422
    assert pay(client, target, headers, outcome='paid').status_code == 422
    assert pay(client, target, {'Origin': 'http://127.0.0.1:5173'}).status_code == 403
    assert pay(client, target, {**headers, 'Origin': 'https://outside.example'}).status_code == 403
    assert pay(client, target, sign_in(client, 'other')).status_code == 403
    assert pay(client, target, sign_in(client, 'employee')).status_code == 403
    client.cookies.clear()
    assert pay(client, target, headers).status_code == 401
    assert db_session.query(SimulatedPayment).count() == 0


def test_failed_attempt_allows_cancellation_and_exact_retry_after_cancel(client, invoice, db_session):
    headers = sign_in(client)
    key = str(uuid4())
    failed = pay(client, invoice['invoice_id'], headers, key=key, outcome='failed')
    assert failed.status_code == 200
    assert client.post(f"/api/orders/{invoice['order_id']}/cancel", headers=headers).status_code == 200
    assert pay(client, invoice['invoice_id'], headers).status_code == 409
    assert pay(client, invoice['invoice_id'], headers, key=key, outcome='failed').json() == failed.json()
    assert db_session.query(SimulatedPayment).count() == 1


def test_payment_rollback_then_same_key_retry(client, invoice, db_session):
    headers = sign_in(client)
    key = str(uuid4())
    def fail(_mapper, _connection, _target):
        raise RuntimeError('Injected confirmation failure')
    event.listen(OrderStatusEvent, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='Injected confirmation failure'):
            pay(client, invoice['invoice_id'], headers, amount='35.58', key=key)
    finally:
        event.remove(OrderStatusEvent, 'before_insert', fail)
    assert db_session.query(SimulatedPayment).count() == 0
    assert db_session.get(Order, invoice['order_id']).status == 'awaiting_payment'
    assert db_session.get(CommercialInvoice, invoice['invoice_id']).paid_amount == Decimal('0.00')
    assert db_session.query(OrderCommercialSnapshot).one().successful_payment_count == 0
    assert pay(client, invoice['invoice_id'], headers, amount='35.58', key=key).status_code == 200
