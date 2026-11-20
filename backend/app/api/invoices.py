from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.commercial import InvoiceDetailResponse, InvoiceSummaryResponse
from app.services.commercial_service import (
    get_invoice_detail_for_user,
    list_invoices_for_user,
    render_demo_invoice_html,
)

router = APIRouter(prefix='/api/invoices', tags=['invoices'])


@router.get('', response_model=list[InvoiceSummaryResponse])
def list_invoices(
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_invoices_for_user(db, current_user, status_filter=status, search=search)


@router.get('/{invoice_id}', response_model=InvoiceDetailResponse)
def get_invoice_detail(
    invoice_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_invoice_detail_for_user(db, invoice_id, current_user)


@router.get('/{invoice_id}/download')
def download_demo_invoice(
    invoice_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    detail = get_invoice_detail_for_user(db, invoice_id, current_user)
    try:
        html_content = render_demo_invoice_html(detail)
    except Exception:
        raise HTTPException(503, detail={'code':'INVOICE_DOWNLOAD_UNAVAILABLE', 'message':'Unable to generate the demo invoice. Please try again.'}) from None
    filename = f'KPC-DEMO-{detail.invoice_number}.html'
    return Response(
        content=html_content.encode('utf-8'),
        media_type='text/html; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'X-Content-Type-Options': 'nosniff',
        },
    )
