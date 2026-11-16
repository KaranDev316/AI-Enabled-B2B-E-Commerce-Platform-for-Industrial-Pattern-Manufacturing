import pytest

from app.models import Category, Product, RFQ, RFQStatus, RFQType, UserRole

TRUSTED_ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture
def sample_product(db_session) -> Product:
    cat = Category(name='Cast Patterns', description='Standard foundry patterns')
    db_session.add(cat)
    db_session.flush()

    prod = Product(
        category_id=cat.id,
        name='Standard Cast Iron Flange Pattern',
        slug='standard-cast-iron-flange-pattern',
        material_type='Cast Iron Grade 20',
        indicative_price=24000.00,
        is_active=True,
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod


def test_s05_custom_rfq_submission_success(client, test_users):
    """REQ-08 / AC-03-01: Customer submits a Custom industrial pattern RFQ."""
    # 1. Login as Customer 1
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # 2. Submit Custom RFQ
    rfq_payload = {
        'title': 'High-Pressure Turbine Housing Pattern',
        'rfq_type': 'custom',
        'material': 'Teak Wood & Epoxy Coating',
        'quantity': 2,
        'description': 'Two-piece split pattern with core prints for steam turbine casing sand casting.',
        'dimensions': '850mm x 600mm x 450mm',
        'specifications': 'Machining allowance +3mm, shrinkage rate 1.5%, draft angle 1.5 deg.',
        'target_delivery_date': '2026-12-15',
        'notes': 'Urgent requirement for NTPC power plant project.',
    }

    res = client.post(
        '/api/rfqs',
        json=rfq_payload,
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data['title'] == 'High-Pressure Turbine Housing Pattern'
    assert data['rfq_type'] == 'custom'
    assert data['quantity'] == 2
    assert data['status'] == 'submitted'
    assert data['rfq_number'].startswith('RFQ-')


def test_s05_standard_rfq_submission_success(client, test_users, sample_product):
    """REQ-08 / AC-03-01: Customer submits a Standard catalogue-linked RFQ."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    rfq_payload = {
        'title': 'Standard Flange Pattern Order',
        'rfq_type': 'standard',
        'product_id': sample_product.id,
        'material': 'Cast Iron Grade 20',
        'quantity': 5,
        'description': 'Standard catalogue flange pattern requirement.',
    }

    res = client.post(
        '/api/rfqs',
        json=rfq_payload,
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data['product_id'] == sample_product.id
    assert data['rfq_type'] == 'standard'


def test_s05_rfq_validation_failures(client, test_users):
    """REQ-08 / AC-03-03: Invalid RFQ input (qty <= 0, missing product for standard, blank fields) fails."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # 1. Quantity <= 0 fails
    res_qty = client.post(
        '/api/rfqs',
        json={'title': 'Test Part', 'material': 'Wood', 'quantity': 0},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_qty.status_code == 422

    # 2. Blank whitespace title fails
    res_blank = client.post(
        '/api/rfqs',
        json={'title': '   ', 'material': 'Wood', 'quantity': 1},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_blank.status_code == 422

    # 3. Standard RFQ without product_id fails
    res_noprod = client.post(
        '/api/rfqs',
        json={'title': 'Standard Part', 'rfq_type': 'standard', 'material': 'Wood', 'quantity': 1},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_noprod.status_code == 400
    assert res_noprod.json()['detail']['code'] == 'PRODUCT_REQUIRED'


def test_s05_customer_rfq_tenant_isolation(client, test_users):
    """REQ-10 / AC-03-08: Tenant isolation - Customer A cannot view or list Customer B's RFQ."""
    # 1. Customer 1 submits RFQ 1
    c1_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c1_csrf = c1_login.json()['csrf_token']

    rfq1_res = client.post(
        '/api/rfqs',
        json={'title': 'Customer 1 Valve Pattern', 'material': 'Mahogany Wood', 'quantity': 1},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    rfq1_id = rfq1_res.json()['id']

    # 2. Customer 2 logs in
    client.cookies.clear()
    c2_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.two@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c2_csrf = c2_login.json()['csrf_token']

    # Customer 2 checks own list
    my_list_c2 = client.get('/api/rfqs/my').json()
    assert not any(item['id'] == rfq1_id for item in my_list_c2)

    # Customer 2 attempts to direct GET Customer 1's RFQ -> 403 Forbidden!
    c2_peek = client.get(f'/api/rfqs/{rfq1_id}')
    assert c2_peek.status_code == 403


def test_s05_admin_rfq_review_and_status_update(client, test_users):
    """REQ-10: Admin lists all customer RFQs and updates review status."""
    # 1. Customer 1 submits RFQ
    c1_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c1_csrf = c1_login.json()['csrf_token']

    rfq_res = client.post(
        '/api/rfqs',
        json={'title': 'Impeller Casting Pattern', 'material': 'Aluminum Alloy', 'quantity': 3},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    rfq_id = rfq_res.json()['id']

    # 2. Admin logs in
    client.cookies.clear()
    admin_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    admin_csrf = admin_login.json()['csrf_token']

    # Admin reads single RFQ details
    admin_get = client.get(f'/api/rfqs/{rfq_id}')
    assert admin_get.status_code == 200
    details = admin_get.json()
    assert details['customer_company'] == 'Apex Castings Ltd'
    assert details['title'] == 'Impeller Casting Pattern'

    # Admin lists RFQs
    admin_list = client.get('/api/admin/rfqs')
    assert admin_list.status_code == 200
    assert any(r['id'] == rfq_id for r in admin_list.json())

    # Admin transitions status to 'under_review'
    status_res = client.patch(
        f'/api/admin/rfqs/{rfq_id}/status',
        json={'status': 'under_review'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': admin_csrf},
    )
    assert status_res.status_code == 200
    assert status_res.json()['status'] == 'under_review'


def test_s05_employee_cannot_view_unassigned_rfq(client, test_users):
    """AC-03-08: Unassigned employees cannot access customer RFQ records."""
    # 1. Customer 1 submits RFQ
    c1_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    rfq_id = client.post(
        '/api/rfqs',
        json={'title': 'Confidential Prototype Pattern', 'material': 'Steel', 'quantity': 1},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_login.json()['csrf_token']},
    ).json()['id']

    # 2. Employee logs in and attempts to access
    client.cookies.clear()
    client.post(
        '/api/auth/login',
        json={'email': 'employee.one@example.test', 'password': 'Employee@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    emp_res = client.get(f'/api/rfqs/{rfq_id}')
    assert emp_res.status_code == 403
