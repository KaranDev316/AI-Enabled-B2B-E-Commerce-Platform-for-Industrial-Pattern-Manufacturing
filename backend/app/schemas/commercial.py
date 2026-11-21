from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommercialLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., ge=1)
    unit: str = Field(default='pcs', max_length=32)
    unit_price: Decimal = Field(..., ge=Decimal('0.00'))
    line_total: Decimal = Field(..., ge=Decimal('0.00'))


class OrderStatusEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    note: Optional[str] = None
    actor_user_id: Optional[int] = None
    created_at: datetime


class LinkedInvoiceSummary(BaseModel):
    id: int
    invoice_number: str
    status: str
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    is_demo_invoice: bool = True
    issued_at: datetime


class OrderSummaryResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    customer_name: str
    rfq_id: Optional[int] = None
    quotation_id: Optional[int] = None
    quotation_version: Optional[int] = None
    product_summary: str
    quantity: int
    currency: str = 'INR'
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    status: str
    payment_status: str
    production_status: Optional[str] = None
    estimated_lead_time_days: Optional[int] = None
    can_cancel: bool
    can_assign: bool = False
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    created_at: datetime
    cancelled_at: Optional[datetime] = None


class OrderDetailResponse(OrderSummaryResponse):
    customer_gstin: Optional[str] = None
    customer_address: Optional[str] = None
    subtotal_amount: Decimal
    tax_rate_percent: Decimal
    tax_amount: Decimal
    items: list[CommercialLineItem]
    successful_payment_count: int = 0
    cancellation_reason: Optional[str] = None
    invoice: Optional[LinkedInvoiceSummary] = None
    status_history: list[OrderStatusEventResponse] = Field(default_factory=list)


class OrderCancelRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class OrderCancelResponse(BaseModel):
    order: OrderDetailResponse
    message: str


class InvoiceSummaryResponse(BaseModel):
    id: int
    invoice_number: str
    order_id: int
    order_number: str
    customer_id: int
    customer_name: str
    currency: str = 'INR'
    subtotal_amount: Decimal
    tax_rate_percent: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_balance: Decimal
    status: str
    is_demo_invoice: bool = True
    issued_at: datetime
    due_at: Optional[datetime] = None


class SimulatedPaymentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2, allow_inf_nan=False)
    outcome: Literal['succeeded', 'failed'] = 'succeeded'
    idempotency_key: UUID


class SimulatedPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    actor_user_id: int
    idempotency_key: str
    amount: Decimal
    outcome: Literal['succeeded', 'failed']
    created_at: datetime


class InvoiceDetailResponse(InvoiceSummaryResponse):
    customer_gstin: Optional[str] = None
    customer_address: Optional[str] = None
    items: list[CommercialLineItem]
    order_status: str
    payments: list[SimulatedPaymentResponse] = Field(default_factory=list)
    demo_notice: str = (
        'Academic Demonstration Invoice — Sample tax figures are for demonstration only and do not '
        'constitute a statutory tax invoice or real financial transaction.'
    )
