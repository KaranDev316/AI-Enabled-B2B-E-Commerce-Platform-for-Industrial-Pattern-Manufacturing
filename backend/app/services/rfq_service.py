from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session as DBSession

from app.models import (
    CustomerProfile,
    Product,
    RFQ,
    RFQFile,
    RFQStatus,
    RFQType,
    User,
    UserRole,
)
from app.schemas.rfq import RFQCreateRequest
from app.services.file_validation import (
    ALLOWED_EXTENSIONS,
    MAX_FILES_PER_RFQ,
    is_previewable,
    sanitize_filename,
    validate_file_content,
)
from app.services.storage_service import get_storage_service



def generate_rfq_number(db: DBSession) -> str:
    """Generates a sequential human-readable RFQ reference number: e.g. RFQ-2026-0001."""
    year = datetime.now().year
    prefix = f'RFQ-{year}-'
    latest_rfq = (
        db.query(RFQ)
        .filter(RFQ.rfq_number.like(f'{prefix}%'))
        .order_by(desc(RFQ.id))
        .first()
    )

    if latest_rfq and latest_rfq.rfq_number:
        try:
            current_num = int(latest_rfq.rfq_number.split('-')[-1])
            next_num = current_num + 1
        except Exception:
            next_num = 1
    else:
        next_num = 1

    return f'{prefix}{next_num:04d}'


def create_rfq(db: DBSession, customer: User, data: RFQCreateRequest) -> RFQ:
    """REQ-08: Customer submits a Standard or Custom RFQ."""
    product_obj = None

    if data.rfq_type == RFQType.STANDARD:
        if not data.product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={'code': 'PRODUCT_REQUIRED', 'message': 'A valid product selection is required for standard RFQs.'},
            )
        product_obj = db.get(Product, data.product_id)
        if not product_obj or not product_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={'code': 'PRODUCT_NOT_AVAILABLE', 'message': 'Selected product is inactive or unavailable.'},
            )

    rfq_number = generate_rfq_number(db)

    new_rfq = RFQ(
        rfq_number=rfq_number,
        customer_id=customer.id,
        rfq_type=data.rfq_type.value,
        product_id=product_obj.id if product_obj else None,
        title=data.title.strip(),
        material=data.material.strip(),
        quantity=data.quantity,
        description=data.description.strip() if data.description else None,
        dimensions=data.dimensions.strip() if data.dimensions else None,
        specifications=data.specifications.strip() if data.specifications else None,
        target_delivery_date=data.target_delivery_date.strip() if data.target_delivery_date else None,
        notes=data.notes.strip() if data.notes else None,
        status=RFQStatus.SUBMITTED.value,
    )

    db.add(new_rfq)
    db.commit()
    db.refresh(new_rfq)
    return new_rfq


def get_customer_rfqs(db: DBSession, customer_id: int) -> list[RFQ]:
    """REQ-10: Retrieves RFQs belonging strictly to the authenticated customer."""
    return (
        db.query(RFQ)
        .filter(RFQ.customer_id == customer_id)
        .order_by(desc(RFQ.created_at))
        .all()
    )


def get_rfq_details(db: DBSession, rfq_id: int, user: User) -> dict:
    """REQ-10 / AC-03-08: Customer and Admin can inspect saved RFQ; unrelated customers blocked."""
    rfq = db.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'RFQ_NOT_FOUND', 'message': 'Requested RFQ does not exist.'},
        )

    user_role = user.role.value if isinstance(user.role, UserRole) else user.role

    # Tenant isolation
    if user_role == UserRole.CUSTOMER.value and rfq.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'You do not have permission to view this RFQ.'},
        )

    if user_role == UserRole.EMPLOYEE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Employee access to unassigned RFQs is restricted.'},
        )

    customer_user = rfq.customer
    customer_profile = customer_user.customer_profile if customer_user else None

    file_list = [
        {
            'id': f.id,
            'file_name': f.file_name,
            'content_type': f.content_type,
            'file_size_bytes': f.file_size_bytes,
            'created_at': f.created_at,
            'can_preview': is_previewable(f.file_name),
        }
        for f in rfq.files
    ]

    return {
        'id': rfq.id,
        'rfq_number': rfq.rfq_number,
        'customer_id': rfq.customer_id,
        'rfq_type': rfq.rfq_type,
        'product_id': rfq.product_id,
        'title': rfq.title,
        'material': rfq.material,
        'quantity': rfq.quantity,
        'description': rfq.description,
        'dimensions': rfq.dimensions,
        'specifications': rfq.specifications,
        'target_delivery_date': rfq.target_delivery_date,
        'notes': rfq.notes,
        'status': rfq.status,
        'created_at': rfq.created_at,
        'updated_at': rfq.updated_at,
        'customer_email': customer_user.email if customer_user else '',
        'customer_company': customer_profile.company_name if customer_profile else None,
        'customer_contact': customer_profile.contact_person if customer_profile else None,
        'customer_phone': customer_profile.phone if customer_profile else None,
        'product_name': rfq.product.name if rfq.product else None,
        'files': file_list,
    }


def list_admin_rfqs(
    db: DBSession,
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> list[dict]:
    """REQ-10: Admin lists all customer RFQs with search and filters."""
    query = db.query(RFQ).join(User, RFQ.customer_id == User.id).outerjoin(CustomerProfile, User.id == CustomerProfile.user_id)

    if status_filter:
        query = query.filter(RFQ.status == status_filter)

    if type_filter:
        query = query.filter(RFQ.rfq_type == type_filter)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(RFQ.rfq_number).like(term),
                func.lower(RFQ.title).like(term),
                func.lower(User.email).like(term),
                func.lower(CustomerProfile.company_name).like(term),
            )
        )

    rfqs = query.order_by(desc(RFQ.created_at)).all()
    results = []
    for r in rfqs:
        results.append(get_rfq_details(db, r.id, user=User(id=0, role=UserRole.ADMIN.value, email='')))
    return results


def update_rfq_status(db: DBSession, rfq_id: int, new_status: str) -> RFQ:
    """Admin transitions RFQ status (e.g. submitted -> under_review)."""
    rfq = db.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'RFQ_NOT_FOUND', 'message': 'Requested RFQ does not exist.'},
        )
    rfq.status = new_status
    db.commit()
    db.refresh(rfq)
    return rfq


def attach_rfq_file(
    db: DBSession,
    rfq_id: int,
    user: User,
    file_name: str,
    content: bytes,
    claimed_content_type: Optional[str] = None,
) -> RFQFile:
    """REQ-09 / AC-03-04: Owning customer attaches drawing/CAD file (max 2 per RFQ)."""
    # Verify RFQ exists and belongs to customer
    rfq = db.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'RFQ_NOT_FOUND', 'message': 'Requested RFQ does not exist.'},
        )

    user_role = user.role.value if isinstance(user.role, UserRole) else user.role
    if user_role != UserRole.CUSTOMER.value or rfq.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Only the owning customer can attach files to this RFQ.'},
        )

    if rfq.status != RFQStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'RFQ_NOT_EDITABLE', 'message': 'Attachments can only be added while RFQ is submitted.'},
        )

    # Concurrency and 2-file limit check
    current_files_count = db.query(func.count(RFQFile.id)).filter(RFQFile.rfq_id == rfq_id).scalar() or 0
    if current_files_count >= MAX_FILES_PER_RFQ:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'MAX_FILES_EXCEEDED', 'message': f'An RFQ can hold at most {MAX_FILES_PER_RFQ} attached files.'},
        )

    clean_name = sanitize_filename(file_name)
    ext = Path(clean_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'code': 'UNSUPPORTED_FILE_TYPE',
                'message': f"File extension '{ext}' is not permitted. Allowed formats: PDF, PNG, JPG/JPEG, WEBP, STEP, IGES, STL, DWG, DXF.",
            },
        )

    # Validate file content integrity and magic bytes
    try:
        validate_file_content(content, ext)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'INVALID_FILE_CONTENT', 'message': str(val_err)},
        )

    content_type = ALLOWED_EXTENSIONS.get(ext, claimed_content_type or 'application/octet-stream')

    storage_service = get_storage_service()
    storage_key = storage_service.generate_storage_key(rfq_id=rfq_id, original_filename=clean_name)

    try:
        storage_service.save_file(storage_key=storage_key, content=content, content_type=content_type)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={'code': 'STORAGE_FAILURE', 'message': f'Failed to store uploaded file: {str(exc)}'},
        )

    rfq_file = RFQFile(
        rfq_id=rfq_id,
        uploaded_by_user_id=user.id,
        file_name=clean_name,
        storage_key=storage_key,
        content_type=content_type,
        file_size_bytes=len(content),
    )

    try:
        db.add(rfq_file)
        db.commit()
        db.refresh(rfq_file)
    except Exception:
        db.rollback()
        # Clean up storage if database commit failed
        storage_service.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={'code': 'DATABASE_ERROR', 'message': 'Failed to save attachment metadata.'},
        )

    return rfq_file


def get_rfq_file_data(db: DBSession, rfq_id: int, file_id: int, user: User) -> tuple[RFQFile, bytes]:
    """REQ-09 / AC-03-06: Authorized customer or Admin retrieves file bytes."""
    rfq = db.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'RFQ_NOT_FOUND', 'message': 'Requested RFQ does not exist.'},
        )

    user_role = user.role.value if isinstance(user.role, UserRole) else user.role

    # Tenant isolation
    if user_role == UserRole.CUSTOMER.value and rfq.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'You do not have permission to access files on this RFQ.'},
        )

    if user_role == UserRole.EMPLOYEE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Employee access to unassigned RFQ files is restricted.'},
        )

    rfq_file = db.get(RFQFile, file_id)
    if not rfq_file or rfq_file.rfq_id != rfq_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'FILE_NOT_FOUND', 'message': 'Requested attachment does not exist.'},
        )

    storage_service = get_storage_service()
    try:
        data = storage_service.get_file(rfq_file.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'FILE_DATA_UNAVAILABLE', 'message': f'Attachment content unavailable: {str(exc)}'},
        )

    return rfq_file, data


def delete_rfq_file(db: DBSession, rfq_id: int, file_id: int, user: User) -> None:
    """REQ-09: Owning customer removes attachment while RFQ is submitted."""
    rfq = db.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'RFQ_NOT_FOUND', 'message': 'Requested RFQ does not exist.'},
        )

    user_role = user.role.value if isinstance(user.role, UserRole) else user.role
    if user_role != UserRole.CUSTOMER.value or rfq.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={'code': 'FORBIDDEN', 'message': 'Only the owning customer can delete attachments.'},
        )

    if rfq.status != RFQStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'code': 'RFQ_NOT_EDITABLE', 'message': 'Attachments cannot be removed once RFQ is under review or quoted.'},
        )

    rfq_file = db.get(RFQFile, file_id)
    if not rfq_file or rfq_file.rfq_id != rfq_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={'code': 'FILE_NOT_FOUND', 'message': 'Requested attachment does not exist.'},
        )

    storage_service = get_storage_service()
    storage_service.delete_file(rfq_file.storage_key)

    db.delete(rfq_file)
    db.commit()

