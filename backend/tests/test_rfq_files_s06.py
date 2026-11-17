import pytest

from app.models import Category, Product, RFQ, RFQStatus, RFQType, UserRole

TRUSTED_ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture
def sample_rfq(client, test_users, db_session) -> int:
    """Creates a sample RFQ owned by customer.one@example.test."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    res = client.post(
        '/api/rfqs',
        json={
            'title': 'Centrifugal Pump Volute Pattern',
            'rfq_type': 'custom',
            'material': 'Teak Wood',
            'quantity': 1,
            'dimensions': '500mm x 500mm x 300mm',
            'specifications': 'Machining allowance 2.5mm',
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 201
    return res.json()['id']


def test_s06_upload_valid_single_file_and_retrieve(client, test_users, sample_rfq):
    """REQ-09 / AC-03-04 / AC-03-06: Upload a valid PDF, inspect metadata, stream inline & attachment."""
    # 1. Login as owning customer
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    pdf_bytes = b'%PDF-1.4\n1 0 obj\n<< /Title (Pump Casing Blueprint) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'
    upload_res = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('pump_volute_drawing.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert upload_res.status_code == 201
    file_info = upload_res.json()
    assert file_info['file_name'] == 'pump_volute_drawing.pdf'
    assert file_info['content_type'] == 'application/pdf'
    assert file_info['file_size_bytes'] == len(pdf_bytes)
    assert file_info['can_preview'] is True
    file_id = file_info['id']

    # 2. Retrieve file list
    list_res = client.get(f'/api/rfqs/{sample_rfq}/files')
    assert list_res.status_code == 200
    files = list_res.json()
    assert len(files) == 1
    assert files[0]['id'] == file_id

    # 3. Stream inline (for browser PDF preview)
    stream_inline = client.get(f'/api/rfqs/{sample_rfq}/files/{file_id}?disposition=inline')
    assert stream_inline.status_code == 200
    assert stream_inline.headers['Content-Type'] == 'application/pdf'
    assert 'inline;' in stream_inline.headers['Content-Disposition']
    assert stream_inline.content == pdf_bytes

    # 4. Stream attachment (for file download)
    stream_attach = client.get(f'/api/rfqs/{sample_rfq}/files/{file_id}?disposition=attachment')
    assert stream_attach.status_code == 200
    assert 'attachment;' in stream_attach.headers['Content-Disposition']
    assert stream_attach.content == pdf_bytes


def test_s06_upload_two_files_including_cad_step(client, test_users, sample_rfq):
    """REQ-09 / AC-03-04: Attach exactly two files (PNG drawing + STEP 3D CAD)."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # File 1: PNG Image
    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
    res1 = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('flange_preview.png', png_bytes, 'image/png')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res1.status_code == 201
    assert res1.json()['can_preview'] is True

    # File 2: STEP CAD
    step_bytes = b'ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((\'KPC Industrial Pattern\'),\'2;1\');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n'
    res2 = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('volute_core_assembly.step', step_bytes, 'application/step')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res2.status_code == 201
    assert res2.json()['can_preview'] is False

    # Check RFQ detail now includes both files
    detail_res = client.get(f'/api/rfqs/{sample_rfq}')
    assert detail_res.status_code == 200
    assert len(detail_res.json()['files']) == 2


def test_s06_reject_third_file_max_limit(client, test_users, sample_rfq):
    """REQ-09 / AC-03-04 / AC-03-05: Reject 3rd file upload (maximum 2 allowed per RFQ)."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4'
    pdf_bytes = b'%PDF-1.4\n trailer << >> %%EOF'

    # Upload 1st file
    client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('file1.png', png_bytes, 'image/png')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    # Upload 2nd file
    client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('file2.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )

    # Attempt 3rd file
    res3 = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('file3.png', png_bytes, 'image/png')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res3.status_code == 400
    assert res3.json()['detail']['code'] == 'MAX_FILES_EXCEEDED'


def test_s06_reject_oversized_file(client, test_users, sample_rfq):
    """REQ-09 / AC-03-04: Reject file exceeding 20 MB size limit."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # 20 MB + 100 bytes
    oversized = b'%PDF-1.4\n' + b'A' * (20 * 1024 * 1024 + 100)
    res = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('huge_blueprint.pdf', oversized, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res.status_code == 400
    assert 'maximum permitted limit of 20 MB' in res.json()['detail']['message']


def test_s06_reject_disallowed_and_masquerading_files(client, test_users, sample_rfq):
    """REQ-09 / AC-03-07: Reject unsupported extensions, executable binaries, and empty files."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # 1. Disallowed extension (.exe)
    res_exe = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('malware.exe', b'MZ\x90\x00', 'application/x-msdownload')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_exe.status_code == 400
    assert res_exe.json()['detail']['code'] == 'UNSUPPORTED_FILE_TYPE'

    # 2. Masquerading Windows binary named as .step CAD
    res_masq = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('fake_cad.step', b'MZ\x90\x00some_payload', 'application/step')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_masq.status_code == 400
    assert 'prohibited' in res_masq.json()['detail']['message']

    # 3. Shell script named as .stl
    res_sh = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('script.stl', b'#!/bin/bash\necho hello', 'model/stl')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_sh.status_code == 400
    assert 'prohibited' in res_sh.json()['detail']['message']

    # 4. Empty file (0 bytes)
    res_empty = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('empty.pdf', b'', 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert res_empty.status_code == 400
    assert 'Empty files' in res_empty.json()['detail']['message']


def test_s06_tenant_isolation_unrelated_customer_blocked(client, test_users, sample_rfq):
    """REQ-09 / AC-03-06: Customer B cannot list, download, upload, or delete Customer A's files."""
    # 1. Customer A uploads a file
    login_a = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_a = login_a.json()['csrf_token']

    pdf_bytes = b'%PDF-1.4\n drawing content %%EOF'
    up_res = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('confidential_spec.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_a},
    )
    file_id = up_res.json()['id']

    # 2. Login as Customer B
    login_b = client.post(
        '/api/auth/login',
        json={'email': 'customer.two@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_b = login_b.json()['csrf_token']

    # Try listing files on Customer A's RFQ
    res_list = client.get(f'/api/rfqs/{sample_rfq}/files')
    assert res_list.status_code == 403

    # Try streaming Customer A's file
    res_stream = client.get(f'/api/rfqs/{sample_rfq}/files/{file_id}')
    assert res_stream.status_code == 403

    # Try uploading to Customer A's RFQ
    res_up = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('intruder.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_b},
    )
    assert res_up.status_code == 403

    # Try deleting Customer A's file
    res_del = client.delete(
        f'/api/rfqs/{sample_rfq}/files/{file_id}',
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_b},
    )
    assert res_del.status_code == 403


def test_s06_admin_can_inspect_and_download_customer_files(client, test_users, sample_rfq):
    """REQ-09 / AC-03-08: Admin can inspect and download Customer's CAD and PDF attachments."""
    # Customer uploads PDF
    login_cust = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_cust = login_cust.json()['csrf_token']

    pdf_bytes = b'%PDF-1.4\n technical drawing %%EOF'
    up_res = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('engine_block.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_cust},
    )
    file_id = up_res.json()['id']

    # Admin signs in
    client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )

    # Admin lists files
    list_res = client.get(f'/api/rfqs/{sample_rfq}/files')
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Admin downloads file
    dl_res = client.get(f'/api/rfqs/{sample_rfq}/files/{file_id}?disposition=attachment')
    assert dl_res.status_code == 200
    assert dl_res.content == pdf_bytes


def test_s06_unauthenticated_and_csrf_origin_checks(client, test_users, sample_rfq):
    """REQ-09: Unauthenticated blocked (401), missing CSRF or untrusted origin blocked (403)."""
    # 1. Unauthenticated download attempt (clear any existing session cookies)
    client.cookies.clear()
    res_unauth = client.get(f'/api/rfqs/{sample_rfq}/files/1')
    assert res_unauth.status_code == 401

    # Login as customer
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']
    pdf_bytes = b'%PDF-1.4\n drawing %%EOF'

    # Untrusted origin
    res_bad_origin = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('file.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': 'http://malicious-site.test', 'X-CSRF-Token': csrf_token},
    )
    assert res_bad_origin.status_code == 403

    # Missing CSRF token
    res_bad_csrf = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('file.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res_bad_csrf.status_code == 403


def test_s06_delete_file_in_submitted_status_and_block_in_under_review(client, test_users, sample_rfq):
    """REQ-09: Delete attached file in submitted state; block deletion after status moves to under_review."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    pdf_bytes = b'%PDF-1.4\n drawing %%EOF'
    up_res = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('drawing_v1.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    file_id = up_res.json()['id']

    # Delete while still 'submitted'
    del_res = client.delete(
        f'/api/rfqs/{sample_rfq}/files/{file_id}',
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert del_res.status_code == 200
    assert del_res.json()['status'] == 'deleted'

    # Verify RFQ files is now empty
    files_check = client.get(f'/api/rfqs/{sample_rfq}/files')
    assert len(files_check.json()) == 0

    # Upload new file
    up_res2 = client.post(
        f'/api/rfqs/{sample_rfq}/files',
        files={'file': ('drawing_v2.pdf', pdf_bytes, 'application/pdf')},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    file_id2 = up_res2.json()['id']

    # Admin changes RFQ status to 'under_review'
    login_admin = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    admin_csrf = login_admin.json()['csrf_token']
    client.patch(
        f'/api/admin/rfqs/{sample_rfq}/status',
        json={'status': 'under_review'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': admin_csrf},
    )

    # Customer tries to delete file2 after status is under_review -> Rejected
    login_cust2 = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    cust_csrf_new = login_cust2.json()['csrf_token']
    del_blocked = client.delete(
        f'/api/rfqs/{sample_rfq}/files/{file_id2}',
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': cust_csrf_new},
    )
    assert del_blocked.status_code == 400
    assert del_blocked.json()['detail']['code'] == 'RFQ_NOT_EDITABLE'
