from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import (
    get_current_user,
    require_admin,
    require_customer,
    verify_csrf_token,
    verify_trusted_origin,
)
from app.models import Order, RFQ, User
from app.schemas.support import (
    SupportFileOut,
    SupportMessageCreateRequest,
    SupportMessageOut,
    SupportStatusUpdateRequest,
    SupportTicketCreateRequest,
    SupportTicketDetailOut,
    SupportTicketOut,
)
from app.services.support_service import SupportService

router = APIRouter(prefix='/api', tags=['Support & Tickets'])
support_service = SupportService()


@router.post(
    '/support/tickets',
    response_model=SupportTicketDetailOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def create_support_ticket(
    data: SupportTicketCreateRequest,
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-30 / AC-09-01: Customer creates an owned support ticket."""
    return support_service.create_ticket(db, customer=current_user, data=data)


@router.get('/support/tickets/my', response_model=list[SupportTicketOut])
def get_my_tickets(
    status: Optional[str] = Query(None),
    ticket_type: Optional[str] = Query(None),
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-30 / AC-09-01: Customer lists their own support tickets."""
    return support_service.list_customer_tickets(
        db, customer_id=current_user.id, status=status, ticket_type=ticket_type
    )


@router.get('/support/customer-context')
def get_customer_support_context(
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """Helper to populate related Order and RFQ dropdowns for the customer."""
    orders = (
        db.query(Order)
        .filter(Order.customer_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    rfqs = (
        db.query(RFQ)
        .filter(RFQ.customer_id == current_user.id)
        .order_by(RFQ.created_at.desc())
        .all()
    )
    return {
        'orders': [{'id': o.id, 'order_number': o.order_number, 'status': o.status} for o in orders],
        'rfqs': [{'id': r.id, 'rfq_number': r.rfq_number, 'title': r.title} for r in rfqs],
    }


@router.get('/support/tickets/{ticket_id}', response_model=SupportTicketDetailOut)
def get_ticket_details(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-31 / AC-09-03 / AC-09-04: View conversation thread and attachments."""
    return support_service.get_ticket_detail(db, ticket_id=ticket_id, user=current_user)


@router.post(
    '/support/tickets/{ticket_id}/messages',
    response_model=SupportMessageOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def add_ticket_reply(
    ticket_id: int,
    data: SupportMessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-31 / AC-09-03: Post a reply into the ticket conversation thread."""
    return support_service.add_message(
        db, ticket_id=ticket_id, user=current_user, message_text=data.message
    )


@router.post(
    '/support/tickets/{ticket_id}/files',
    response_model=SupportFileOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def upload_support_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-30 / AC-09-02: Attach JPG/PNG/PDF file (max 2 files, 20 MB each)."""
    return support_service.attach_file(db, ticket_id=ticket_id, user=current_user, file=file)


@router.get('/support/tickets/{ticket_id}/files/{file_id}')
def download_support_attachment(
    ticket_id: int,
    file_id: int,
    disposition: str = Query('inline', pattern='^(inline|attachment)$'),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-30 / AC-09-04: Secure download / in-browser preview of support attachment."""
    content, filename, content_type = support_service.retrieve_file(
        db, ticket_id=ticket_id, file_id=file_id, user=current_user
    )
    headers = {
        'Content-Disposition': f'{disposition}; filename="{filename}"',
        'Cache-Control': 'private, no-cache',
    }
    return Response(content=content, media_type=content_type, headers=headers)


@router.get('/admin/support/tickets', response_model=list[SupportTicketOut])
def admin_list_tickets(
    status: Optional[str] = Query(None),
    ticket_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-32 / AC-09-01: Admin support queue view with status and type filters."""
    return support_service.list_admin_tickets(
        db, status=status, ticket_type=ticket_type, search=search
    )


@router.patch(
    '/admin/support/tickets/{ticket_id}/status',
    response_model=SupportTicketOut,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def admin_update_ticket_status(
    ticket_id: int,
    data: SupportStatusUpdateRequest,
    current_user: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-32 / AC-09-05: Admin updates ticket status (open, in_progress, resolved, closed)."""
    return support_service.update_status(
        db, ticket_id=ticket_id, user=current_user, new_status=data.status
    )
