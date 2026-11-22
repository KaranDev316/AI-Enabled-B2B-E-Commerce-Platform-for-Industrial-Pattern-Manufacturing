from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Order, User, ProductionJob, JobStageHistory
from app.models_commercial import OrderStatusEvent

WORK_STAGES = ('design_and_tooling','machining_production')


def job_for_actor(db, job_id, actor):
    job=db.get(ProductionJob,job_id)
    if not job or (actor.role != 'admin' and (actor.role != 'employee' or job.employee_id != actor.id)):
        raise HTTPException(404,'Job not found.')
    return job


def assign_job(db,data,actor,gate):
    order=db.query(Order).filter_by(id=data.order_id).populate_existing().with_for_update().first()
    if not order: raise HTTPException(404,'Order not found.')
    if order.status != 'confirmed': raise HTTPException(409,'Only confirmed, fully settled orders can enter production.')
    if not gate.available: raise HTTPException(503,gate.message)
    if not gate.is_fully_settled(db,order): raise HTTPException(409,'This order has not been fully settled.')
    employee=db.query(User).filter_by(id=data.employee_id).with_for_update().first()
    if not employee or employee.role != 'employee' or not employee.is_active:
        raise HTTPException(422,'Select an active Employee account.')
    if db.query(ProductionJob).filter_by(order_id=order.id).first():
        raise HTTPException(409,'This order already has a production job.')
    job=ProductionJob(order_id=order.id,employee_id=employee.id,instructions=data.instructions,
                      stage='design_and_tooling',progress=0,is_paused=False,version=0)
    try:
        db.add(job);db.flush()
        order.status = 'in_production'
        db.add(OrderStatusEvent(order_id=order.id, actor_user_id=actor.id, event_type='production_assigned', from_status='confirmed', to_status='in_production', note='Assigned to production.'))
        db.add(JobStageHistory(job_id=job.id,from_stage=None,to_stage=job.stage,action='assigned',
            progress=0,is_paused=False,actor_id=actor.id,note='Production job assigned.',customer_note=None))
        db.flush();db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'This order already has a production job.') from None
    except SQLAlchemyError:
        db.rollback();raise HTTPException(503,'Assignment could not be confirmed. Refresh before retrying.') from None
    return job


def update_job(db,job_id,data,actor):
    job=job_for_actor(db,job_id,actor)
    order=db.get(Order,job.order_id)
    if order.status not in ('confirmed','in_production'):
        raise HTTPException(409,'This order is not eligible for active production updates.')
    if actor.role != 'employee': raise HTTPException(403,'Only the assigned Employee can report production progress.')
    if job.version != data.expected_version: raise HTTPException(409,'This job changed. Refresh before updating it.')
    if job.stage not in WORK_STAGES: raise HTTPException(409,'Work is under quality review or completed. Employee changes are locked.')
    stage=job.stage;paused=job.is_paused;progress=data.progress
    if data.action == 'pause':
        if paused: raise HTTPException(409,'Job is already paused.')
        paused=True
    elif data.action == 'resume':
        if not paused: raise HTTPException(409,'Job is not paused.')
        paused=False
    else:
        if paused: raise HTTPException(409,'Resume the job before updating or advancing work.')
        if data.action == 'advance':
            if stage == 'design_and_tooling': stage='machining_production'
            else:
                if progress != 100: raise HTTPException(422,'Set progress to 100 before submitting Quality Check.')
                stage='quality_check'
    if data.action in ('pause','resume') and progress != job.progress:
        raise HTTPException(422,'Pause/resume must retain the current progress.')
    old_stage=job.stage
    try:
        result=db.execute(update(ProductionJob).where(
            ProductionJob.id==job.id,ProductionJob.version==data.expected_version,
            ProductionJob.employee_id==actor.id,ProductionJob.stage.in_(WORK_STAGES)
        ).values(stage=stage,is_paused=paused,progress=progress,version=ProductionJob.version+1)
         .execution_options(synchronize_session=False))
        if result.rowcount != 1: raise HTTPException(409,'This job changed. Refresh before updating it.')
        db.add(JobStageHistory(job_id=job.id,from_stage=old_stage,to_stage=stage,action=data.action,
            progress=progress,is_paused=paused,actor_id=actor.id,note=data.note,customer_note=data.customer_note))
        db.flush();db.commit()
    except HTTPException:
        db.rollback();raise
    except SQLAlchemyError:
        db.rollback();raise HTTPException(503,'Progress could not be confirmed. Refresh before retrying.') from None
    db.refresh(job)
    return job
