"""S04: Admin catalogue writes. Public image delivery lives in products.py."""
import io
import logging
from pathlib import Path
import uuid
import warnings

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import require_admin, verify_csrf_token, verify_trusted_origin
from app.models import Category, Product, ProductImage
from app.schemas.catalogue import CategoryInput, CategoryResponse, ProductInput
from app.schemas.rfq import ProductSummaryResponse
from app.services.storage_service import StorageService
from app.services.catalogue_storage import CatalogueStorageError, get_catalogue_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/admin/catalogue', tags=['Admin catalogue'], dependencies=[Depends(require_admin)])
MUTATIONS = [Depends(verify_trusted_origin), Depends(verify_csrf_token)]
MAX_IMAGE_BYTES = 20 * 1024 * 1024


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A category name or product slug is already in use.')


def find_product(db, product_id, lock=False):
    query = db.query(Product).filter(Product.id == product_id)
    if lock:
        query = query.with_for_update()
    product = query.first()
    if not product:
        raise HTTPException(404, 'Product not found.')
    return product


@router.get('/categories', response_model=list[CategoryResponse])
def categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


def save_category(db, data, category=None):
    duplicate = db.query(Category).filter(func.lower(Category.name) == data.name.lower()).first()
    if duplicate and (category is None or duplicate.id != category.id):
        raise HTTPException(409, 'This category name is already in use.')
    if category is None:
        category = Category()
        db.add(category)
    category.name, category.description = data.name, data.description
    commit(db)
    db.refresh(category)
    return category


@router.post('/categories', response_model=CategoryResponse, status_code=201, dependencies=MUTATIONS)
def create_category(data: CategoryInput, db: Session = Depends(get_db)):
    return save_category(db, data)


@router.put('/categories/{category_id}', response_model=CategoryResponse, dependencies=MUTATIONS)
def update_category(category_id: int, data: CategoryInput, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(404, 'Category not found.')
    return save_category(db, data, category)


@router.get('/products', response_model=list[ProductSummaryResponse])
def products(db: Session = Depends(get_db)):
    return db.query(Product).options(selectinload(Product.images), selectinload(Product.category)).order_by(Product.name).all()


def save_product(db, data, product=None):
    if data.category_id is not None and db.get(Category, data.category_id) is None:
        raise HTTPException(422, 'Select an existing category.')
    if product is None:
        product = Product()
        db.add(product)
    for field, value in data.model_dump().items():
        setattr(product, field, value)
    commit(db)
    db.refresh(product)
    return product


@router.post('/products', response_model=ProductSummaryResponse, status_code=201, dependencies=MUTATIONS)
def create_product(data: ProductInput, db: Session = Depends(get_db)):
    return save_product(db, data)


@router.put('/products/{product_id}', response_model=ProductSummaryResponse, dependencies=MUTATIONS)
def update_product(product_id: int, data: ProductInput, db: Session = Depends(get_db)):
    # Never delete products or mutate RFQ/order records when editing the catalogue.
    return save_product(db, data, find_product(db, product_id, lock=True))


def validate_image(content: bytes, filename: str, content_type: str):
    ext = Path(filename).suffix.lower()
    formats = {'.jpg': ('JPEG', 'image/jpeg'), '.jpeg': ('JPEG', 'image/jpeg'), '.png': ('PNG', 'image/png')}
    if ext not in formats:
        raise HTTPException(422, 'Only JPG, JPEG and PNG images are allowed.')
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(422, 'Each image must be non-empty and no larger than 20 MB.')
    expected_format, expected_type = formats[ext]
    if content_type != expected_type:
        raise HTTPException(422, 'Image extension and content type do not match.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format != expected_format or image.width * image.height > 25_000_000:
                    raise ValueError('Invalid image format or dimensions.')
                image.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Invalid, damaged or excessively large image. Use a JPG/PNG of up to 25 megapixels.')
    return ext, expected_type


@router.post('/products/{product_id}/images', response_model=ProductSummaryResponse, dependencies=MUTATIONS)
def upload_images(product_id: int, files: list[UploadFile] = File(...),
                  db: Session = Depends(get_db), storage: StorageService = Depends(get_catalogue_storage)):
    if not 1 <= len(files) <= 2:
        raise HTTPException(422, 'Upload one or two images per submission.')
    # Read at most the permitted size plus one byte; validate all files before any writes.
    validated = []
    for file in files:
        content = file.file.read(MAX_IMAGE_BYTES + 1)
        ext, mime = validate_image(content, file.filename or '', file.content_type or '')
        validated.append((file, content, ext, mime))
    if not storage.is_supabase_configured():
        raise HTTPException(503, 'Configure private Supabase Storage in backend .env before uploading product images.')
    product = find_product(db, product_id, lock=True)
    attempted_keys = []
    stage = 'storage'
    try:
        for file, content, ext, mime in validated:
            key = f'catalogue/{product_id}/{uuid.uuid4().hex}{ext}'
            attempted_keys.append(key)
            storage.save_file(key, content, mime)
            db.add(ProductImage(product_id=product_id, storage_key=key,
                                file_name=Path((file.filename or '').replace('\\', '/')).name[:255],
                                content_type=mime, file_size_bytes=len(content)))
        stage = 'database'
        db.commit()
    except Exception as exc:
        logger.error('Catalogue upload failed at %s stage (%s).', stage, type(exc).__name__)
        db.rollback()
        for key in attempted_keys:
            try:
                storage.delete_file(key)
            except Exception:
                logger.error('Catalogue upload compensation failed for object %s; operator cleanup required.', key)
        if isinstance(exc, CatalogueStorageError):
            raise HTTPException(503, str(exc)) from None
        if stage == 'database':
            raise HTTPException(503, 'The upload reached storage but image metadata could not be saved to PostgreSQL. Run alembic upgrade head using the same backend settings, and check database access. No new image associations were saved.') from None
        raise HTTPException(503, 'Image storage failed unexpectedly. Check the backend terminal for the failure stage; no new image associations were saved.') from None
    db.refresh(product)
    return product


@router.delete('/products/{product_id}/images/{image_id}', status_code=204, dependencies=MUTATIONS)
def remove_image(product_id: int, image_id: int, db: Session = Depends(get_db),
                 storage: StorageService = Depends(get_catalogue_storage)):
    find_product(db, product_id, lock=True)
    image = db.query(ProductImage).filter_by(id=image_id, product_id=product_id).first()
    if not image:
        raise HTTPException(404, 'Image not found.')
    # Remove public association first. Never delete bytes while a live association remains.
    key = image.storage_key
    db.delete(image)
    commit(db)
    try:
        storage.delete_file(key)
    except Exception:
        logger.exception('Unreferenced catalogue image requires storage cleanup: %s', key)
    return Response(status_code=204)


@router.get('/products/{product_id}/images/{image_id}')
def admin_image(product_id: int, image_id: int, db: Session = Depends(get_db),
                storage: StorageService = Depends(get_catalogue_storage)):
    image = db.query(ProductImage).filter_by(id=image_id, product_id=product_id).first()
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
