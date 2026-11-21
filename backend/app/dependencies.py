from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Session, User, UserRole
from app.services.auth_service import get_active_session
from app.services.security import constant_time_compare


def verify_trusted_origin(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforces that state-changing requests come from a strictly trusted browser origin."""
    origin = request.headers.get('origin')
    if not origin or origin.lower() == 'null':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'UNTRUSTED_ORIGIN', 'message': 'Origin header is absent, null, or untrusted.'},
        )

    normalized_origin = origin.rstrip('/')
    trusted_origins = [o.rstrip('/') for o in settings.allowed_origins]

    if normalized_origin not in trusted_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'UNTRUSTED_ORIGIN', 'message': 'Origin is not allowed.'},
        )


def get_current_session(
    request: Request,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Session:
    """Validates the session token or cookie and returns an active, unexpired database session."""
    session_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token_candidate = auth_header.split(' ', 1)[1].strip()
        if token_candidate:
            session_id = token_candidate

    if not session_id:
        session_id = request.cookies.get(settings.session_cookie_name)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'code': 'UNAUTHENTICATED', 'message': 'Authentication required.'},
        )

    session = get_active_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'code': 'UNAUTHENTICATED', 'message': 'Session is invalid, expired, or deactivated.'},
        )

    return session


def get_current_user(
    session: Session = Depends(get_current_session),
) -> User:
    """Returns the authenticated User owning the current active session."""
    return session.user


def verify_csrf_token(
    request: Request,
    session: Session = Depends(get_current_session),
) -> Session:
    """Enforces session-bound CSRF token verification for authenticated mutations."""
    csrf_header = request.headers.get('X-CSRF-Token')
    if not csrf_header or not constant_time_compare(csrf_header, session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'INVALID_CSRF_TOKEN', 'message': 'CSRF token is missing or invalid.'},
        )
    return session


def require_role(*allowed_roles: UserRole) -> Callable:
    """Role-guard dependency factory that enforces RBAC on endpoints."""
    role_values = {r.value if isinstance(r, UserRole) else r for r in allowed_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_val = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
        if user_role_val not in role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={'code': 'FORBIDDEN', 'message': 'You do not have permission to access this portal.'},
            )
        return current_user

    return role_checker


require_customer = require_role(UserRole.CUSTOMER)
require_employee = require_role(UserRole.EMPLOYEE)
require_admin = require_role(UserRole.ADMIN)
