from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrderCommercialStatus(str, Enum):
    AWAITING_PAYMENT = 'awaiting_payment'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'


class InvoiceStatus(str, Enum):
    UNPAID = 'unpaid'
    PARTIALLY_PAID = 'partially_paid'
    PAID = 'paid'
    CANCELLED = 'cancelled'


class OrderCommercialSnapshot(Base):
    """Immutable commercial snapshot and lifecycle metadata for an Order (S08).

    Kept in its own 1:1 table (`order_id` unique) so S08 commercial fields can be
    developed and tested independently without modifying S07's in-progress `models.py`.
    """

    __tablename__ = 'order_commercial_snapshots'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('orders.id', ondelete='CASCADE'), unique=True, index=True, nullable=False
    )
    quotation_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('quotations.id'), unique=True, index=True, nullable=True)
    quotation_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Immutable customer & requirement snapshot captured at order creation
    customer_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_gstin_snapshot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_address_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estimated_lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Immutable INR commercial totals
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default='INR')
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    tax_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal('18.00'))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    items_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Settlement summary (controlled-fixture tested in S08; live payments in S09)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal('0.00'))
    successful_payment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Cancellation metadata (REQ-21: preserves history, blocks assignment & payments)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CommercialInvoice(Base):
    """One demonstration invoice per Order with an immutable commercial snapshot (REQ-20)."""

    __tablename__ = 'invoices'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('orders.id', ondelete='CASCADE'), unique=True, index=True, nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )

    # Immutable snapshot fields
    customer_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_gstin_snapshot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_address_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default='INR')
    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    tax_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal('18.00'))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    items_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Settlement & demo flags
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=Decimal('0.00'))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=InvoiceStatus.UNPAID.value)
    is_demo_invoice: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrderStatusEvent(Base):
    """Append-only audit history of order lifecycle transitions (preserves cancellation history)."""

    __tablename__ = 'order_status_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('orders.id', ondelete='CASCADE'), index=True, nullable=False
    )
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SimulatedPayment(Base):
    """Append-only demo attempts; successful rows are the settlement ledger."""

    __tablename__ = 'simulated_payments'
    __table_args__ = (
        CheckConstraint('amount > 0', name='ck_simulated_payment_positive'),
        CheckConstraint("outcome IN ('succeeded', 'failed')", name='ck_simulated_payment_outcome'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'), index=True, nullable=False)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
