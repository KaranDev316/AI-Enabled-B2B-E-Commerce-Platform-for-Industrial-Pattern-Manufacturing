from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.dependencies import (
    get_current_user,
    require_customer,
    verify_csrf_token,
    verify_trusted_origin,
)
from app.models import User
from app.schemas.commercial import (
    OrderCancelRequest,
    OrderCancelResponse,
    OrderDetailResponse,
    OrderSummaryResponse,
)
from app.services.commercial_service import (
    cancel_unpaid_order,
    get_order_detail_for_user,
    list_orders_for_user,
)

router = APIRouter(prefix='/api/orders', tags=['orders'])


@router.get('', response_model=list[OrderSummaryResponse])
def list_orders(
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_orders_for_user(db, current_user, status_filter=status, search=search)


@router.get('/{order_id}', response_model=OrderDetailResponse)
def get_order_detail(
    order_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_order_detail_for_user(db, order_id, current_user)


@router.post(
    '/{order_id}/cancel',
    response_model=OrderCancelResponse,
    dependencies=[Depends(verify_trusted_origin), Depends(verify_csrf_token)],
)
def cancel_order(
    order_id: int,
    payload: OrderCancelRequest = OrderCancelRequest(),
    db: DBSession = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    detail = cancel_unpaid_order(db, order_id, current_user, reason=payload.reason)
    db.commit()
    return OrderCancelResponse(
        order=detail,
        message='Unpaid order cancelled. Order history has been preserved.',
    )
