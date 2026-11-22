import re
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_employee, require_admin, verify_csrf_token, verify_trusted_origin
from app.models import User, ProductionJob
from app.issue_models import ProductionIssue, ProductionIssueFile, ProductionIssueEvent
from app.schemas.production_issue import IssueInput, IssueHandlingInput
from app.services.storage_service import get_storage_service
from app.services.file_validation import MAX_FILE_SIZE_BYTES, validate_support_file_content

router = APIRouter(prefix='/api/production/issues', tags=['Production issues'])
mutations = [Depends(verify_trusted_origin), Depends(verify_csrf_token)]
logger = logging.getLogger(__name__)

def permitted(db, issue_id, actor):
    issue = db.get(ProductionIssue, issue_id)
    if not issue or (actor.role != 'admin' and (actor.role != 'employee' or issue.employee_id != actor.id)):
        raise HTTPException(404, 'Issue not found.')
    return issue

def view(db, issue):
    files = db.query(ProductionIssueFile).filter_by(issue_id=issue.id).order_by(ProductionIssueFile.id).all()
    events = db.query(ProductionIssueEvent).filter_by(issue_id=issue.id).order_by(ProductionIssueEvent.id).all()
    return {**{k:getattr(issue,k) for k in ('id','employee_id','job_id','issue_type','title','description','priority','status','version','created_at','updated_at')},
        'files':[{'id':f.id, 'file_name':f.file_name, 'content_type':f.content_type, 'file_size_bytes':f.file_size_bytes,
                  'url':f'/api/production/issues/{issue.id}/files/{f.id}'} for f in files],
        'history':[{'id':e.id,'status':e.status,'note':e.note,'created_at':e.created_at} for e in events]}

@router.get('')
def listing(db:Session=Depends(get_db), actor:User=Depends(get_current_user)):
    if actor.role not in ('admin','employee'): raise HTTPException(403, 'Employee or Admin access required.')
    query = db.query(ProductionIssue)
    if actor.role != 'admin': query = query.filter_by(employee_id=actor.id)
    return [view(db,i) for i in query.order_by(ProductionIssue.id.desc()).all()]

@router.post('', dependencies=mutations, status_code=201)
async def create(title:str=Form(...), description:str=Form(...), issue_type:str=Form(...), priority:str=Form(...),
                 job_id:int|None=Form(None), files:list[UploadFile]=File(default=[]),
                 db:Session=Depends(get_db), actor:User=Depends(require_employee), storage=Depends(get_storage_service)):
    try: data = IssueInput(title=title,description=description,issue_type=issue_type,priority=priority,job_id=job_id)
    except ValidationError: raise HTTPException(422,'Provide a valid issue type, title (3–200 characters), description (10–10000 characters), priority and optional job.') from None
    if data.job_id:
        job = db.get(ProductionJob, data.job_id)
        if not job or job.employee_id != actor.id: raise HTTPException(404,'Assigned job not found.')
    if len(files)>2: raise HTTPException(422,'Attach a maximum of two files per issue.')
    validated=[]
    for file in files:
        content=await file.read(MAX_FILE_SIZE_BYTES+1)
        try: name,content_type=validate_support_file_content(content,file.filename or '')
        except ValueError as exc: raise HTTPException(422,str(exc)) from None
        validated.append((name,content_type,content))
    if validated and not storage.is_supabase_configured():
        raise HTTPException(503,'Configure private Supabase Storage before attaching issue files.')
    issue=ProductionIssue(employee_id=actor.id, **data.model_dump(),status='open',version=0)
    keys=[]
    try:
        db.add(issue);db.flush()
        for name,content_type,content in validated:
            key=f'issues/{issue.id}/{uuid4().hex}{Path(name).suffix.lower()}'
            keys.append(key) # Include ambiguous uploads in compensation.
            storage.save_file(key,content,content_type)
            db.add(ProductionIssueFile(issue_id=issue.id,storage_key=key,file_name=name,content_type=content_type,file_size_bytes=len(content)))
        db.add(ProductionIssueEvent(issue_id=issue.id,actor_id=actor.id,status='open',note='Issue reported.'))
        db.flush(); result=view(db,issue);db.commit()
        return result
    except Exception:
        db.rollback()
        for key in keys:
            try: storage.delete_file(key)
            except Exception: logger.warning('Issue attachment cleanup could not be confirmed.')
        raise HTTPException(503,'Issue could not be saved. Refresh your reported issues before retrying.') from None

@router.get('/{issue_id}')
def detail(issue_id:int,db:Session=Depends(get_db),actor:User=Depends(get_current_user)):
    return view(db,permitted(db,issue_id,actor))

@router.patch('/{issue_id}', dependencies=mutations)
def handle(issue_id:int,data:IssueHandlingInput,db:Session=Depends(get_db),actor:User=Depends(require_admin)):
    issue=permitted(db,issue_id,actor)
    try:
        result=db.execute(update(ProductionIssue).where(ProductionIssue.id==issue.id,ProductionIssue.version==data.expected_version)
            .values(status=data.status,version=ProductionIssue.version+1).execution_options(synchronize_session=False))
        if result.rowcount!=1: raise HTTPException(409,'Issue changed. Refresh before saving your handling update.')
        db.add(ProductionIssueEvent(issue_id=issue.id,actor_id=actor.id,status=data.status,note=data.note))
        db.flush();db.commit();db.refresh(issue)
    except HTTPException: db.rollback();raise
    except SQLAlchemyError: db.rollback();raise HTTPException(503,'Handling update could not be saved.') from None
    return view(db,issue)

@router.get('/{issue_id}/files/{file_id}')
def attachment(issue_id:int,file_id:int,preview:bool=False,db:Session=Depends(get_db),
               actor:User=Depends(get_current_user),storage=Depends(get_storage_service)):
    permitted(db,issue_id,actor)
    file=db.query(ProductionIssueFile).filter_by(id=file_id,issue_id=issue_id).first()
    if not file: raise HTTPException(404,'File not found.')
    try: content=storage.get_file(file.storage_key)
    except FileNotFoundError: raise HTTPException(404,'File unavailable.') from None
    except Exception: raise HTTPException(503,'Private storage is unavailable.') from None
    disposition='inline' if preview else 'attachment'
    return Response(content,media_type=file.content_type,headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
        'Content-Disposition':f"{disposition}; filename=\"{re.sub(r'[^A-Za-z0-9._ -]', '_', Path(file.file_name).name)}\"; filename*=UTF-8''{quote(file.file_name,safe='')}"})
