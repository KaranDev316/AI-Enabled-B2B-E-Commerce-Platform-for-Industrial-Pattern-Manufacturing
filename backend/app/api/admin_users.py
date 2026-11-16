from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import (
    require_admin,
    verify_csrf_token,
    verify_trusted_origin,
)
from app.models import User
from app.schemas.account import (
    AdminResetPasswordRequest,
    AdminUserListItemResponse,
    EmployeeCreateRequest,
    UserStatusUpdateRequest,
)
from app.schemas.auth import UserResponse
from app.services.account_service import (
    create_employee_account,
    list_users,
    reset_user_password,
    set_user_status,
)

router = APIRouter(prefix='/api/admin/users', tags=['Admin User Management'])


@router.get('', response_model=list[AdminUserListItemResponse])
def get_users(
    role: Optional[str] = Query(None, description='Filter by user role'),
    search: Optional[str] = Query(None, description='Search by email or name'),
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-04: Admin lists registered Customers, Employees, and Admins."""
    user_records = list_users(db, role_filter=role, search=search)
    response_items = []
    for record in user_records:
        u = record['user']
        response_items.append(
            AdminUserListItemResponse(
                id=u.id,
                email=u.email,
                role=u.role,
                is_active=u.is_active,
                must_change_password=u.must_change_password,
                created_at=u.created_at,
                customer_profile=u.customer_profile,
                employee_profile=u.employee_profile,
                active_sessions_count=record['active_sessions_count'],
            )
        )
    return response_items


@router.post(
    '/employee',
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def create_employee(
    data: EmployeeCreateRequest,
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-04: Admin provisions a new Employee account."""
    new_employee = create_employee_account(db, data)
    return UserResponse.model_validate(new_employee)


@router.patch(
    '/{user_id}/status',
    response_model=UserResponse,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def update_user_status(
    user_id: int,
    data: UserStatusUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-04 / AC-01-04: Admin activates/deactivates user; deactivation immediately revokes sessions."""
    updated = set_user_status(db, user_id, data.is_active, acting_admin=current_admin)
    return UserResponse.model_validate(updated)


@router.post(
    '/{user_id}/reset-password',
    response_model=UserResponse,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def reset_password(
    user_id: int,
    data: AdminResetPasswordRequest,
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-04 / AC-01-08: Admin resets password; revokes sessions and forces password change."""
    updated = reset_user_password(db, user_id, data.new_password)
    return UserResponse.model_validate(updated)
