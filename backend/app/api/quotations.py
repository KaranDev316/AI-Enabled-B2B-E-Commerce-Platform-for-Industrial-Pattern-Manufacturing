"""S07 manual quotations. Every mutation serializes on the parent RFQ row."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, require_customer, verify_csrf_token, verify_trusted_origin
from app.models import Quotation, QuotationDecision, QuotationItem, RFQ, User
from app.schemas.quotation import QuoteCreateInput, QuoteUpdateInput, QuoteSendInput, QuoteDecisionInput

router = APIRouter(prefix='/api', tags=['Quotations'])
write_checks = [Depends(verify_trusted_origin), Depends(verify_csrf_token)]
CENT = Decimal('0.01')


def now():
    return datetime.now(timezone.utc)


def expired(quote):
    until = quote.valid_until
    if until is not None and until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until is not None and until <= now()


def rfq_for(db, rfq_id, customer=None, lock=False):
    stmt = select(RFQ).where(RFQ.id == rfq_id)
    if customer:
        stmt = stmt.where(RFQ.customer_id == customer.id)
    if lock:
        stmt = stmt.with_for_update()
    rfq = db.scalar(stmt)
    if not rfq:
        raise HTTPException(404, 'RFQ not found')
    return rfq


def versions(db, rfq_id):
    return list(db.scalars(select(Quotation).where(Quotation.rfq_id == rfq_id).order_by(Quotation.version.desc()).execution_options(populate_existing=True)))


def quote_for_update(db, quote_id, customer=None):
    # Read the parent ID only; load state AFTER obtaining its lock.
    rfq_id = db.scalar(select(Quotation.rfq_id).where(Quotation.id == quote_id))
    rfq_for(db, rfq_id, customer, lock=True)
    quotes = versions(db, rfq_id)
    quote = next((q for q in quotes if q.id == quote_id), None)
    if not quote:
        raise HTTPException(404, 'Quotation not found')
    return quote, quotes[0]


def current_draft(quote, latest, revision):
    if quote.id != latest.id or quote.status != 'draft' or quote.revision != revision:
        raise HTTPException(409, 'Quotation changed or is no longer an editable draft. Reload the latest version.')


def apply_draft(quote, data):
    quote.items = [QuotationItem(position=i, description=item.description, quantity=item.quantity,
                                unit_price=item.unit_price, amount=(item.unit_price * item.quantity).quantize(CENT))
                   for i, item in enumerate(data.items)]
    quote.subtotal = sum((item.amount for item in quote.items), Decimal('0.00'))
    quote.tax_percent = data.tax_percent
    quote.tax_amount = (quote.subtotal * data.tax_percent / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    quote.total = quote.subtotal + quote.tax_amount
    quote.lead_time_days = data.lead_time_days
    quote.valid_until = data.valid_until
    quote.notes = data.notes


def output(quote, latest):
    is_expired = expired(quote)
    return {
        'id': quote.id, 'rfq_id': quote.rfq_id, 'version': quote.version, 'revision': quote.revision,
        'status': 'expired' if quote.status == 'sent' and is_expired else quote.status,
        'is_latest': quote.id == latest.id,
        'can_respond': quote.id == latest.id and quote.status == 'sent' and not is_expired,
        'pricing_source': quote.pricing_source, 'estimation_id': quote.estimation_id,
        'currency': 'INR', 'tax_label': 'Sample tax (academic demonstration)',
        **{key: str(getattr(quote, key)) for key in ('subtotal', 'tax_percent', 'tax_amount', 'total')},
        'lead_time_days': quote.lead_time_days, 'valid_until': quote.valid_until,
        'notes': quote.notes, 'created_at': quote.created_at, 'sent_at': quote.sent_at,
        'items': [{'description': i.description, 'quantity': i.quantity, 'unit_price': str(i.unit_price), 'amount': str(i.amount)} for i in quote.items],
        'decisions': [{'id': d.id, 'action': d.action, 'message': d.message, 'created_at': d.created_at} for d in quote.decisions],
    }


@router.get('/admin/rfqs/{rfq_id}/quotations')
def admin_list(rfq_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rfq_for(db, rfq_id)
    quotes = versions(db, rfq_id)
    return [output(q, quotes[0]) for q in quotes]


@router.get('/rfqs/{rfq_id}/quotations')
def customer_list(rfq_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    rfq_for(db, rfq_id, user)
    quotes = versions(db, rfq_id)
    # Never disclose unpublished draft prices, including superseded drafts.
    return [output(q, quotes[0]) for q in quotes if q.sent_at is not None]


@router.post('/admin/rfqs/{rfq_id}/quotations', status_code=201, dependencies=write_checks)
def create_draft(rfq_id: int, data: QuoteCreateInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rfq = rfq_for(db, rfq_id, lock=True)
    quotes = versions(db, rfq_id)
    if any(q.status == 'accepted' for q in quotes):
        raise HTTPException(409, 'An accepted quotation cannot be revised')
    latest_version = quotes[0].version if quotes else 0
    if data.expected_version != latest_version:
        raise HTTPException(409, 'A newer version exists. Reload before revising.')
    if rfq.status in ('closed', 'rejected'):
        raise HTTPException(409, 'This RFQ is closed or rejected')
    if quotes:
        quotes[0].status = 'superseded'
    quote = Quotation(rfq_id=rfq_id, version=latest_version + 1, revision=1, created_by=user.id,
                      status='draft', pricing_source='manual', estimation_id=None)
    apply_draft(quote, data)
    db.add(quote)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Another revision was saved. Reload the latest quotation.')
    return output(quote, quote)


@router.put('/admin/quotations/{quote_id}', dependencies=write_checks)
def update_draft(quote_id: int, data: QuoteUpdateInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    quote, latest = quote_for_update(db, quote_id)
    current_draft(quote, latest, data.expected_revision)
    apply_draft(quote, data)
    quote.revision += 1
    db.commit()
    return output(quote, latest)


@router.post('/admin/quotations/{quote_id}/send', dependencies=write_checks)
def send_quote(quote_id: int, data: QuoteSendInput, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    quote, latest = quote_for_update(db, quote_id)
    current_draft(quote, latest, data.expected_revision)
    if not quote.items or not quote.lead_time_days or quote.total <= 0 or expired(quote):
        raise HTTPException(422, 'Add line items, a positive total and lead time, and a future validity date if supplied.')
    quote.status = 'sent'
    quote.sent_at = now()
    quote.revision += 1
    db.get(RFQ, quote.rfq_id).status = 'quoted'
    db.commit()
    return output(quote, latest)


@router.post('/quotations/{quote_id}/decisions', status_code=201, dependencies=write_checks)
def decide_quote(quote_id: int, data: QuoteDecisionInput, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    quote, latest = quote_for_update(db, quote_id, user)
    if quote.id != latest.id or quote.status != 'sent' or expired(quote):
        raise HTTPException(409, 'This offer is no longer available for a decision. Reload the latest quotation.')
    quote.decisions.append(QuotationDecision(customer_id=user.id, action=data.action, message=data.message))
    if data.action == 'reject':
        quote.status = 'rejected'
    db.commit()
    return output(quote, latest)
