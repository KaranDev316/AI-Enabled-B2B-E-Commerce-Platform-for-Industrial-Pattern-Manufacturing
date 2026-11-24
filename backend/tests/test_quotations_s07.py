from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.models import RFQ, Quotation

ORIGIN = 'http://127.0.0.1:5173'


def login(client, role='admin'):
    names = {'admin': ('admin.one', 'Admin'), 'customer': ('customer.one', 'Customer'),
             'other': ('customer.two', 'Customer'), 'employee': ('employee.one', 'Employee')}
    email, password = names[role]
    response = client.post('/api/auth/login', json={'email': email + '@example.test', 'password': password + '@12345'}, headers={'Origin': ORIGIN})
    assert response.status_code == 200, response.text
    return {'Origin': ORIGIN, 'X-CSRF-Token': response.json()['csrf_token']}


@pytest.fixture
def rfq(db_session, test_users):
    record = RFQ(rfq_number='RFQ-S07', customer_id=test_users['customer_1'].id,
                 title='Casting pattern', material='Wood', quantity=2, rfq_type='custom')
    db_session.add(record)
    db_session.commit()
    return record


def draft(client, rfq, headers, version=0, **overrides):
    payload = {'expected_version': version, 'items': [{'description': 'Tooling', 'quantity': 3, 'unit_price': '10.05'}],
               'tax_percent': '18', 'lead_time_days': 12, **overrides}
    response = client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def send(client, quote, headers):
    response = client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': quote['revision']}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_manual_lifecycle_money_and_change_request(client, rfq, db_session):
    admin = login(client)
    quote = draft(client, rfq, admin)
    assert quote['pricing_source'] == 'manual' and quote['estimation_id'] is None
    assert Decimal(quote['subtotal']) == Decimal('30.15')
    assert Decimal(quote['tax_amount']) == Decimal('5.43')
    assert Decimal(quote['total']) == Decimal('35.58')
    customer = login(client, 'customer')
    assert client.get(f'/api/rfqs/{rfq.id}/quotations').json() == []
    admin = login(client)
    quote = send(client, quote, admin)
    customer = login(client, 'customer')
    response = client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'request_changes', 'message': 'Please shorten the lead time'}, headers=customer)
    assert response.status_code == 201, response.text
    assert response.json()['total'] == quote['total']
    assert response.json()['status'] == 'sent'
    admin = login(client)
    history = client.get(f'/api/admin/rfqs/{rfq.id}/quotations').json()
    assert history[0]['decisions'][0]['message'] == 'Please shorten the lead time'
    revised = draft(client, rfq, admin, version=1, lead_time_days=8)
    assert revised['version'] == 2
    customer = login(client, 'customer')
    old = client.get(f'/api/rfqs/{rfq.id}/quotations').json()[0]
    assert old['status'] == 'superseded' and not old['can_respond']
    assert old['total'] == quote['total']
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'reject', 'message': 'Stale'}, headers=customer).status_code == 409
    admin = login(client)
    revised = send(client, revised, admin)
    customer = login(client, 'customer')
    assert client.post(f"/api/quotations/{revised['id']}/decisions", json={'action': 'reject', 'message': 'Budget exceeded'}, headers=customer).json()['status'] == 'rejected'
    assert client.get(f'/api/rfqs/{rfq.id}').json()['status'] == 'rejected'
    admin = login(client)
    assert client.get(f'/api/admin/rfqs/{rfq.id}/quotations').json()[0]['decisions'][0]['action'] == 'reject'


def test_owner_roles_csrf_and_no_acceptance(client, rfq):
    admin = login(client)
    quote = send(client, draft(client, rfq, admin), admin)
    other = login(client, 'other')
    assert client.get(f'/api/rfqs/{rfq.id}/quotations').status_code == 404
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'reject', 'message': 'No'}, headers=other).status_code == 404
    customer = login(client, 'customer')
    assert client.get(f'/api/admin/rfqs/{rfq.id}/quotations').status_code == 403
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'reject', 'message': 'No'}).status_code == 403
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'accept', 'message': 'Yes'}, headers=customer).status_code == 422
    login(client, 'employee')
    assert client.get(f'/api/rfqs/{rfq.id}/quotations').status_code == 403


def test_incomplete_expired_and_stale_draft(client, rfq, db_session):
    admin = login(client)
    quote = draft(client, rfq, admin, items=[], lead_time_days=None)
    assert client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': 1}, headers=admin).status_code == 422
    payload = {'items': [{'description': 'Pattern', 'quantity': 1, 'unit_price': '100.00'}], 'lead_time_days': 10, 'expected_revision': 1}
    updated = client.put(f"/api/admin/quotations/{quote['id']}", json=payload, headers=admin)
    assert updated.status_code == 200
    assert client.put(f"/api/admin/quotations/{quote['id']}", json=payload, headers=admin).status_code == 409
    quote = send(client, updated.json(), admin)
    assert client.put(f"/api/admin/quotations/{quote['id']}", json={**payload, 'expected_revision': quote['revision']}, headers=admin).status_code == 409
    db_session.get(Quotation, quote['id']).valid_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    customer = login(client, 'customer')
    assert client.get(f'/api/rfqs/{rfq.id}/quotations').json()[0]['status'] == 'expired'
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'request_changes', 'message': 'Change'}, headers=customer).status_code == 409


def test_version_conflict_and_accepted_immutable(client, rfq, db_session):
    admin = login(client)
    quote = draft(client, rfq, admin)
    response = client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json={'expected_version': 0}, headers=admin)
    assert response.status_code == 409
    assert len(client.get(f'/api/admin/rfqs/{rfq.id}/quotations').json()) == 1
    record = db_session.get(Quotation, quote['id'])
    record.status = 'accepted'  # Seed future S08 state: S07 must preserve it.
    db_session.commit()
    assert client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json={'expected_version': 1}, headers=admin).status_code == 409
    assert client.put(f"/api/admin/quotations/{quote['id']}", json={'expected_revision': 1}, headers=admin).status_code == 409
    assert client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': 1}, headers=admin).status_code == 409


@pytest.mark.parametrize('field,value', [('tax_percent','100.01'), ('tax_percent','NaN'), ('lead_time_days',0), ('items',[{'description':' ', 'quantity':1,'unit_price':'1'}]), ('items',[{'description':'X','quantity':0,'unit_price':'1'}]), ('items',[{'description':'X','quantity':1,'unit_price':'1.001'}])])
def test_invalid_values(client, rfq, field, value):
    admin = login(client)
    response = client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json={'expected_version':0, field:value}, headers=admin)
    assert response.status_code == 422, response.text


def test_send_completeness_and_private_superseded_draft(client, rfq):
    admin = login(client)
    quote = draft(client, rfq, admin, items=[{'description': 'Tooling', 'quantity': 1, 'unit_price': '0'}])
    assert client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': 1}, headers=admin).status_code == 422
    quote = draft(client, rfq, admin, version=1, valid_until=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': 1}, headers=admin).status_code == 422
    login(client, 'customer')
    assert client.get(f'/api/rfqs/{rfq.id}/quotations').json() == []


def test_untrusted_origin_and_manual_provenance_cannot_be_overridden(client, rfq):
    admin = login(client)
    endpoint = f'/api/admin/rfqs/{rfq.id}/quotations'
    assert client.post(endpoint, json={'expected_version': 0}, headers={**admin, 'Origin': 'https://untrusted.example'}).status_code == 403
    for supplied in ({'pricing_source': 'ai'}, {'estimation_id': 123}, {'total': '0.01'}):
        assert client.post(endpoint, json={'expected_version': 0, **supplied}, headers=admin).status_code == 422


def test_customer_submission_becomes_linked_quote_after_admin_review(client, test_users, db_session):
    customer = login(client, 'customer')
    submitted = client.post('/api/rfqs', json={
        'title': 'Customer engine core box', 'rfq_type': 'custom', 'material': 'Mahogany Wood',
        'quantity': 7, 'dimensions': '200 x 100 mm', 'specifications': 'Draft angle 2 degrees',
        'notes': 'Review drawing before manufacture',
    }, headers=customer)
    assert submitted.status_code == 201, submitted.text
    rfq_id = submitted.json()['id']
    admin = login(client)
    reviewed = client.patch(f'/api/admin/rfqs/{rfq_id}/status', json={'status': 'under_review'}, headers=admin)
    assert reviewed.status_code == 200, reviewed.text
    response = client.post(f'/api/admin/rfqs/{rfq_id}/quotations', json={'expected_version': 0, 'from_rfq': True}, headers=admin)
    assert response.status_code == 201, response.text
    quote = response.json()
    assert quote['rfq_id'] == rfq_id
    assert quote['items'] == [{'description': 'Customer engine core box', 'quantity': 7, 'unit_price': '0.00', 'amount': '0.00'}]
    assert quote['lead_time_days'] is None and Decimal(quote['total']) == 0
    assert db_session.query(RFQ).count() == 1  # No duplicate request.
    source = db_session.get(RFQ, rfq_id)
    assert (source.material, source.quantity, source.specifications) == ('Mahogany Wood', 7, 'Draft angle 2 degrees')
    assert client.post(f"/api/admin/quotations/{quote['id']}/send", json={'expected_revision': quote['revision']}, headers=admin).status_code == 422
    saved = client.put(f"/api/admin/quotations/{quote['id']}", json={
        'expected_revision': quote['revision'], 'items': [{'description': quote['items'][0]['description'], 'quantity': 7, 'unit_price': '100.00'}],
        'lead_time_days': 10,
    }, headers=admin)
    assert saved.status_code == 200, saved.text
    issued = send(client, saved.json(), admin)
    assert Decimal(issued['total']) == Decimal('700.00')
    login(client, 'customer')
    offers = client.get(f'/api/rfqs/{rfq_id}/quotations').json()
    assert offers[0]['id'] == quote['id'] and offers[0]['items'][0]['quantity'] == 7


def test_blank_creation_and_revision_remain_explicit(client, rfq):
    admin = login(client)
    first = draft(client, rfq, admin, items=[])
    assert first['items'] == []
    mixed = client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json={'expected_version': 1, 'from_rfq': True}, headers=admin)
    assert mixed.status_code == 422
    revised = draft(client, rfq, admin, version=1)
    assert revised['items'][0]['description'] == 'Tooling'
    assert revised['rfq_id'] == rfq.id


def test_revision_after_customer_rejection_preserves_history(client, rfq, db_session):
    admin = login(client)
    quote = send(client, draft(client, rfq, admin), admin)
    customer = login(client, 'customer')
    assert client.post(f"/api/quotations/{quote['id']}/decisions", json={'action': 'reject', 'message': 'Too costly'}, headers=customer).status_code == 201
    admin = login(client)
    revised = draft(client, rfq, admin, version=1)
    assert revised['version'] == 2 and revised['status'] == 'draft'
    assert client.get(f'/api/rfqs/{rfq.id}').json()['status'] == 'under_review'
    history = client.get(f'/api/admin/rfqs/{rfq.id}/quotations').json()
    assert history[1]['status'] == 'rejected' and history[1]['decisions'][0]['message'] == 'Too costly'
    assert history[1]['total'] == quote['total']
    issued = send(client, revised, admin)
    login(client, 'customer')
    visible = client.get(f'/api/rfqs/{rfq.id}/quotations').json()
    assert visible[0]['id'] == issued['id'] and visible[0]['can_respond']
    assert visible[1]['status'] == 'rejected' and not visible[1]['can_respond']
    assert visible[1]['items'] == quote['items']


def test_admin_rejected_rfq_still_requires_reopening(client, rfq, db_session):
    rfq.status = 'rejected'
    db_session.commit()
    admin = login(client)
    response = client.post(f'/api/admin/rfqs/{rfq.id}/quotations', json={'expected_version': 0}, headers=admin)
    assert response.status_code == 409


def test_retried_identical_change_request_is_saved_once(client, rfq):
    admin = login(client)
    quote = send(client, draft(client, rfq, admin), admin)
    customer = login(client, 'customer')
    body = {'action': 'request_changes', 'message': 'Shorter lead time please'}
    for _ in range(2):
        response = client.post(f"/api/quotations/{quote['id']}/decisions", json=body, headers=customer)
        assert response.status_code == 201, response.text
    assert len(response.json()['decisions']) == 1
    assert response.json()['total'] == quote['total']
