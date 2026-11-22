from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin, verify_csrf_token, verify_trusted_origin
from app.models import InventoryMaterial, StockAdjustment, User
from app.schemas.inventory import MaterialInput, MaterialResponse, AdjustmentInput, AdjustmentResponse
from app.services.inventory_service import save_material, material_by_id, adjust_stock

router = APIRouter(prefix='/api/admin/inventory', tags=['Manual inventory'], dependencies=[Depends(require_admin)])
MUTATIONS = [Depends(verify_trusted_origin), Depends(verify_csrf_token)]

@router.get('/materials', response_model=list[MaterialResponse])
def list_materials(db: Session = Depends(get_db)):
    return db.query(InventoryMaterial).order_by(InventoryMaterial.name, InventoryMaterial.id).all()

@router.get('/summary')
def stock_summary(db: Session = Depends(get_db)):
    materials = db.query(InventoryMaterial).all()
    return {'total': len(materials), **{status: sum(m.stock_status == status for m in materials)
            for status in ('in_stock', 'low_stock', 'out_of_stock')}}

@router.get('/materials/{material_id}', response_model=MaterialResponse)
def material_detail(material_id: int, db: Session = Depends(get_db)):
    return material_by_id(db, material_id)

@router.post('/materials', response_model=MaterialResponse, status_code=201, dependencies=MUTATIONS)
def create_material(data: MaterialInput, db: Session = Depends(get_db)):
    return save_material(db, data)

@router.put('/materials/{material_id}', response_model=MaterialResponse, dependencies=MUTATIONS)
def edit_material(material_id: int, data: MaterialInput, db: Session = Depends(get_db)):
    return save_material(db, data, material_id)

@router.get('/materials/{material_id}/adjustments', response_model=list[AdjustmentResponse])
def history(material_id: int, db: Session = Depends(get_db)):
    material_by_id(db, material_id)
    return db.query(StockAdjustment).filter_by(material_id=material_id).order_by(StockAdjustment.id.desc()).all()

@router.post('/materials/{material_id}/adjustments', response_model=AdjustmentResponse, dependencies=MUTATIONS)
def create_adjustment(material_id: int, data: AdjustmentInput, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    return adjust_stock(db, material_id, data, actor)
