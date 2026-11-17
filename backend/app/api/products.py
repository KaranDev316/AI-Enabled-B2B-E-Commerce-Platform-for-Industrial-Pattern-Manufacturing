from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import Product
from app.schemas.rfq import ProductSummaryResponse

router = APIRouter(prefix='/api/products', tags=['Products & Catalogue'])


@router.get('', response_model=list[ProductSummaryResponse])
def get_active_products(
    db: DBSession = Depends(get_db),
):
    """REQ-05: Returns active catalogue products for public browsing and standard RFQs."""
    products = (
        db.query(Product)
        .filter(Product.is_active.is_(True))
        .order_by(Product.name.asc())
        .all()
    )
    return [ProductSummaryResponse.model_validate(p).model_copy(update={"category_name": p.category.name if p.category else None}) for p in products]
