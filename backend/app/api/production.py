import re
from pathlib import Path
from app.models_commercial import OrderCommercialSnapshot
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin, require_employee, require_customer, get_current_user, verify_csrf_token, verify_trusted_origin
from app.models import Order, User, RFQ, RFQFile, ProductionJob, JobStageHistory
from app.schemas.production import JobAssignmentInput, JobUpdateInput
from app.services.production_service import assign_job, update_job, job_for_actor
from app.services.production_settlement import get_settlement_gate
from app.services.storage_service import get_storage_service

router=APIRouter(prefix='/api/production',tags=['Production jobs'])
MUTATIONS=[Depends(verify_trusted_origin),Depends(verify_csrf_token)]


def job_view(db,job,internal=False):
    order=db.get(Order,job.order_id)
    rfq=db.get(RFQ,order.rfq_id) if order.rfq_id else None
    snapshot=db.query(OrderCommercialSnapshot).filter_by(order_id=order.id).first()
    events=db.query(JobStageHistory).filter_by(job_id=job.id).order_by(JobStageHistory.id).all()
    result={'id':job.id,'order_id':order.id,'order_number':order.order_number,'order_status':order.status,
        'title':snapshot.product_summary if snapshot else (rfq.title if rfq else order.order_number),'material':rfq.material if rfq else None,
        'quantity':snapshot.quantity if snapshot else (rfq.quantity if rfq else None),'stage':job.stage,'progress':job.progress,'is_paused':job.is_paused,
        'created_at':job.created_at,'updated_at':job.updated_at,
        'history':[{'id':h.id,'from_stage':h.from_stage,'to_stage':h.to_stage,'action':h.action,
                    'progress':h.progress,'is_paused':h.is_paused,'created_at':h.created_at,
                    'message':h.customer_note} for h in events]}
    if internal:
        employee=db.get(User,job.employee_id)
        result.update(employee_id=job.employee_id,employee_name=employee.employee_profile.full_name if employee.employee_profile else employee.email,
            instructions=job.instructions,version=job.version,
            specifications=rfq.specifications if rfq else None,dimensions=rfq.dimensions if rfq else None,
            files=[{'id':f.id,'name':f.file_name,'content_type':f.content_type,'url':f'/api/production/jobs/{job.id}/files/{f.id}'} for f in rfq.files] if rfq else [])
        for item,event in zip(result['history'],events):item.update(note=event.note,actor_id=event.actor_id)
    return result


@router.get('/admin/board')
def admin_board(db:Session=Depends(get_db),actor:User=Depends(require_admin),gate=Depends(get_settlement_gate)):
    orders=db.query(Order).order_by(Order.id.desc()).all()
    jobs=db.query(ProductionJob).order_by(ProductionJob.id.desc()).all()
    employees=db.query(User).filter_by(role='employee',is_active=True).order_by(User.id).all()
    assigned={j.order_id for j in jobs}
    return {'assignment_available':gate.available,'integration_message':None if gate.available else gate.message,
        'orders':[{'id':o.id,'order_number':o.order_number,'status':o.status,'has_job':o.id in assigned,'fully_settled':gate.is_fully_settled(db,o)} for o in orders],
        'employees':[{'id':e.id,'name':e.employee_profile.full_name if e.employee_profile else e.email} for e in employees],
        'jobs':[job_view(db,j,True) for j in jobs]}

@router.post('/admin/jobs',dependencies=MUTATIONS,status_code=201)
def assign(data:JobAssignmentInput,db:Session=Depends(get_db),actor:User=Depends(require_admin),gate=Depends(get_settlement_gate)):
    return job_view(db,assign_job(db,data,actor,gate),True)

@router.get('/employee/jobs')
def employee_jobs(db:Session=Depends(get_db),actor:User=Depends(require_employee)):
    jobs=db.query(ProductionJob).filter_by(employee_id=actor.id).order_by(ProductionJob.id.desc()).all()
    return [job_view(db,j,True) for j in jobs]

@router.get('/jobs/{job_id}')
def job_detail(job_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    return job_view(db,job_for_actor(db,job_id,actor),True)

@router.patch('/employee/jobs/{job_id}',dependencies=MUTATIONS)
def progress(job_id:int,data:JobUpdateInput,db:Session=Depends(get_db),actor:User=Depends(require_employee)):
    return job_view(db,update_job(db,job_id,data,actor),True)

@router.get('/customer/orders')
def customer_tracking(db:Session=Depends(get_db),actor:User=Depends(require_customer)):
    orders=db.query(Order).filter_by(customer_id=actor.id).order_by(Order.id.desc()).all()
    return [{'id':o.id,'order_number':o.order_number,'status':o.status,
             'production':job_view(db,job,False) if (job:=db.query(ProductionJob).filter_by(order_id=o.id).first()) else None} for o in orders]

@router.get('/jobs/{job_id}/files/{file_id}')
def job_file(job_id:int,file_id:int,preview:bool=False,db:Session=Depends(get_db),actor:User=Depends(get_current_user),storage=Depends(get_storage_service)):
    job=job_for_actor(db,job_id,actor)
    order=db.get(Order,job.order_id)
    file=db.query(RFQFile).filter_by(id=file_id,rfq_id=order.rfq_id).first() if order.rfq_id else None
    if not file:raise HTTPException(404,'File not found.')
    try:content=storage.get_file(file.storage_key)
    except FileNotFoundError:raise HTTPException(404,'File unavailable.') from None
    except Exception:raise HTTPException(503,'File storage is unavailable.') from None
    disposition='inline' if preview and file.content_type in ('image/jpeg','image/png','application/pdf') else 'attachment'
    return Response(content,media_type=file.content_type,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
        'Content-Disposition':f"{disposition}; filename=\"{re.sub(r'[^A-Za-z0-9._ -]', '_', Path(file.file_name).name)}\"; filename*=UTF-8''{quote(file.file_name,safe='')}"})
