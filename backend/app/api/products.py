from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DBSession, joinedload, selectinload

from app.database import get_db
from app.models import Product, ProductImage
from app.services.storage_service import StorageService
from app.services.catalogue_storage import get_catalogue_storage
from app.schemas.rfq import ProductSummaryResponse

router = APIRouter(prefix='/api/products', tags=['Products & Catalogue'])


@router.get('', response_model=list[ProductSummaryResponse])
def get_active_products(
    db: DBSession = Depends(get_db),
):
    """REQ-05: Returns active catalogue products for public browsing and standard RFQs."""
    products = (
        db.query(Product)
        .options(joinedload(Product.category), selectinload(Product.images))
        .filter(Product.is_active.is_(True))
        .order_by(Product.name.asc())
        .all()
    )
    return products


@router.get('/{slug}', response_model=ProductSummaryResponse)
def get_product(slug: str, db: DBSession = Depends(get_db)):
    product = (db.query(Product).options(joinedload(Product.category), selectinload(Product.images))
               .filter(Product.slug == slug, Product.is_active.is_(True)).first())
    # Keep existing numeric /products/:id links working while slugs are canonical.
    if product is None and slug.isdecimal() and len(slug) <= 10 and int(slug) <= 2147483647:
        product = (db.query(Product).options(joinedload(Product.category), selectinload(Product.images))
                   .filter(Product.id == int(slug), Product.is_active.is_(True)).first())
    if product is None:
        raise HTTPException(status_code=404, detail='Product not found or no longer available')
    return product


@router.get('/images/{image_id}')
def image_bytes(image_id: int, db: DBSession = Depends(get_db),
                storage: StorageService = Depends(get_catalogue_storage)):
    image = (db.query(ProductImage).join(Product)
             .filter(ProductImage.id == image_id, Product.is_active.is_(True)).first())
    if not image:
        raise HTTPException(404, 'Image not found.')
    try:
        content = storage.get_file(image.storage_key)
    except FileNotFoundError:
        raise HTTPException(404, 'Image unavailable.')
    except Exception:
        raise HTTPException(503, 'Image storage is unavailable.')
    return Response(content, media_type=image.content_type,
                    headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})
