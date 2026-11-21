from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from uuid import uuid4
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Order, Quotation, User, UserRole
from app.models_commercial import (
    CommercialInvoice,
    InvoiceStatus,
    OrderCommercialSnapshot,
    OrderCommercialStatus,
    OrderStatusEvent,
    SimulatedPayment,
)
from app.schemas.commercial import (
    CommercialLineItem,
    InvoiceDetailResponse,
    InvoiceSummaryResponse,
    LinkedInvoiceSummary,
    OrderDetailResponse,
    OrderStatusEventResponse,
    OrderSummaryResponse,
    SimulatedPaymentResponse,
)

TWO_PLACES = Decimal('0.01')
AWAITING_PAYMENT_STATUSES = {OrderCommercialStatus.AWAITING_PAYMENT.value, 'pending_payment'}


def quantize_inr(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def compute_commercial_totals(
    items: list[dict],
    tax_rate_percent: Decimal | int | float | str = Decimal('18.00'),
) -> tuple[list[dict], Decimal, Decimal, Decimal, Decimal]:
    """Computes normalized immutable line items and exact Decimal INR totals."""
    if not items:
        raise ValueError('At least one line item is required for a commercial snapshot.')

    normalized_items: list[dict] = []
    subtotal = Decimal('0.00')
    for raw in items:
        qty = int(raw['quantity'])
        if qty < 1:
            raise ValueError('Item quantity must be at least 1.')
        unit_price = quantize_inr(raw['unit_price'])
        if unit_price < Decimal('0.00'):
            raise ValueError('Item unit price cannot be negative.')
        line_total = quantize_inr(unit_price * qty)
        subtotal = quantize_inr(subtotal + line_total)
        normalized_items.append(
            {
                'description': str(raw['description']).strip(),
                'quantity': qty,
                'unit': str(raw.get('unit') or 'pcs').strip(),
                'unit_price': str(unit_price),
                'line_total': str(line_total),
            }
        )

    rate = quantize_inr(tax_rate_percent)
    if rate < Decimal('0.00') or rate > Decimal('100.00'):
        raise ValueError('Tax rate must be between 0 and 100.')
    tax_amount = quantize_inr((subtotal * rate) / Decimal('100.00'))
    total_amount = quantize_inr(subtotal + tax_amount)
    return normalized_items, subtotal, rate, tax_amount, total_amount


def compute_outstanding_balance(total_amount: Decimal, paid_amount: Decimal) -> Decimal:
    remaining = quantize_inr(Decimal(str(total_amount)) - Decimal(str(paid_amount)))
    return remaining if remaining > Decimal('0.00') else Decimal('0.00')


def _parse_items_snapshot(raw_json: str) -> list[CommercialLineItem]:
    parsed = json.loads(raw_json) if raw_json else []
    return [
        CommercialLineItem(
            description=item['description'],
            quantity=int(item['quantity']),
            unit=item.get('unit', 'pcs'),
            unit_price=quantize_inr(item['unit_price']),
            line_total=quantize_inr(item['line_total']),
        )
        for item in parsed
    ]


def _derive_payment_status(order_status: str, total_amount: Decimal, paid_amount: Decimal) -> str:
    if order_status == OrderCommercialStatus.CANCELLED.value:
        return InvoiceStatus.CANCELLED.value
    total = quantize_inr(total_amount)
    paid = quantize_inr(paid_amount)
    if paid <= Decimal('0.00'):
        return InvoiceStatus.UNPAID.value
    if paid >= total:
        return InvoiceStatus.PAID.value
    return InvoiceStatus.PARTIALLY_PAID.value


def _is_order_cancellable(order: Order, snapshot: OrderCommercialSnapshot) -> bool:
    return (
        order.status in AWAITING_PAYMENT_STATUSES
        and quantize_inr(snapshot.paid_amount) == Decimal('0.00')
        and int(snapshot.successful_payment_count) == 0
    )


def _generate_next_order_number(db: DBSession) -> str:
    return f'KPC-{datetime.now(timezone.utc).year}-{uuid4().hex}'


def _generate_next_invoice_number(db: DBSession) -> str:
    return f'INV-{datetime.now(timezone.utc).year}-{uuid4().hex}'


def create_order_and_invoice_atomic(
    db: DBSession,
    *,
    customer_id: int,
    customer_name: str,
    product_summary: str,
    items: list[dict],
    tax_rate_percent: Decimal | int | float | str = Decimal('18.00'),
    rfq_id: Optional[int] = None,
    quotation_id: Optional[int] = None,
    quotation_version: Optional[int] = None,
    customer_gstin: Optional[str] = None,
    customer_address: Optional[str] = None,
    estimated_lead_time_days: Optional[int] = None,
    due_in_days: Optional[int] = None,
    actor_user_id: Optional[int] = None,
    accepted_quote: Optional[Quotation] = None,
    requested_quantity: Optional[int] = None,
) -> tuple[Order, OrderCommercialSnapshot, CommercialInvoice]:
    """Atomically creates 1 awaiting-payment Order, 1 immutable snapshot, and 1 demo Invoice.

    If `quotation_id` is provided and an order already exists for that quotation, returns the
    existing records idempotently without creating duplicates (REQ-17 / AC-05-07).
    """
    if quotation_id is not None:
        existing_snapshot = db.scalar(
            select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.quotation_id == quotation_id)
        )
        if existing_snapshot is not None:
            existing_order = db.get(Order, existing_snapshot.order_id)
            existing_invoice = db.scalar(
                select(CommercialInvoice).where(CommercialInvoice.order_id == existing_snapshot.order_id)
            )
            if existing_order is not None and existing_invoice is not None:
                return existing_order, existing_snapshot, existing_invoice

    if accepted_quote is not None:
        # Copy the issued commercial values exactly; never recalculate from catalogue/settings.
        normalized_items = [dict(description=i.description, quantity=i.quantity, unit='pcs',
                                 unit_price=str(i.unit_price), line_total=str(i.amount)) for i in accepted_quote.items]
        subtotal, rate, tax_amount, total_amount = (getattr(accepted_quote, field) for field in
                                                  ('subtotal', 'tax_percent', 'tax_amount', 'total'))
    else:
        normalized_items, subtotal, rate, tax_amount, total_amount = compute_commercial_totals(
            items=items, tax_rate_percent=tax_rate_percent,
        )
    total_qty = requested_quantity if requested_quantity is not None else sum(int(item['quantity']) for item in normalized_items)
    items_json = json.dumps(normalized_items)
    now = datetime.now(timezone.utc)

    with db.begin_nested():
        order = Order(
            order_number=_generate_next_order_number(db),
            customer_id=customer_id,
            rfq_id=rfq_id,
            total_amount=total_amount,
            status=OrderCommercialStatus.AWAITING_PAYMENT.value,
        )
        db.add(order)
        db.flush()
        order.order_number = f'KPC-{now.year}-{order.id:06d}'

        snapshot = OrderCommercialSnapshot(
            order_id=order.id,
            quotation_id=quotation_id,
            quotation_version=quotation_version,
            customer_name_snapshot=customer_name.strip(),
            customer_gstin_snapshot=customer_gstin.strip() if customer_gstin else None,
            customer_address_snapshot=customer_address.strip() if customer_address else None,
            product_summary=product_summary.strip(),
            quantity=total_qty,
            estimated_lead_time_days=estimated_lead_time_days,
            currency='INR',
            subtotal_amount=subtotal,
            tax_rate_percent=rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            items_snapshot_json=items_json,
            paid_amount=Decimal('0.00'),
            successful_payment_count=0,
        )
        db.add(snapshot)

        invoice = CommercialInvoice(
            invoice_number=_generate_next_invoice_number(db),
            order_id=order.id,
            customer_id=customer_id,
            customer_name_snapshot=customer_name.strip(),
            customer_gstin_snapshot=customer_gstin.strip() if customer_gstin else None,
            customer_address_snapshot=customer_address.strip() if customer_address else None,
            currency='INR',
            subtotal_amount=subtotal,
            tax_rate_percent=rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            items_snapshot_json=items_json,
            paid_amount=Decimal('0.00'),
            status=InvoiceStatus.UNPAID.value,
            is_demo_invoice=True,
            issued_at=now,
            due_at=now + timedelta(days=due_in_days) if due_in_days is not None else None,
        )
        db.add(invoice)

        event = OrderStatusEvent(
            order_id=order.id,
            actor_user_id=actor_user_id or customer_id,
            event_type='order_created',
            from_status=None,
            to_status=OrderCommercialStatus.AWAITING_PAYMENT.value,
            note='Order and invoice created awaiting payment.',
        )
        db.add(event)
        db.flush()
        invoice.invoice_number = f'INV-{now.year}-{invoice.id:06d}'
        db.flush()

    return order, snapshot, invoice


def _require_commercial_access(user: User, resource_customer_id: int) -> None:
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role == UserRole.ADMIN.value:
        return
    if role == UserRole.CUSTOMER.value and user.id == resource_customer_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={'code': 'FORBIDDEN', 'message': 'You do not have permission to access this commercial record.'},
    )


def _serialize_order_summary(
    order: Order,
    snapshot: Optional[OrderCommercialSnapshot],
    invoice: Optional[CommercialInvoice],
    current_user: User,
) -> OrderSummaryResponse:
    role = current_user.role.value if isinstance(current_user.role, UserRole) else current_user.role
    total = quantize_inr(snapshot.total_amount if snapshot else order.total_amount)
    paid = quantize_inr(snapshot.paid_amount if snapshot else Decimal('0.00'))
    outstanding = compute_outstanding_balance(total, paid)
    payment_status = _derive_payment_status(order.status, total, paid)
    can_cancel = (
        role == UserRole.CUSTOMER.value
        and current_user.id == order.customer_id
        and snapshot is not None
        and _is_order_cancellable(order, snapshot)
    )

    return OrderSummaryResponse(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_name=snapshot.customer_name_snapshot if snapshot else f'Customer #{order.customer_id}',
        rfq_id=order.rfq_id,
        quotation_id=snapshot.quotation_id if snapshot else None,
        quotation_version=snapshot.quotation_version if snapshot else None,
        product_summary=snapshot.product_summary if snapshot else 'Manufacturing Order',
        quantity=snapshot.quantity if snapshot else 1,
        currency=snapshot.currency if snapshot else 'INR',
        total_amount=total,
        paid_amount=paid,
        outstanding_balance=outstanding,
        status=order.status,
        payment_status=payment_status,
        production_status=None,  # S08 boundary: no invented production/job history
        estimated_lead_time_days=snapshot.estimated_lead_time_days if snapshot else None,
        can_cancel=can_cancel,
        can_assign=(role == UserRole.ADMIN.value and order.status == 'confirmed'
                    and snapshot is not None and paid == total and total > 0
                    and snapshot.successful_payment_count > 0),
        invoice_id=invoice.id if invoice else None,
        invoice_number=invoice.invoice_number if invoice else None,
        created_at=order.created_at,
        cancelled_at=snapshot.cancelled_at if snapshot else None,
    )


def list_orders_for_user(
    db: DBSession,
    user: User,
    *,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> list[OrderSummaryResponse]:
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role not in (UserRole.CUSTOMER.value, UserRole.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Only Customers and Admins can access commercial orders.'},
        )

    stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    if role == UserRole.CUSTOMER.value:
        stmt = stmt.where(Order.customer_id == user.id)
    if status_filter and status_filter != 'all':
        stmt = stmt.where(Order.status == status_filter)

    orders = list(db.scalars(stmt).all())
    if not orders:
        return []

    order_ids = [o.id for o in orders]
    snapshots = {
        s.order_id: s
        for s in db.scalars(
            select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id.in_(order_ids))
        ).all()
    }
    invoices = {
        inv.order_id: inv
        for inv in db.scalars(
            select(CommercialInvoice).where(CommercialInvoice.order_id.in_(order_ids))
        ).all()
    }

    summaries = [
        _serialize_order_summary(order, snapshots.get(order.id), invoices.get(order.id), user)
        for order in orders
    ]

    if search and search.strip():
        needle = search.strip().lower()
        summaries = [
            s
            for s in summaries
            if needle in s.order_number.lower()
            or needle in s.product_summary.lower()
            or needle in s.customer_name.lower()
            or (s.invoice_number and needle in s.invoice_number.lower())
        ]

    return summaries


def get_order_detail_for_user(db: DBSession, order_id: int, user: User) -> OrderDetailResponse:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'ORDER_NOT_FOUND', 'message': 'Order not found.'},
        )
    _require_commercial_access(user, order.customer_id)

    snapshot = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order.id).execution_options(populate_existing=True))
    invoice = db.scalar(select(CommercialInvoice).where(CommercialInvoice.order_id == order.id))
    events = list(
        db.scalars(
            select(OrderStatusEvent)
            .where(OrderStatusEvent.order_id == order.id)
            .order_by(OrderStatusEvent.created_at.asc(), OrderStatusEvent.id.asc())
        ).all()
    )

    summary = _serialize_order_summary(order, snapshot, invoice, user)
    linked_invoice = None
    if invoice is not None:
        linked_invoice = LinkedInvoiceSummary(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            total_amount=quantize_inr(invoice.total_amount),
            paid_amount=quantize_inr(invoice.paid_amount),
            outstanding_balance=compute_outstanding_balance(invoice.total_amount, invoice.paid_amount),
            is_demo_invoice=invoice.is_demo_invoice,
            issued_at=invoice.issued_at,
        )

    return OrderDetailResponse(
        **summary.model_dump(),
        customer_gstin=snapshot.customer_gstin_snapshot if snapshot else None,
        customer_address=snapshot.customer_address_snapshot if snapshot else None,
        subtotal_amount=quantize_inr(snapshot.subtotal_amount if snapshot else order.total_amount),
        tax_rate_percent=quantize_inr(snapshot.tax_rate_percent if snapshot else Decimal('0.00')),
        tax_amount=quantize_inr(snapshot.tax_amount if snapshot else Decimal('0.00')),
        items=_parse_items_snapshot(snapshot.items_snapshot_json) if snapshot else [],
        successful_payment_count=snapshot.successful_payment_count if snapshot else 0,
        cancellation_reason=snapshot.cancellation_reason if snapshot else None,
        invoice=linked_invoice,
        status_history=[OrderStatusEventResponse.model_validate(e).model_copy(update={'note': {
            'Order and academic demonstration invoice created awaiting payment.': 'Order and invoice created awaiting payment.',
            'Full simulated settlement recorded. Eligible for production assignment.': 'Payment completed. Order ready for production assignment.',
        }.get(e.note, e.note)}) for e in events],
    )


def cancel_unpaid_order(
    db: DBSession,
    order_id: int,
    customer_user: User,
    reason: Optional[str] = None,
) -> OrderDetailResponse:
    """Cancels an awaiting-payment order with zero successful payments (REQ-21 / AC-06-07)."""
    role = customer_user.role.value if isinstance(customer_user.role, UserRole) else customer_user.role
    if role != UserRole.CUSTOMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Only the owning Customer can cancel an unpaid order.'},
        )

    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'ORDER_NOT_FOUND', 'message': 'Order not found.'},
        )

    if order.customer_id != customer_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'You cannot cancel another customer’s order.'},
        )

    if order.status == OrderCommercialStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'code': 'ORDER_ALREADY_CANCELLED', 'message': 'This order is already cancelled.'},
        )

    snapshot = db.scalar(select(OrderCommercialSnapshot).where(OrderCommercialSnapshot.order_id == order.id).execution_options(populate_existing=True))
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={'code': 'CANCELLATION_NOT_ALLOWED', 'message': 'Order commercial state is unavailable.'},
        )

    if not _is_order_cancellable(order, snapshot):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'code': 'CANCELLATION_NOT_ALLOWED',
                'message': 'Only an awaiting-payment order with zero successful payments can be cancelled.',
            },
        )

    previous_status = order.status
    now = datetime.now(timezone.utc)
    cleaned_reason = reason.strip() if reason and reason.strip() else 'Cancelled by customer before payment.'

    with db.begin_nested():
        order.status = OrderCommercialStatus.CANCELLED.value
        snapshot.cancelled_at = now
        snapshot.cancelled_by_user_id = customer_user.id
        snapshot.cancellation_reason = cleaned_reason

        invoice = db.scalar(select(CommercialInvoice).where(CommercialInvoice.order_id == order.id))
        if invoice is not None:
            invoice.status = InvoiceStatus.CANCELLED.value

        db.add(
            OrderStatusEvent(
                order_id=order.id,
                actor_user_id=customer_user.id,
                event_type='order_cancelled',
                from_status=previous_status,
                to_status=OrderCommercialStatus.CANCELLED.value,
                note=cleaned_reason,
            )
        )
        db.flush()

    return get_order_detail_for_user(db, order.id, customer_user)


def _serialize_invoice_summary(invoice: CommercialInvoice, order: Order) -> InvoiceSummaryResponse:
    total = quantize_inr(invoice.total_amount)
    paid = quantize_inr(invoice.paid_amount)
    return InvoiceSummaryResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        order_id=invoice.order_id,
        order_number=order.order_number,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer_name_snapshot,
        currency=invoice.currency,
        subtotal_amount=quantize_inr(invoice.subtotal_amount),
        tax_rate_percent=quantize_inr(invoice.tax_rate_percent),
        tax_amount=quantize_inr(invoice.tax_amount),
        total_amount=total,
        paid_amount=paid,
        outstanding_balance=compute_outstanding_balance(total, paid),
        status=invoice.status,
        is_demo_invoice=invoice.is_demo_invoice,
        issued_at=invoice.issued_at,
        due_at=invoice.due_at,
    )


def list_invoices_for_user(
    db: DBSession,
    user: User,
    *,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> list[InvoiceSummaryResponse]:
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    if role not in (UserRole.CUSTOMER.value, UserRole.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Only Customers and Admins can access invoices.'},
        )

    stmt = select(CommercialInvoice).order_by(CommercialInvoice.issued_at.desc(), CommercialInvoice.id.desc())
    if role == UserRole.CUSTOMER.value:
        stmt = stmt.where(CommercialInvoice.customer_id == user.id)
    if status_filter and status_filter != 'all':
        stmt = stmt.where(CommercialInvoice.status == status_filter)

    invoices = list(db.scalars(stmt).all())
    if not invoices:
        return []

    order_ids = [inv.order_id for inv in invoices]
    orders = {
        o.id: o
        for o in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()
    }

    results = [
        _serialize_invoice_summary(inv, orders[inv.order_id])
        for inv in invoices
        if inv.order_id in orders
    ]

    if search and search.strip():
        needle = search.strip().lower()
        results = [
            inv
            for inv in results
            if needle in inv.invoice_number.lower()
            or needle in inv.order_number.lower()
            or needle in inv.customer_name.lower()
        ]

    return results


def get_invoice_detail_for_user(db: DBSession, invoice_id: int, user: User) -> InvoiceDetailResponse:
    invoice = db.get(CommercialInvoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'INVOICE_NOT_FOUND', 'message': 'Invoice not found.'},
        )
    _require_commercial_access(user, invoice.customer_id)

    order = db.get(Order, invoice.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'ORDER_NOT_FOUND', 'message': 'Associated order not found.'},
        )

    summary = _serialize_invoice_summary(invoice, order)
    return InvoiceDetailResponse(
        **summary.model_dump(),
        customer_gstin=invoice.customer_gstin_snapshot,
        customer_address=invoice.customer_address_snapshot,
        items=_parse_items_snapshot(invoice.items_snapshot_json),
        order_status=order.status,
        payments=[SimulatedPaymentResponse.model_validate(payment) for payment in db.scalars(
            select(SimulatedPayment).where(SimulatedPayment.invoice_id == invoice.id)
            .order_by(SimulatedPayment.created_at, SimulatedPayment.id))],
    )
