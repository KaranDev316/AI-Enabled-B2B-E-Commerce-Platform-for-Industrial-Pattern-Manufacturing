from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import UserRole


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_stripped = v.strip().lower()
        if '@' not in v_stripped or '.' not in v_stripped.split('@')[-1]:
            raise ValueError('Invalid email address format.')
        return v_stripped


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_name: str
    contact_person: str
    phone: str
    gstin: Optional[str] = None
    address: Optional[str] = None


class EmployeeProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_name: str
    phone: Optional[str] = None
    department: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    customer_profile: Optional[CustomerProfileResponse] = None
    employee_profile: Optional[EmployeeProfileResponse] = None


class SessionResponse(BaseModel):
    user: UserResponse
    csrf_token: str
    message: str = 'Authenticated successfully'
    session_token: Optional[str] = None
    token: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: Optional[dict[str, str]] = None
