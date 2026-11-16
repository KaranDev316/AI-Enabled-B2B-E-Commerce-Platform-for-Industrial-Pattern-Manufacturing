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
from app.models import User
from app.schemas.rfq import (
    RFQCreateRequest,
    RFQDetailResponse,
    RFQFileOut,
    RFQResponse,
    RFQStatusUpdateRequest,
)
from app.services.file_validation import is_previewable
from app.services.rfq_service import (
    attach_rfq_file,
    create_rfq,
    delete_rfq_file,
    get_customer_rfqs,
    get_rfq_details,
    get_rfq_file_data,
    list_admin_rfqs,
    update_rfq_status,
)

router = APIRouter(prefix='/api', tags=['RFQs'])


@router.post(
    '/rfqs',
    response_model=RFQResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def submit_rfq(
    data: RFQCreateRequest,
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-08: Customer submits a 3-step Standard or Custom RFQ."""
    created = create_rfq(db, customer=current_user, data=data)
    return RFQResponse.model_validate(created)


@router.get('/rfqs/my', response_model=list[RFQResponse])
def get_my_rfqs(
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-10: Authenticated customer retrieves their own submitted RFQs."""
    rfqs = get_customer_rfqs(db, customer_id=current_user.id)
    return [RFQResponse.model_validate(r) for r in rfqs]


@router.get('/rfqs/{rfq_id}', response_model=RFQDetailResponse)
def get_single_rfq(
    rfq_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-10 / AC-03-08: Customer or Admin views single RFQ specifications."""
    details = get_rfq_details(db, rfq_id=rfq_id, user=current_user)
    return RFQDetailResponse.model_validate(details)


@router.get('/admin/rfqs', response_model=list[RFQDetailResponse])
def admin_list_rfqs(
    status: Optional[str] = Query(None, description='Filter by RFQ status'),
    rfq_type: Optional[str] = Query(None, description='Filter by standard or custom type'),
    search: Optional[str] = Query(None, description='Search by reference, company, or part name'),
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-10: Admin inspects all incoming customer RFQs with search and filters."""
    records = list_admin_rfqs(
        db, status_filter=status, type_filter=rfq_type, search=search
    )
    return [RFQDetailResponse.model_validate(r) for r in records]


@router.patch(
    '/admin/rfqs/{rfq_id}/status',
    response_model=RFQDetailResponse,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def admin_update_rfq_status(
    rfq_id: int,
    data: RFQStatusUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: DBSession = Depends(get_db),
):
    """REQ-10: Admin transitions RFQ review lifecycle."""
    update_rfq_status(db, rfq_id=rfq_id, new_status=data.status.value)
    details = get_rfq_details(db, rfq_id=rfq_id, user=current_admin)
    return RFQDetailResponse.model_validate(details)


@router.post(
    '/rfqs/{rfq_id}/files',
    response_model=RFQFileOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
async def upload_rfq_file(
    rfq_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-09 / AC-03-04: Customer uploads technical drawings/CAD files (max 2 per RFQ, 20 MB each)."""
    content = await file.read()
    rfq_file = attach_rfq_file(
        db=db,
        rfq_id=rfq_id,
        user=current_user,
        file_name=file.filename or 'attachment',
        content=content,
        claimed_content_type=file.content_type,
    )
    return RFQFileOut(
        id=rfq_file.id,
        file_name=rfq_file.file_name,
        content_type=rfq_file.content_type,
        file_size_bytes=rfq_file.file_size_bytes,
        created_at=rfq_file.created_at,
        can_preview=is_previewable(rfq_file.file_name),
    )


@router.get('/rfqs/{rfq_id}/files', response_model=list[RFQFileOut])
def list_rfq_files(
    rfq_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-09 / REQ-10: Retrieve list of attached files on an RFQ for authorized user."""
    details = get_rfq_details(db, rfq_id=rfq_id, user=current_user)
    return [RFQFileOut.model_validate(f) for f in details.get('files', [])]


@router.get('/rfqs/{rfq_id}/files/{file_id}')
def stream_rfq_file(
    rfq_id: int,
    file_id: int,
    disposition: str = Query('inline', pattern='^(inline|attachment)$'),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """REQ-09 / AC-03-06: Authorized customer or Admin streams or downloads attachment."""
    rfq_file, file_bytes = get_rfq_file_data(
        db=db, rfq_id=rfq_id, file_id=file_id, user=current_user
    )

    headers = {
        'Content-Disposition': f'{disposition}; filename="{rfq_file.file_name}"',
        'Content-Type': rfq_file.content_type,
        'Content-Length': str(rfq_file.file_size_bytes),
        'Cache-Control': 'private, no-cache, no-store, must-revalidate',
        'X-Content-Type-Options': 'nosniff',
    }
    return Response(content=file_bytes, media_type=rfq_file.content_type, headers=headers)


@router.delete(
    '/rfqs/{rfq_id}/files/{file_id}',
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def remove_rfq_file(
    rfq_id: int,
    file_id: int,
    current_user: User = Depends(require_customer),
    db: DBSession = Depends(get_db),
):
    """REQ-09: Owning customer removes an attachment while RFQ is submitted."""
    delete_rfq_file(db=db, rfq_id=rfq_id, file_id=file_id, user=current_user)
    return {'status': 'deleted', 'file_id': file_id}

