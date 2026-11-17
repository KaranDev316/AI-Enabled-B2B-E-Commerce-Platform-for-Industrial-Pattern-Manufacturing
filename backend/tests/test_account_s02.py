import pytest

from app.models import Session as DBSessionModel, User, UserRole

TRUSTED_ORIGIN = 'http://127.0.0.1:5173'


def test_s02_customer_registration_success(client, db_session):
    """REQ-01 / AC-01-01: Valid customer registration creates exactly one user and customer profile."""
    reg_payload = {
        'email': 'new.buyer@foundrycorp.in',
        'password': 'SecureBuyerPass123!',
        'company_name': 'Foundry Corp India',
        'contact_person': 'Anil Sharma',
        'phone': '+919988776655',
        'gstin': '24AABCF1234F1Z1',
        'address': 'Phase 4, GIDC Naroda, Ahmedabad',
    }
    res = client.post(
        '/api/auth/register',
        json=reg_payload,
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data['email'] == 'new.buyer@foundrycorp.in'
    assert data['role'] == UserRole.CUSTOMER.value
    assert data['is_active'] is True
    assert data['must_change_password'] is False
    assert data['customer_profile']['company_name'] == 'Foundry Corp India'
    assert data['customer_profile']['gstin'] == '24AABCF1234F1Z1'

    # Now verify customer can log in
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'new.buyer@foundrycorp.in', 'password': 'SecureBuyerPass123!'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert login_res.status_code == 200
    assert 'kpc_session' in login_res.cookies


def test_s02_duplicate_registration_conflict(client, test_users):
    """REQ-01 / AC-01-02: Duplicate registration returns 409 Conflict without creating orphan profiles."""
    reg_payload = {
        'email': 'customer.one@example.test',  # Already exists
        'password': 'AnotherPassword123!',
        'company_name': 'Duplicate Testing Ltd',
        'contact_person': 'Ramesh',
        'phone': '+919876543219',
    }
    res = client.post(
        '/api/auth/register',
        json=reg_payload,
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 409
    assert res.json()['detail']['code'] == 'EMAIL_ALREADY_EXISTS'


def test_s02_role_tampering_on_registration_fails(client):
    """REQ-01 / AC-01-02: Visitor cannot supply privileged role on registration."""
    reg_payload = {
        'email': 'hacker@attacker.test',
        'password': 'Password12345!',
        'company_name': 'Attacker Corp',
        'contact_person': 'Hacker',
        'phone': '+919999999999',
        'role': 'admin',  # Attempt privilege escalation
    }
    res = client.post(
        '/api/auth/register',
        json=reg_payload,
        headers={'Origin': TRUSTED_ORIGIN},
    )
    # Pydantic extra='forbid' rejects unknown fields with 422
    assert res.status_code == 422


def test_s02_admin_creates_employee_and_employee_can_login(client, test_users, db_session):
    """REQ-04 / AC-01-07: Admin provisions an employee; employee can sign in."""
    # 1. Sign in as Admin
    admin_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    admin_csrf = admin_login.json()['csrf_token']

    # 2. Provision new employee
    emp_payload = {
        'email': 'tooling.tech@kpc.com',
        'password': 'TempEmployeePass123!',
        'full_name': 'Kishan Dave',
        'department': 'CAD Tooling & CNC Machining',
        'phone': '+919812345678',
    }
    emp_res = client.post(
        '/api/admin/users/employee',
        json=emp_payload,
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': admin_csrf},
    )
    assert emp_res.status_code == 201
    emp_data = emp_res.json()
    assert emp_data['email'] == 'tooling.tech@kpc.com'
    assert emp_data['role'] == UserRole.EMPLOYEE.value
    assert emp_data['must_change_password'] is True
    assert emp_data['employee_profile']['full_name'] == 'Kishan Dave'

    # 3. New employee logs in
    client.cookies.clear()
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'tooling.tech@kpc.com', 'password': 'TempEmployeePass123!'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert login_res.status_code == 200
    assert login_res.json()['user']['must_change_password'] is True


def test_s02_customer_cannot_create_employee(client, test_users):
    """REQ-04 / AC-01-07: Customer cannot create employees or access admin routes."""
    # Sign in as Customer
    cust_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    cust_csrf = cust_login.json()['csrf_token']

    emp_payload = {
        'email': 'unauthorized.emp@kpc.com',
        'password': 'TempEmployeePass123!',
        'full_name': 'Unauthorized',
    }
    res = client.post(
        '/api/admin/users/employee',
        json=emp_payload,
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': cust_csrf},
    )
    assert res.status_code == 403


def test_s02_admin_deactivation_immediately_revokes_sessions(client, test_users, db_session):
    """REQ-04 / AC-01-04: Admin deactivates account -> active sessions are purged and denied immediately."""
    # 1. Customer signs in in client A (session established)
    cust_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.two@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    cust_cookie = cust_login.cookies.get('kpc_session')
    user_id = cust_login.json()['user']['id']
    assert cust_cookie is not None

    # Verify session is in DB
    assert db_session.get(DBSessionModel, cust_cookie) is not None

    # 2. Admin signs in in client B and deactivates Customer Two
    client.cookies.clear()
    admin_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    admin_csrf = admin_login.json()['csrf_token']

    deact_res = client.patch(
        f'/api/admin/users/{user_id}/status',
        json={'is_active': False},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': admin_csrf},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()['is_active'] is False

    # 3. Check Customer Two's session in DB: MUST BE PURGED
    assert db_session.get(DBSessionModel, cust_cookie) is None

    # 4. Customer Two tries to call protected endpoint with old cookie
    client.cookies.clear()
    client.cookies.set('kpc_session', cust_cookie)
    me_res = client.get('/api/auth/me')
    assert me_res.status_code == 401


def test_s02_admin_password_reset_revokes_sessions_and_forces_change(client, test_users, db_session):
    """REQ-04 / AC-01-08: Admin password reset invalidates existing sessions and forces password update."""
    # 1. Employee signs in
    emp_login = client.post(
        '/api/auth/login',
        json={'email': 'employee.one@example.test', 'password': 'Employee@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    emp_cookie = emp_login.cookies.get('kpc_session')
    user_id = emp_login.json()['user']['id']

    # 2. Admin resets employee password
    client.cookies.clear()
    admin_login = client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    admin_csrf = admin_login.json()['csrf_token']

    reset_res = client.post(
        f'/api/admin/users/{user_id}/reset-password',
        json={'new_password': 'AdminGeneratedResetPass99!'},
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': admin_csrf},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()['must_change_password'] is True

    # 3. Pre-reset session is revoked
    client.cookies.clear()
    client.cookies.set('kpc_session', emp_cookie)
    assert client.get('/api/auth/me').status_code == 401

    # 4. Employee signs in with new password
    login_new = client.post(
        '/api/auth/login',
        json={'email': 'employee.one@example.test', 'password': 'AdminGeneratedResetPass99!'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert login_new.status_code == 200
    assert login_new.json()['user']['must_change_password'] is True


def test_s02_self_profile_update(client, test_users):
    """REQ-03 / AC-01-06: Valid self-profile updates persist and survive reload."""
    # 1. Customer updates business profile
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    update_payload = {
        'company_name': 'Apex Advanced Castings Ltd',
        'contact_person': 'Rajesh V. Patel',
        'phone': '+919876599999',
        'gstin': '24AAACA9999A1Z9',
        'address': 'Plot 44, GIDC Vatva Phase II, Ahmedabad',
    }
    patch_res = client.patch(
        '/api/profile/me',
        json=update_payload,
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert patch_res.status_code == 200
    prof = patch_res.json()['customer_profile']
    assert prof['company_name'] == 'Apex Advanced Castings Ltd'
    assert prof['gstin'] == '24AAACA9999A1Z9'

    # Verify GET /api/profile/me reflects update
    get_res = client.get('/api/profile/me')
    assert get_res.status_code == 200
    assert get_res.json()['customer_profile']['company_name'] == 'Apex Advanced Castings Ltd'


def test_s02_self_password_change(client, test_users):
    """REQ-03 / AC-01-06: User changes own password; enforces fresh sign in with new credentials."""
    login_res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    csrf_token = login_res.json()['csrf_token']

    # Change password
    change_res = client.post(
        '/api/auth/change-password',
        json={
            'current_password': 'Customer@12345',
            'new_password': 'BrandNewCustomerPass99!',
        },
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert change_res.status_code == 200

    # Old password no longer works
    fail_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert fail_login.status_code == 401

    # New password authenticates successfully
    success_login = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'BrandNewCustomerPass99!'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert success_login.status_code == 200
