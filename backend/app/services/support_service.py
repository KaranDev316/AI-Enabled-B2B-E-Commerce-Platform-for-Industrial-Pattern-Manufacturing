from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import (
    CustomerProfile,
    EmployeeProfile,
    Order,
    RFQ,
    SupportMessage,
    SupportTicket,
    SupportTicketFile,
    TicketStatus,
    TicketType,
    User,
    UserRole,
)
from app.schemas.support import (
    SupportFileOut,
    SupportMessageOut,
    SupportTicketCreateRequest,
    SupportTicketDetailOut,
    SupportTicketOut,
)
from app.services.file_validation import (
    MAX_FILES_PER_SUPPORT,
    is_previewable,
    validate_support_file_content,
)
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def generate_ticket_number(db: Session) -> str:
    """Generates an incremental ticket identifier: TICK-YYYY-XXXX."""
    current_year = datetime.now(timezone.utc).year
    prefix = f"TICK-{current_year}-"
    count = db.query(SupportTicket).filter(SupportTicket.ticket_number.startswith(prefix)).count()
    return f"{prefix}{count + 1:04d}"


def get_user_display_name(user: Optional[User]) -> str:
    if not user:
        return 'System'
    if user.role == UserRole.CUSTOMER.value and user.customer_profile:
        return f"{user.customer_profile.contact_person} ({user.customer_profile.company_name})"
    if user.role == UserRole.EMPLOYEE.value and user.employee_profile:
        return user.employee_profile.full_name
    if user.role == UserRole.ADMIN.value:
        return 'KPC Support Admin'
    return user.email.split('@')[0]


def serialize_ticket_out(ticket: SupportTicket) -> SupportTicketOut:
    customer_name = get_user_display_name(ticket.customer)
    order_number = ticket.order.order_number if ticket.order else None
    rfq_number = ticket.rfq.rfq_number if ticket.rfq else None

    return SupportTicketOut(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        ticket_type=ticket.ticket_type,
        subject=ticket.subject,
        status=ticket.status,
        order_id=ticket.order_id,
        order_number=order_number,
        rfq_id=ticket.rfq_id,
        rfq_number=rfq_number,
        customer_id=ticket.customer_id,
        customer_name=customer_name,
        customer_email=ticket.customer.email if ticket.customer else None,
        message_count=len(ticket.messages),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def serialize_ticket_detail(ticket: SupportTicket) -> SupportTicketDetailOut:
    customer_name = get_user_display_name(ticket.customer)
    order_number = ticket.order.order_number if ticket.order else None
    rfq_number = ticket.rfq.rfq_number if ticket.rfq else None

    messages_out = [
        SupportMessageOut(
            id=m.id,
            ticket_id=m.ticket_id,
            sender_id=m.sender_id,
            sender_role=m.sender_role,
            sender_name=get_user_display_name(m.sender),
            message=m.message,
            created_at=m.created_at,
        )
        for m in sorted(ticket.messages, key=lambda x: x.created_at)
    ]

    attachments_out = [
        SupportFileOut(
            id=f.id,
            ticket_id=f.ticket_id,
            file_name=f.file_name,
            content_type=f.content_type,
            file_size_bytes=f.file_size_bytes,
            is_previewable=is_previewable(f.file_name),
            created_at=f.created_at,
        )
        for f in ticket.attachments
    ]

    return SupportTicketDetailOut(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        ticket_type=ticket.ticket_type,
        subject=ticket.subject,
        status=ticket.status,
        order_id=ticket.order_id,
        order_number=order_number,
        rfq_id=ticket.rfq_id,
        rfq_number=rfq_number,
        customer_id=ticket.customer_id,
        customer_name=customer_name,
        customer_email=ticket.customer.email if ticket.customer else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=messages_out,
        attachments=attachments_out,
    )


class SupportService:
    def __init__(self, storage_service: Optional[StorageService] = None):
        self.storage = storage_service or StorageService()

    def create_ticket(self, db: Session, customer: User, data: SupportTicketCreateRequest) -> SupportTicketDetailOut:
        """Creates a unified support ticket with initial message (REQ-30)."""
        # Validate related order ownership if provided (AC-09-02)
        if data.order_id is not None:
            order = db.query(Order).filter(Order.id == data.order_id).first()
            if not order:
                raise HTTPException(status_code=400, detail="Related order not found.")
            if order.customer_id != customer.id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot link ticket to an order that does not belong to your account.",
                )

        # Validate related RFQ ownership if provided
        if data.rfq_id is not None:
            rfq = db.query(RFQ).filter(RFQ.id == data.rfq_id).first()
            if not rfq:
                raise HTTPException(status_code=400, detail="Related RFQ not found.")
            if rfq.customer_id != customer.id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot link ticket to an RFQ that does not belong to your account.",
                )

        ticket_number = generate_ticket_number(db)
        ticket = SupportTicket(
            ticket_number=ticket_number,
            customer_id=customer.id,
            ticket_type=data.ticket_type.value,
            subject=data.subject.strip(),
            status=TicketStatus.OPEN.value,
            order_id=data.order_id,
            rfq_id=data.rfq_id,
        )
        db.add(ticket)
        db.flush()

        initial_msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=customer.id,
            sender_role='customer',
            message=data.message.strip(),
        )
        db.add(initial_msg)
        db.commit()
        db.refresh(ticket)

        return serialize_ticket_detail(ticket)

    def verify_ticket_access(self, db: Session, ticket_id: int, user: User) -> SupportTicket:
        """Enforces tenant isolation and role boundaries (AC-09-04)."""
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found.")

        # Employees cannot view or participate in customer support conversations (REQ-31 / AC-09-04)
        if user.role == UserRole.EMPLOYEE.value:
            raise HTTPException(
                status_code=403,
                detail="Employees are not authorized to view customer support tickets.",
            )

        # Customer can only view their own tickets (REQ-31 / AC-09-04)
        if user.role == UserRole.CUSTOMER.value and ticket.customer_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access another customer's ticket.",
            )

        return ticket

    def get_ticket_detail(self, db: Session, ticket_id: int, user: User) -> SupportTicketDetailOut:
        """Retrieves complete conversation thread and attachments (REQ-31)."""
        ticket = self.verify_ticket_access(db, ticket_id, user)
        return serialize_ticket_detail(ticket)

    def add_message(self, db: Session, ticket_id: int, user: User, message_text: str) -> SupportMessageOut:
        """Adds a message to the conversation thread (REQ-31 / AC-09-03)."""
        ticket = self.verify_ticket_access(db, ticket_id, user)

        if not message_text or not message_text.strip():
            raise HTTPException(status_code=400, detail="Message content cannot be empty.")

        # Reject reply if ticket is resolved or closed (AC-09-06)
        if ticket.status in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reply to a {ticket.status} ticket. Reopen the ticket first.",
            )

        sender_role = 'admin' if user.role == UserRole.ADMIN.value else 'customer'
        new_msg = SupportMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            sender_role=sender_role,
            message=message_text.strip(),
        )
        db.add(new_msg)

        # Admin replies automatically advance an 'open' ticket to 'in_progress'
        if sender_role == 'admin' and ticket.status == TicketStatus.OPEN.value:
            ticket.status = TicketStatus.IN_PROGRESS.value

        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(new_msg)

        return SupportMessageOut(
            id=new_msg.id,
            ticket_id=new_msg.ticket_id,
            sender_id=new_msg.sender_id,
            sender_role=new_msg.sender_role,
            sender_name=get_user_display_name(user),
            message=new_msg.message,
            created_at=new_msg.created_at,
        )

    def update_status(self, db: Session, ticket_id: int, user: User, new_status: TicketStatus) -> SupportTicketOut:
        """Updates ticket lifecycle status (REQ-32 / AC-09-05)."""
        if user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=403,
                detail="Only administrators can update ticket status.",
            )

        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found.")

        ticket.status = new_status.value
        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
        return serialize_ticket_out(ticket)

    def list_customer_tickets(
        self,
        db: Session,
        customer_id: int,
        status: Optional[str] = None,
        ticket_type: Optional[str] = None,
    ) -> list[SupportTicketOut]:
        """Lists tickets owned by the authenticated customer."""
        query = db.query(SupportTicket).filter(SupportTicket.customer_id == customer_id)
        if status:
            query = query.filter(SupportTicket.status == status)
        if ticket_type:
            query = query.filter(SupportTicket.ticket_type == ticket_type)

        tickets = query.order_by(SupportTicket.updated_at.desc()).all()
        return [serialize_ticket_out(t) for t in tickets]

    def list_admin_tickets(
        self,
        db: Session,
        status: Optional[str] = None,
        ticket_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[SupportTicketOut]:
        """Admin queue view across all customer tickets with filters."""
        query = db.query(SupportTicket)
        if status:
            query = query.filter(SupportTicket.status == status)
        if ticket_type:
            query = query.filter(SupportTicket.ticket_type == ticket_type)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    SupportTicket.ticket_number.ilike(term),
                    SupportTicket.subject.ilike(term),
                )
            )

        tickets = query.order_by(SupportTicket.updated_at.desc()).all()
        return [serialize_ticket_out(t) for t in tickets]

    def attach_file(self, db: Session, ticket_id: int, user: User, file: UploadFile) -> SupportFileOut:
        """Validates and uploads an attachment for a support ticket (REQ-30 / AC-09-02)."""
        ticket = self.verify_ticket_access(db, ticket_id, user)

        if ticket.status == TicketStatus.CLOSED.value:
            raise HTTPException(status_code=400, detail="Cannot upload attachments to a closed ticket.")

        current_count = db.query(SupportTicketFile).filter(SupportTicketFile.ticket_id == ticket.id).count()
        if current_count >= MAX_FILES_PER_SUPPORT:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum limit of {MAX_FILES_PER_SUPPORT} attachments reached for this ticket.",
            )

        try:
            content = file.file.read()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(exc)}")

        try:
            clean_name, content_type = validate_support_file_content(content, file.filename or 'attachment')
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        storage_key = self.storage.generate_support_storage_key(ticket.id, clean_name)
        try:
            self.storage.save_file(storage_key, content, content_type)
        except Exception as exc:
            logger.error(f"Failed to store attachment in storage: {exc}")
            raise HTTPException(status_code=500, detail="Failed to persist attachment to storage.")

        file_record = SupportTicketFile(
            ticket_id=ticket.id,
            uploaded_by_user_id=user.id,
            file_name=clean_name,
            storage_key=storage_key,
            content_type=content_type,
            file_size_bytes=len(content),
        )
        db.add(file_record)
        ticket.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(file_record)

        return SupportFileOut(
            id=file_record.id,
            ticket_id=file_record.ticket_id,
            file_name=file_record.file_name,
            content_type=file_record.content_type,
            file_size_bytes=file_record.file_size_bytes,
            is_previewable=is_previewable(file_record.file_name),
            created_at=file_record.created_at,
        )

    def retrieve_file(self, db: Session, ticket_id: int, file_id: int, user: User) -> tuple[bytes, str, str]:
        """Safely retrieves attachment bytes with tenant permission verification (AC-09-04)."""
        ticket = self.verify_ticket_access(db, ticket_id, user)

        file_rec = (
            db.query(SupportTicketFile)
            .filter(SupportTicketFile.id == file_id, SupportTicketFile.ticket_id == ticket.id)
            .first()
        )
        if not file_rec:
            raise HTTPException(status_code=404, detail="Attachment not found.")

        content = self.storage.get_file(file_rec.storage_key)
        return content, file_rec.file_name, file_rec.content_type
