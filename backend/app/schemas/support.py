from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import TicketStatus, TicketType


class SupportTicketCreateRequest(BaseModel):
    ticket_type: TicketType = Field(default=TicketType.INQUIRY)
    subject: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=3, max_length=5000)
    order_id: Optional[int] = None
    rfq_id: Optional[int] = None


class SupportMessageCreateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class SupportStatusUpdateRequest(BaseModel):
    status: TicketStatus


class SupportFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    file_name: str
    content_type: str
    file_size_bytes: int
    is_previewable: bool
    created_at: datetime


class SupportMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    sender_id: int
    sender_role: str
    sender_name: Optional[str] = None
    message: str
    created_at: datetime


class SupportTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    ticket_type: str
    subject: str
    status: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    rfq_id: Optional[int] = None
    rfq_number: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class SupportTicketDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    ticket_type: str
    subject: str
    status: str
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    rfq_id: Optional[int] = None
    rfq_number: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[SupportMessageOut] = []
    attachments: list[SupportFileOut] = []
