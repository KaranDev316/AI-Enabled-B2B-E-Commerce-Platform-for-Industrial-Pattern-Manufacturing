from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session as DBSession

from app.models import CustomerProfile, EmployeeProfile, Session, User, UserRole
from app.schemas.account import (
    CustomerRegisterRequest,
    EmployeeCreateRequest,
    ProfileUpdateRequest,
)
from app.services.security import hash_password, verify_password


def register_customer(db: DBSession, data: CustomerRegisterRequest) -> User:
    """Atomically registers a new Customer and their corresponding CustomerProfile."""
    clean_email = data.email.strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'code': 'EMAIL_ALREADY_EXISTS', 'message': 'An account with this email address already exists.'},
        )

    # 1. Create User
    new_user = User(
        email=clean_email,
        password_hash=hash_password(data.password),
        role=UserRole.CUSTOMER.value,
        is_active=True,
        must_change_password=False,
    )
    db.add(new_user)
    db.flush()

    # 2. Create Profile
    profile = CustomerProfile(
        user_id=new_user.id,
        company_name=data.company_name.strip(),
        contact_person=data.contact_person.strip(),
        phone=data.phone.strip(),
        gstin=data.gstin.strip().upper() if data.gstin else None,
        address=data.address.strip() if data.address else None,
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)
    return new_user


def create_employee_account(db: DBSession, data: EmployeeCreateRequest) -> User:
    """Admin-only: Creates an Employee account with forced password change on next login."""
    clean_email = data.email.strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'code': 'EMAIL_ALREADY_EXISTS', 'message': 'An account with this email address already exists.'},
        )

    new_user = User(
        email=clean_email,
        password_hash=hash_password(data.password),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
        must_change_password=True,
    )
    db.add(new_user)
    db.flush()

    profile = EmployeeProfile(
        user_id=new_user.id,
        full_name=data.full_name.strip(),
        phone=data.phone.strip() if data.phone else None,
        department=data.department.strip() if data.department else None,
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)
    return new_user


def set_user_status(db: DBSession, user_id: int, is_active: bool, acting_admin: User) -> User:
    """Admin-only: Activates or deactivates an account. Immediately invalidates all sessions on deactivation."""
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'USER_NOT_FOUND', 'message': 'User does not exist.'},
        )

    # Protect against self-deactivation of the logged-in admin
    if target_user.id == acting_admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'SELF_DEACTIVATION_FORBIDDEN', 'message': 'Admin cannot deactivate their own account.'},
        )

    target_user.is_active = is_active

    # REQ-04 / AC-01-04: Immediate session invalidation on deactivation
    if not is_active:
        db.query(Session).filter(Session.user_id == target_user.id).delete()

    db.commit()
    db.refresh(target_user)
    return target_user


def reset_user_password(db: DBSession, user_id: int, new_password: str) -> User:
    """Admin-only: Resets password, invalidates all existing sessions, and sets must_change_password."""
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'USER_NOT_FOUND', 'message': 'User does not exist.'},
        )

    target_user.password_hash = hash_password(new_password)
    target_user.must_change_password = True

    # REQ-04 / AC-01-08: Pre-reset sessions immediately invalidated
    db.query(Session).filter(Session.user_id == target_user.id).delete()

    db.commit()
    db.refresh(target_user)
    return target_user


def change_own_password(
    db: DBSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """User changes their own password. Verifies current password, resets flag, and invalidates other sessions."""
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'INVALID_CURRENT_PASSWORD', 'message': 'Current password is incorrect.'},
        )

    user.password_hash = hash_password(new_password)
    user.must_change_password = False

    # REQ-03: Invalidate all existing sessions to enforce fresh login
    db.query(Session).filter(Session.user_id == user.id).delete()
    db.commit()


def update_own_profile(db: DBSession, user: User, data: ProfileUpdateRequest) -> User:
    """Allows authenticated Customer or Employee to maintain permitted profile fields."""
    user_role = user.role.value if isinstance(user.role, UserRole) else user.role

    if user_role == UserRole.CUSTOMER.value:
        profile = user.customer_profile
        if not profile:
            profile = CustomerProfile(user_id=user.id, company_name='', contact_person='', phone='')
            db.add(profile)
        if data.company_name is not None and data.company_name.strip():
            profile.company_name = data.company_name.strip()
        if data.contact_person is not None and data.contact_person.strip():
            profile.contact_person = data.contact_person.strip()
        if data.phone is not None and data.phone.strip():
            profile.phone = data.phone.strip()
        if data.gstin is not None:
            profile.gstin = data.gstin.strip().upper() if data.gstin.strip() else None
        if data.address is not None:
            profile.address = data.address.strip() if data.address.strip() else None

    elif user_role == UserRole.EMPLOYEE.value:
        profile = user.employee_profile
        if not profile:
            profile = EmployeeProfile(user_id=user.id, full_name='')
            db.add(profile)
        if data.full_name is not None and data.full_name.strip():
            profile.full_name = data.full_name.strip()
        if data.phone is not None:
            profile.phone = data.phone.strip() if data.phone.strip() else None
        # Note: Department is an employment fact set by Admin, not modified by employee
        if data.department is not None and data.department.strip():
            # Tampering rejection: employee cannot alter own department
            pass

    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: DBSession,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """Admin-only: Lists users with profiles and active session counts."""
    query = db.query(User)

    if role_filter and role_filter in ['admin', 'employee', 'customer']:
        query = query.filter(User.role == role_filter)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.outerjoin(User.customer_profile).outerjoin(User.employee_profile).filter(
            or_(
                func.lower(User.email).like(term),
                func.lower(CustomerProfile.company_name).like(term),
                func.lower(CustomerProfile.contact_person).like(term),
                func.lower(EmployeeProfile.full_name).like(term),
            )
        )

    users = query.order_by(User.id.desc()).all()
    results = []
    for u in users:
        active_sessions = db.query(Session).filter(Session.user_id == u.id).count()
        results.append({
            'user': u,
            'active_sessions_count': active_sessions,
        })
    return results
