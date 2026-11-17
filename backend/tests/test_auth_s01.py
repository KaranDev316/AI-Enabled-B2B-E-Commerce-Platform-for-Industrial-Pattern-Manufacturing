from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Session as DBSessionModel, UserRole
from app.services.security import hash_password, verify_password

TRUSTED_ORIGIN = 'http://127.0.0.1:5173'
UNTRUSTED_ORIGIN = 'http://untrusted.attacker.test'


def test_s01_v21_argon2id_hashing():
    """Verify password hashing produces valid Argon2id hash and verifies correctly."""
    raw = 'SecurePassword123!'
    hashed = hash_password(raw)
    assert hashed.startswith('$argon2id$')
    assert len(hashed) <= 255
    assert verify_password(raw, hashed) is True
    assert verify_password('WrongPassword', hashed) is False
    assert verify_password('', hashed) is False


def test_s01_v01_successful_login_and_me(client, test_users):
    """S01-V01: Customer, Employee, Admin can log in and retrieve own session identity."""
    for email, password, expected_role in [
        ('customer.one@example.test', 'Customer@12345', UserRole.CUSTOMER.value),
        ('employee.one@example.test', 'Employee@12345', UserRole.EMPLOYEE.value),
        ('admin.one@example.test', 'Admin@12345', UserRole.ADMIN.value),
    ]:
        res = client.post(
            '/api/auth/login',
            json={'email': email, 'password': password},
            headers={'Origin': TRUSTED_ORIGIN},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data['user']['email'] == email
        assert data['user']['role'] == expected_role
        assert 'csrf_token' in data
        assert len(data['csrf_token']) > 20

        # Verify HttpOnly cookie is set
        assert 'kpc_session' in res.cookies
        cookie_header = res.headers.get('set-cookie', '')
        assert 'httponly' in cookie_header.lower()
        assert 'samesite=lax' in cookie_header.lower()

        # Call /api/auth/me using the cookie
        me_res = client.get('/api/auth/me')
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data['user']['email'] == email
        assert me_data['user']['role'] == expected_role
        assert me_data['csrf_token'] == data['csrf_token']


def test_s01_v02_generic_login_failures(client, test_users):
    """S01-V02: Wrong password, nonexistent user, and inactive user return identical generic 401."""
    cases = [
        ('customer.one@example.test', 'WrongPassword123'),  # Wrong password
        ('nonexistent@example.test', 'AnyPassword123'),     # Nonexistent user
        ('inactive.user@example.test', 'Inactive@12345'),   # Inactive account
    ]
    for email, password in cases:
        res = client.post(
            '/api/auth/login',
            json={'email': email, 'password': password},
            headers={'Origin': TRUSTED_ORIGIN},
        )
        assert res.status_code == 401
        data = res.json()
        assert data['detail']['code'] == 'INVALID_CREDENTIALS'
        assert data['detail']['message'] == 'Invalid email or password.'
        assert 'kpc_session' not in res.cookies


def test_s01_v03_malformed_login_request(client):
    """S01-V03: Missing or malformed login input gives structured 422 feedback."""
    # Missing password
    res = client.post(
        '/api/auth/login',
        json={'email': 'test@example.com'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 422

    # Malformed email
    res2 = client.post(
        '/api/auth/login',
        json={'email': 'not-an-email', 'password': 'pass'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res2.status_code == 422


def test_s01_v04_exact_password_matching(client, test_users):
    """S01-V04: Password must match exactly without silent trimming."""
    # Valid password with added whitespace
    res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': ' Customer@12345 '},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 401


def test_s01_v05_client_cannot_forge_role(client, test_users):
    """S01-V05: Extra role claim in body is forbidden or ignored; role remains authentic."""
    res = client.post(
        '/api/auth/login',
        json={
            'email': 'customer.one@example.test',
            'password': 'Customer@12345',
            'role': 'admin',  # Attempt privilege escalation
        },
        headers={'Origin': TRUSTED_ORIGIN},
    )
    # Extra fields are forbidden by Pydantic extra='forbid' -> 422
    assert res.status_code == 422


def test_s01_v06_unauthenticated_requests(client):
    """S01-V06: Protected endpoint without cookie returns 401."""
    client.cookies.clear()
    res = client.get('/api/auth/me')
    assert res.status_code == 401
    assert res.json()['detail']['code'] == 'UNAUTHENTICATED'


def test_s01_v07_portal_role_guards(client, test_users):
    """S01-V07: Enforce role-based access for Customer, Employee, and Admin portals."""
    # 1. Customer login
    client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert client.get('/api/customer/workspace').status_code == 200
    assert client.get('/api/employee/workspace').status_code == 403
    assert client.get('/api/admin/workspace').status_code == 403

    # 2. Employee login
    client.post(
        '/api/auth/login',
        json={'email': 'employee.one@example.test', 'password': 'Employee@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert client.get('/api/customer/workspace').status_code == 403
    assert client.get('/api/employee/workspace').status_code == 200
    assert client.get('/api/admin/workspace').status_code == 403

    # 3. Admin login
    client.post(
        '/api/auth/login',
        json={'email': 'admin.one@example.test', 'password': 'Admin@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert client.get('/api/customer/workspace').status_code == 403
    assert client.get('/api/employee/workspace').status_code == 403
    assert client.get('/api/admin/workspace').status_code == 200


def test_s01_v08_session_rotation_on_login(client, test_users, db_session):
    """S01-V08: Logging in with an existing session rotates and replaces the session ID."""
    login_1 = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    session_1 = login_1.cookies.get('kpc_session')
    assert session_1 is not None

    # Re-login with the same client
    login_2 = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    session_2 = login_2.cookies.get('kpc_session')
    assert session_2 is not None
    assert session_1 != session_2

    # Old session is deleted in database
    old_db_session = db_session.get(DBSessionModel, session_1)
    assert old_db_session is None

    # New session exists and works
    new_db_session = db_session.get(DBSessionModel, session_2)
    assert new_db_session is not None


def test_s01_v09_session_expiry(client, test_users, db_session):
    """S01-V09: Server rejects and purges expired sessions."""
    res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    session_id = res.cookies.get('kpc_session')

    # Manually expire the session in DB
    db_session_obj = db_session.get(DBSessionModel, session_id)
    db_session_obj.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    # Access /api/auth/me with expired session
    me_res = client.get('/api/auth/me')
    assert me_res.status_code == 401
    assert me_res.json()['detail']['code'] == 'UNAUTHENTICATED'

    # Verify session is cleaned up
    assert db_session.get(DBSessionModel, session_id) is None


def test_s01_v10_logout_and_revocation(client, test_users, db_session):
    """S01-V10: Valid logout revokes server session, clears cookie, and invalidates replay."""
    res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    session_id = res.cookies.get('kpc_session')
    csrf_token = res.json()['csrf_token']

    logout_res = client.post(
        '/api/auth/logout',
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert logout_res.status_code == 200

    # Cookie is cleared
    assert logout_res.cookies.get('kpc_session') in (None, '')
    set_cookie = logout_res.headers.get('set-cookie', '').lower()
    assert 'max-age=0' in set_cookie or 'kpc_session=""' in set_cookie

    # Session in DB is deleted
    assert db_session.get(DBSessionModel, session_id) is None

    # Replay old cookie
    client.cookies.set('kpc_session', session_id)
    assert client.get('/api/auth/me').status_code == 401


def test_s01_v11_logout_twice_safe(client, test_users):
    """S01-V11: Logging out twice or with invalid session does not crash."""
    client.cookies.clear()
    res = client.post(
        '/api/auth/logout',
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 200
    assert res.json()['message'] == 'Logged out successfully'


def test_s01_v12_origin_enforcement_on_login(client, test_users):
    """S01-V12: Origin checks on mutation endpoints reject absent, null, or untrusted origins."""
    payload = {'email': 'customer.one@example.test', 'password': 'Customer@12345'}

    # 1. Trusted origin succeeds
    res_trusted = client.post('/api/auth/login', json=payload, headers={'Origin': TRUSTED_ORIGIN})
    assert res_trusted.status_code == 200

    # 2. Untrusted origin rejected
    res_untrusted = client.post('/api/auth/login', json=payload, headers={'Origin': UNTRUSTED_ORIGIN})
    assert res_untrusted.status_code == 403
    assert res_untrusted.json()['detail']['code'] == 'UNTRUSTED_ORIGIN'

    # 3. Absent origin rejected
    res_absent = client.post('/api/auth/login', json=payload)
    assert res_absent.status_code == 403

    # 4. Null origin rejected
    res_null = client.post('/api/auth/login', json=payload, headers={'Origin': 'null'})
    assert res_null.status_code == 403


def test_s01_v13_v14_csrf_and_origin_enforcement_on_logout(client, test_users, db_session):
    """S01-V13/V14: Untrusted origin or missing/bad CSRF on logout leaves session intact."""
    res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    session_id = res.cookies.get('kpc_session')
    csrf_token = res.json()['csrf_token']

    # Untrusted origin on logout -> 403, session NOT revoked
    bad_origin_res = client.post(
        '/api/auth/logout',
        headers={'Origin': UNTRUSTED_ORIGIN, 'X-CSRF-Token': csrf_token},
    )
    assert bad_origin_res.status_code == 403
    assert db_session.get(DBSessionModel, session_id) is not None

    # Missing CSRF token on logout -> 403, session NOT revoked
    no_csrf_res = client.post(
        '/api/auth/logout',
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert no_csrf_res.status_code == 403
    assert db_session.get(DBSessionModel, session_id) is not None

    # Invalid CSRF token on logout -> 403, session NOT revoked
    bad_csrf_res = client.post(
        '/api/auth/logout',
        headers={'Origin': TRUSTED_ORIGIN, 'X-CSRF-Token': 'wrong-csrf-token'},
    )
    assert bad_csrf_res.status_code == 403
    assert db_session.get(DBSessionModel, session_id) is not None


def test_s01_v17_user_deactivation_stops_session(client, test_users, db_session):
    """S01-V17: User marked inactive is immediately denied on subsequent requests."""
    res = client.post(
        '/api/auth/login',
        json={'email': 'customer.one@example.test', 'password': 'Customer@12345'},
        headers={'Origin': TRUSTED_ORIGIN},
    )
    assert res.status_code == 200

    # Deactivate the user in DB
    user = test_users['customer_1']
    user.is_active = False
    db_session.commit()

    # Next request must be rejected
    me_res = client.get('/api/auth/me')
    assert me_res.status_code == 401
