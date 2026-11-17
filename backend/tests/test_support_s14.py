import pytest

from app.models import Order, TicketStatus, TicketType, UserRole

TRUSTED_ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture
def sample_orders(db_session, test_users) -> dict[str, Order]:
    """Provisions test orders for customer.one and customer.two."""
    c1 = test_users['customer_1']
    c2 = test_users['customer_2']

    ord1 = Order(
        order_number='ORD-2026-0001',
        customer_id=c1.id,
        total_amount=15000.0,
        status='in_production',
    )
    ord2 = Order(
        order_number='ORD-2026-0002',
        customer_id=c2.id,
        total_amount=28500.0,
        status='pending_payment',
    )
    db_session.add_all([ord1, ord2])
    db_session.commit()
    db_session.refresh(ord1)
    db_session.refresh(ord2)
    return {'order_c1': ord1, 'order_c2': ord2}


def test_s14_create_inquiry_ticket_success(client, test_users):
    """REQ-30 / AC-09-01: Customer creates valid inquiry ticket without related order."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    res = client.post(
        '/api/support/tickets',
        json={
            'ticket_type': 'inquiry',
            'subject': 'Inquiry regarding pattern shrink allowance guidelines',
            'message': 'We require guidance on pattern draft angles for heavy grey-iron casting.',
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 201
    ticket = res.json()
    assert ticket['ticket_number'].startswith('TICK-')
    assert ticket['ticket_type'] == 'inquiry'
    assert ticket['subject'] == 'Inquiry regarding pattern shrink allowance guidelines'
    assert ticket['status'] == 'open'
    assert len(ticket['messages']) == 1
    assert ticket['messages'][0]['sender_role'] == 'customer'
    assert 'grey-iron' in ticket['messages'][0]['message']


def test_s14_create_complaint_with_own_order(client, test_users, sample_orders):
    """REQ-30 / AC-09-01: Customer creates complaint linked to their own order."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']
    own_order_id = sample_orders['order_c1'].id

    res = client.post(
        '/api/support/tickets',
        json={
            'ticket_type': 'complaint',
            'subject': 'Dimension variance on core print delivery',
            'message': 'The delivered pattern core print exhibits a 1.2mm deviation from specifications.',
            'order_id': own_order_id,
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 201
    data = res.json()
    assert data['order_id'] == own_order_id
    assert data['order_number'] == 'ORD-2026-0001'
    assert data['ticket_type'] == 'complaint'


def test_s14_reject_unrelated_order_and_invalid_fields(client, test_users, sample_orders):
    """REQ-30 / AC-09-02: Reject linking another customer's order or empty/short fields."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']
    other_order_id = sample_orders['order_c2'].id

    # 1. Attempt to link Customer 2's order
    res_other = client.post(
        '/api/support/tickets',
        json={
            'ticket_type': 'complaint',
            'subject': 'Dispute regarding unowned invoice',
            'message': 'Testing access control with unowned order linkage.',
            'order_id': other_order_id,
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_other.status_code == 400
    assert 'Cannot link ticket to an order that does not belong to your account' in res_other.json()['detail']

    # 2. Attempt with too short subject
    res_short = client.post(
        '/api/support/tickets',
        json={'ticket_type': 'inquiry', 'subject': 'Hi', 'message': 'Valid message body here.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_short.status_code == 422


def test_s14_multiturn_conversation_and_chronology(client, test_users):
    """REQ-31 / AC-09-03: Chronological customer & admin messaging with role attribution."""
    # 1. Customer creates ticket
    c_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c_csrf = c_login.json()['csrf_token']

    res = client.post(
        '/api/support/tickets',
        json={
            'ticket_type': 'technical_support',
            'subject': 'STEP file coordinate alignment issue',
            'message': 'Initial question: Does your CNC intake require origin offset at center?',
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c_csrf},
    )
    ticket_id = res.json()['id']

    # 2. Admin logs in and replies
    a_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    a_csrf = a_login.json()['csrf_token']

    reply_res1 = client.post(
        f'/api/support/tickets/{ticket_id}/messages',
        json={'message': 'Yes, please align coordinate origin at the centroid of the base flange.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': a_csrf},
    )
    assert reply_res1.status_code == 201
    assert reply_res1.json()['sender_role'] == 'admin'

    # Verify status auto-advanced from open to in_progress
    detail_res1 = client.get(f'/api/support/tickets/{ticket_id}')
    assert detail_res1.json()['status'] == 'in_progress'

    # 3. Customer logs back in and provides follow-up
    c_login2 = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c_csrf2 = c_login2.json()['csrf_token']

    reply_res2 = client.post(
        f'/api/support/tickets/{ticket_id}/messages',
        json={'message': 'Thank you! We will update CAD model origin accordingly.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c_csrf2},
    )
    assert reply_res2.status_code == 201
    assert reply_res2.json()['sender_role'] == 'customer'

    # 4. Verify conversation thread has 3 messages strictly ordered
    thread = client.get(f'/api/support/tickets/{ticket_id}').json()['messages']
    assert len(thread) == 3
    assert thread[0]['sender_role'] == 'customer'
    assert thread[1]['sender_role'] == 'admin'
    assert thread[2]['sender_role'] == 'customer'


def test_s14_tenant_isolation_and_employee_restriction(client, test_users):
    """REQ-31 / AC-09-04: Customer B and Employees cannot view or contribute to Customer A's ticket."""
    # 1. Customer 1 creates ticket
    c1_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c1_csrf = c1_login.json()['csrf_token']
    res = client.post(
        '/api/support/tickets',
        json={'ticket_type': 'inquiry', 'subject': 'Confidential casting inquiry', 'message': 'Private specs.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    ticket_id = res.json()['id']

    # 2. Customer 2 logs in
    c2_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.two@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c2_csrf = c2_login.json()['csrf_token']

    # Customer 2 attempts to read Customer 1's ticket -> 403
    res_c2_read = client.get(f'/api/support/tickets/{ticket_id}')
    assert res_c2_read.status_code == 403

    # Customer 2 attempts to reply -> 403
    res_c2_reply = client.post(
        f'/api/support/tickets/{ticket_id}/messages',
        json={'message': 'Intruder message'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c2_csrf},
    )
    assert res_c2_reply.status_code == 403

    # 3. Employee logs in
    e_login = client.post(
        '/api/auth/login',
        json={'email': 'employee.one@example.test', 'password': 'Employee@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    e_csrf = e_login.json()['csrf_token']

    # Employee attempts to read customer support ticket -> 403
    res_e_read = client.get(f'/api/support/tickets/{ticket_id}')
    assert res_e_read.status_code == 403

    # Employee attempts to reply -> 403
    res_e_reply = client.post(
        f'/api/support/tickets/{ticket_id}/messages',
        json={'message': 'Employee unauthorized reply'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': e_csrf},
    )
    assert res_e_reply.status_code == 403


def test_s14_admin_status_management_and_closed_reply_blocking(client, test_users):
    """REQ-32 / AC-09-05 / AC-09-06: Admin manages lifecycle; closed ticket blocks replies."""
    # 1. Customer creates ticket
    c_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c_csrf = c_login.json()['csrf_token']
    res = client.post(
        '/api/support/tickets',
        json={'ticket_type': 'inquiry', 'subject': 'Status lifecycle test', 'message': 'Testing resolution flow.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c_csrf},
    )
    ticket_id = res.json()['id']

    # 2. Customer attempts to change status -> 403 Forbidden
    res_c_status = client.patch(
        f'/api/admin/support/tickets/{ticket_id}/status',
        json={'status': 'resolved'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c_csrf},
    )
    assert res_c_status.status_code == 403

    # 3. Admin updates status to resolved
    a_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    a_csrf = a_login.json()['csrf_token']

    res_resolve = client.patch(
        f'/api/admin/support/tickets/{ticket_id}/status',
        json={'status': 'resolved'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': a_csrf},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()['status'] == 'resolved'

    # 4. Attempt to reply to resolved ticket -> 400 Bad Request
    res_reply_blocked = client.post(
        f'/api/support/tickets/{ticket_id}/messages',
        json={'message': 'Trying to reply to a resolved ticket'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': a_csrf},
    )
    assert res_reply_blocked.status_code == 400
    assert 'Cannot reply to a resolved ticket' in res_reply_blocked.json()['detail']

    # 5. Admin updates status to closed
    res_close = client.patch(
        f'/api/admin/support/tickets/{ticket_id}/status',
        json={'status': 'closed'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': a_csrf},
    )
    assert res_close.status_code == 200
    assert res_close.json()['status'] == 'closed'


def test_s14_support_attachments_upload_and_download(client, test_users):
    """REQ-30 / REQ-31 / AC-09-02 / AC-09-04: Attachments handling, format allowlist, and boundaries."""
    # 1. Customer creates ticket
    c1_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    c1_csrf = c1_login.json()['csrf_token']
    res = client.post(
        '/api/support/tickets',
        json={'ticket_type': 'order_issue', 'subject': 'Surface defect issue', 'message': 'See attached defect photos.'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    ticket_id = res.json()['id']

    # 2. Upload valid PNG image
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
    upload_res1 = client.post(
        f'/api/support/tickets/{ticket_id}/files',
        files={'file': ('defect_photo1.png', png_bytes, 'image/png')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    assert upload_res1.status_code == 201
    file_id1 = upload_res1.json()['id']
    assert upload_res1.json()['file_name'] == 'defect_photo1.png'
    assert upload_res1.json()['is_previewable'] is True

    # 3. Reject disallowed format (e.g. .step or .exe)
    step_bytes = b'ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n'
    upload_res_disallowed = client.post(
        f'/api/support/tickets/{ticket_id}/files',
        files={'file': ('model.step', step_bytes, 'application/step')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    assert upload_res_disallowed.status_code == 400
    assert 'Support attachments only permit JPG, PNG, and PDF' in upload_res_disallowed.json()['detail']

    # 4. Upload valid PDF
    pdf_bytes = b'%PDF-1.4\n1 0 obj\n<< /Title (Inspection Report) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
    upload_res2 = client.post(
        f'/api/support/tickets/{ticket_id}/files',
        files={'file': ('inspection_report.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    assert upload_res2.status_code == 201

    # 5. Exceed max 2 attachments limit
    upload_res3 = client.post(
        f'/api/support/tickets/{ticket_id}/files',
        files={'file': ('extra_photo.png', png_bytes, 'image/png')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': c1_csrf},
    )
    assert upload_res3.status_code == 400
    assert 'Maximum limit of 2 attachments reached' in upload_res3.json()['detail']

    # 6. Customer 1 retrieves file
    dl_res = client.get(f'/api/support/tickets/{ticket_id}/files/{file_id1}?disposition=inline')
    assert dl_res.status_code == 200
    assert dl_res.headers['content-type'] == 'image/png'
    assert dl_res.content == png_bytes

    # 7. Customer 2 tries to download Customer 1's attachment -> 403
    client.post(
        '/api/auth/login',
        json={'email': 'customer.two@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    dl_c2 = client.get(f'/api/support/tickets/{ticket_id}/files/{file_id1}')
    assert dl_c2.status_code == 403
