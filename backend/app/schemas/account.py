from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import UserRole
from app.schemas.auth import CustomerProfileResponse, EmployeeProfileResponse, UserResponse


class CustomerRegisterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    company_name: str = Field(..., min_length=2, max_length=255)
    contact_person: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=7, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_stripped = v.strip().lower()
        if '@' not in v_stripped or '.' not in v_stripped.split('@')[-1]:
            raise ValueError('Invalid email address format.')
        return v_stripped

    @field_validator('gstin')
    @classmethod
    def clean_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return None


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_stripped = v.strip().lower()
        if '@' not in v_stripped or '.' not in v_stripped.split('@')[-1]:
            raise ValueError('Invalid email address format.')
        return v_stripped


class UserStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    is_active: bool


class AdminResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class CustomerProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_person: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, min_length=7, max_length=50)
    gstin: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class EmployeeProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=100)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Optional fields depending on user role
    company_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None


class AdminUserListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    customer_profile: Optional[CustomerProfileResponse] = None
    employee_profile: Optional[EmployeeProfileResponse] = None
    active_sessions_count: int = 0
