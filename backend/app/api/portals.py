from fastapi import APIRouter, Depends

from app.dependencies import require_admin, require_customer, require_employee
from app.models import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix='/api', tags=['Portals'])


@router.get('/customer/workspace')
def get_customer_workspace(current_user: User = Depends(require_customer)):
    return {
        'portal': 'customer',
        'user': UserResponse.model_validate(current_user),
        'status': 'active',
        'message': 'Welcome to Customer Workspace',
    }


@router.get('/employee/workspace')
def get_employee_workspace(current_user: User = Depends(require_employee)):
    return {
        'portal': 'employee',
        'user': UserResponse.model_validate(current_user),
        'status': 'active',
        'message': 'Welcome to Employee Workspace',
    }


@router.get('/admin/workspace')
def get_admin_workspace(current_user: User = Depends(require_admin)):
    return {
        'portal': 'admin',
        'user': UserResponse.model_validate(current_user),
        'status': 'active',
        'message': 'Welcome to Admin Workspace',
    }
