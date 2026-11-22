from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import update, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import InventoryMaterial, StockAdjustment

MAX_QUANTITY = Decimal('99999999999.999')


def material_by_id(db, material_id, lock=False):
    query = db.query(InventoryMaterial).filter_by(id=material_id)
    if lock: query = query.with_for_update()
    material = query.first()
    if not material: raise HTTPException(404, 'Material not found.')
    return material


def save_material(db, data, material_id=None):
    material = material_by_id(db, material_id, lock=True) if material_id else None
    if material is not None and material.unit != data.unit:
        raise HTTPException(422, 'A material unit cannot be changed. Create a separate material to keep stock history meaningful.')
    duplicate = db.query(InventoryMaterial).filter_by(code=data.code).first()
    if duplicate and (material is None or duplicate.id != material.id):
        raise HTTPException(409, 'This material code is already in use.')
    if material is None:
        material = InventoryMaterial(quantity=Decimal('0'))
        db.add(material)
    for field, value in data.model_dump().items(): setattr(material, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This material code is already in use.') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Material could not be saved. Please retry.') from None
    db.refresh(material)
    return material


def matching_retry(previous, material_id, data, actor):
    if (previous.material_id != material_id or previous.actor_id != actor.id or
        previous.direction != data.direction or previous.amount != data.amount or previous.reason != data.reason):
        raise HTTPException(409, 'This adjustment request ID was already used with different details. Refresh the form and retry.')
    return previous


def adjust_stock(db, material_id, data, actor):
    previous = db.query(StockAdjustment).filter_by(request_id=str(data.request_id)).first()
    if previous: return matching_retry(previous, material_id, data, actor)
    material = material_by_id(db, material_id, lock=True)
    if material.unit == 'piece' and data.amount != data.amount.to_integral_value():
        raise HTTPException(422, 'Piece quantities must be whole numbers.')
    delta = data.amount if data.direction == 'addition' else -data.amount
    try:
        # SQL arithmetic and guarded range check prevent lost updates and overspending even
        # on databases where SELECT FOR UPDATE is not available. History is in this transaction.
        next_quantity = func.round(InventoryMaterial.quantity + delta, 3)
        statement = (update(InventoryMaterial).where(
            InventoryMaterial.id == material_id,
            next_quantity >= 0,
            next_quantity <= MAX_QUANTITY,
        ).values(quantity=next_quantity).returning(InventoryMaterial.quantity))
        after = db.execute(statement.execution_options(synchronize_session=False)).scalar_one_or_none()
        if after is None:
            raise HTTPException(409, 'Insufficient stock for this deduction, or the maximum stock quantity would be exceeded. Refresh and check the available balance.')
        after = Decimal(after).quantize(Decimal('0.001'))
        adjustment = StockAdjustment(request_id=str(data.request_id), material_id=material.id,
            material_code=material.code, unit=material.unit, direction=data.direction, amount=data.amount.quantize(Decimal('0.001')),
            quantity_before=after-delta, quantity_after=after, reason=data.reason,
            actor_id=actor.id, actor_email=actor.email)
        db.add(adjustment)
        db.flush()
        db.commit()
        db.expire(material)
        return adjustment
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        previous = db.query(StockAdjustment).filter_by(request_id=str(data.request_id)).first()
        if previous: return matching_retry(previous, material_id, data, actor)
        raise HTTPException(409, 'Stock changed while saving. Refresh and retry.') from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, 'Could not confirm the stock adjustment. Refresh or retry the same request; its request ID prevents a duplicate adjustment.') from None
