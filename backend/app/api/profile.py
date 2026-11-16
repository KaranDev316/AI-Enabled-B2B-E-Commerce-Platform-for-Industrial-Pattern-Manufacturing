from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import (
    get_current_user,
    verify_csrf_token,
    verify_trusted_origin,
)
from app.models import User
from app.schemas.account import ProfileUpdateRequest
from app.schemas.auth import UserResponse
from app.services.account_service import update_own_profile

router = APIRouter(prefix='/api/profile', tags=['Profile'])


@router.get('/me', response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    """REQ-03: Signed-in user reads own profile."""
    return UserResponse.model_validate(current_user)


@router.patch(
    '/me',
    response_model=UserResponse,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-03: Signed-in user updates permitted personal/business profile fields."""
    updated_user = update_own_profile(db, current_user, data)
    return UserResponse.model_validate(updated_user)
