from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import (
    get_current_session,
    get_current_user,
    verify_csrf_token,
    verify_trusted_origin,
)
from app.models import Session, User
from app.schemas.account import ChangePasswordRequest, CustomerRegisterRequest
from app.schemas.auth import LoginRequest, SessionResponse, UserResponse
from app.services.account_service import change_own_password, register_customer
from app.services.auth_service import (
    get_active_session,
    invalidate_session,
    rotate_session,
)
from app.services.security import constant_time_compare, verify_password

router = APIRouter(prefix='/api/auth', tags=['Authentication'])


@router.post(
    '/register',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin)],
)
def register(
    data: CustomerRegisterRequest,
    db: DBSession = Depends(get_db),
):
    """REQ-01: Visitor self-registers a B2B Customer account and business profile."""
    new_user = register_customer(db, data)
    return UserResponse.model_validate(new_user)


@router.post(
    '/login',
    response_model=SessionResponse,
    dependencies=[Depends(verify_trusted_origin)],
)
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Authenticates an active user, establishes a server-side session, and sets an HttpOnly cookie."""
    user = db.query(User).filter(func.lower(User.email) == func.lower(credentials.email)).first()

    if not user or not verify_password(credentials.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'code': 'INVALID_CREDENTIALS', 'message': 'Invalid email or password.'},
        )

    existing_cookie = request.cookies.get(settings.session_cookie_name)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('user-agent')

    new_session = rotate_session(
        db=db,
        old_session_id=existing_cookie,
        user=user,
        ip_address=client_ip,
        user_agent=user_agent,
    )

    response.set_cookie(
        key=settings.session_cookie_name,
        value=new_session.id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite='lax',
        secure=settings.session_secure_cookie,
        path='/',
    )

    return SessionResponse(
        user=UserResponse.model_validate(user),
        csrf_token=new_session.csrf_token,
        session_token=new_session.id,
        token=new_session.id,
        message='Authenticated successfully',
    )


@router.get('/me', response_model=SessionResponse)
def get_current_auth_state(
    session: Session = Depends(get_current_session),
):
    """Returns the authenticated user's profile and session-bound CSRF token."""
    return SessionResponse(
        user=UserResponse.model_validate(session.user),
        csrf_token=session.csrf_token,
        session_token=session.id,
        token=session.id,
        message='Active session resolved',
    )


@router.post(
    '/change-password',
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def change_password(
    data: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """REQ-03: User changes own password; invalidates previous sessions and clears cookie."""
    change_own_password(db, current_user, data.current_password, data.new_password)

    # Clear authentication cookie
    response.delete_cookie(key=settings.session_cookie_name, path='/')
    return {'message': 'Password changed successfully. Please sign in with your new password.'}


@router.post(
    '/logout',
    dependencies=[Depends(verify_trusted_origin)],
)
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Invalidates the server-side session and clears the authentication cookie."""
    session_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token_candidate = auth_header.split(' ', 1)[1].strip()
        if token_candidate:
            session_id = token_candidate

    if not session_id:
        session_id = request.cookies.get(settings.session_cookie_name)

    if session_id:
        active_session = get_active_session(db, session_id)
        if active_session:
            csrf_header = request.headers.get('X-CSRF-Token')
            if not csrf_header or not constant_time_compare(csrf_header, active_session.csrf_token):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={'code': 'INVALID_CSRF_TOKEN', 'message': 'CSRF token is missing or invalid.'},
                )
            invalidate_session(db, active_session.id)

    response.delete_cookie(
        key=settings.session_cookie_name,
        path='/',
    )
    return {'message': 'Logged out successfully'}
