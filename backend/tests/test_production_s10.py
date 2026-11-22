from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.database import Base
from app.models import User, Order, RFQ, RFQFile, ProductionJob, JobStageHistory
from app.schemas.production import JobAssignmentInput, JobUpdateInput
from app.services.production_service import assign_job, update_job
from app.services.production_settlement import get_settlement_gate
from app.services.storage_service import get_storage_service

ORIGIN='http://127.0.0.1:5173'
P='/api/production'

@pytest.fixture
def db_session(test_db_engine):
    connection=test_db_engine.connect();transaction=connection.begin()
    connection.exec_driver_sql('BEGIN')
    db=Session(bind=connection,expire_on_commit=False,autoflush=False,join_transaction_mode='create_savepoint')
    try:yield db
    finally:db.close();transaction.rollback();connection.close()

class TestSettlement:
    available=True
    message='Test-only ledger fixture'
    settled=True
    def is_fully_settled(self,db,order):return self.settled

@pytest.fixture
def gate(app_instance):
    gate=TestSettlement()
    app_instance.dependency_overrides[get_settlement_gate]=lambda:gate
    return gate

@pytest.fixture
def order(db_session,test_users):
    rfq=RFQ(rfq_number='S10-RFQ',customer_id=test_users['customer_1'].id,title='Pattern requirement',material='Wood',quantity=2,specifications='100 mm')
    db_session.add(rfq);db_session.flush()
    order=Order(order_number='S10-ORDER',customer_id=test_users['customer_1'].id,rfq_id=rfq.id,total_amount=100,status='confirmed')
    db_session.add(order);db_session.commit();return order

def login(client,role='admin',email=None):
    r=client.post('/api/auth/login',json={'email':email or f'{role}.one@example.test','password':role.title()+'@12345'},headers={'Origin':ORIGIN})
    assert r.status_code==200,r.text
    return {'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf_token']}

def assign(client,h,order,users,**extra):
    return client.post(P+'/admin/jobs',headers=h,json={'order_id':order.id,'employee_id':users['employee_1'].id,'instructions':'Only-internal work instructions',**extra})

def change(client,h,job,**extra):
    return client.patch(f"{P}/employee/jobs/{job['id']}",headers=h,json={'expected_version':job['version'],'action':'progress','progress':25,'note':'Only-internal progress note',**extra})

def assigned(client,test_users,order):
    h=login(client);r=assign(client,h,order,test_users);assert r.status_code==201,r.text;return r.json()

def test_default_gate_rejects_status_without_payment_ledger(client,test_users,order,db_session):
    h=login(client)
    board=client.get(P+'/admin/board').json()
    assert board['assignment_available'] is True
    assert assign(client,h,order,test_users).status_code==409
    assert db_session.query(ProductionJob).count()==0


def test_assign_once_and_employee_requirements(client,test_users,order,gate,db_session):
    h=login(client);r=assign(client,h,order,test_users)
    assert r.status_code==201,r.text
    job=r.json();assert job['stage']=='design_and_tooling';assert job['progress']==0
    assert job['instructions']=='Only-internal work instructions'
    assert job['specifications']=='100 mm'
    assert assign(client,h,order,test_users).status_code==409
    assert db_session.query(ProductionJob).count()==1
    assert db_session.query(JobStageHistory).count()==1
    login(client,'employee')
    assert client.get(P+'/employee/jobs').json()[0]['id']==job['id']

@pytest.mark.parametrize('status',['pending_payment','cancelled','closed'])
def test_ineligible_order_status(client,test_users,order,gate,db_session,status):
    order.status=status;db_session.commit();h=login(client)
    assert assign(client,h,order,test_users).status_code==409
    assert not db_session.query(ProductionJob).count()


def test_unpaid_and_bad_employee(client,test_users,order,gate,db_session):
    h=login(client);gate.settled=False
    assert assign(client,h,order,test_users).status_code==409
    gate.settled=True
    assert assign(client,h,order,test_users,employee_id=test_users['customer_1'].id).status_code==422
    test_users['employee_1'].is_active=False;db_session.commit()
    assert assign(client,h,order,test_users).status_code==422


def test_stage_progress_pause_resume_and_quality_lock(client,test_users,order,gate):
    job=assigned(client,test_users,order)
    h=login(client,'employee')
    r=change(client,h,job,progress=100);assert r.status_code==200;job=r.json()
    assert job['stage']=='design_and_tooling'  # 100% alone is never completion
    job=change(client,h,job,action='advance',progress=30).json()
    assert job['stage']=='machining_production'
    job=change(client,h,job,action='pause',progress=30,note='Machine requires attention').json()
    assert job['is_paused']
    assert change(client,h,job,progress=40).status_code==409
    job=change(client,h,job,action='resume',progress=30).json()
    assert not job['is_paused']
    assert change(client,h,job,action='advance',progress=99).status_code==422
    job=change(client,h,job,action='advance',progress=100,customer_note='Submitted for review').json()
    assert job['stage']=='quality_check'
    assert change(client,h,job,progress=100).status_code==409
    assert len(job['history'])==6
    assert job['history'][-1]['message']=='Submitted for review'


def test_stale_range_and_forbidden_action(client,test_users,order,gate):
    job=assigned(client,test_users,order);h=login(client,'employee')
    assert change(client,h,job,progress=101).status_code==422
    assert change(client,h,job,progress=-1).status_code==422
    assert change(client,h,job,action='completed').status_code==422
    assert change(client,h,job,progress=10).status_code==200
    assert change(client,h,job,progress=20).status_code==409
    assert client.get(f"{P}/jobs/{job['id']}").json()['progress']==10


def test_customer_isolation_and_internal_redaction(client,test_users,order,gate):
    job=assigned(client,test_users,order);h=login(client,'employee')
    change(client,h,job,customer_note='Machining planned')
    h=login(client,'customer')
    response=client.get(P+'/customer/orders')
    assert response.status_code==200
    public=response.json()[0]['production']
    assert public['progress']==25
    assert public['history'][-1]['message']=='Machining planned'
    assert 'instructions' not in public and 'files' not in public and 'version' not in public
    assert 'Only-internal' not in response.text
    assert client.get(f"{P}/jobs/{job['id']}").status_code==404
    assert change(client,h,job).status_code==403
    login(client,'customer',email='customer.two@example.test')
    assert client.get(P+'/customer/orders').json()==[]


def test_unassigned_employee_and_origin_guards(client,test_users,order,gate,db_session):
    job=assigned(client,test_users,order)
    from app.services.security import hash_password
    e=User(email='employee.other@example.test',password_hash=hash_password('Employee@12345'),role='employee',is_active=True)
    db_session.add(e);db_session.commit()
    h=login(client,'employee',email=e.email)
    assert client.get(P+'/employee/jobs').json()==[]
    assert client.get(f"{P}/jobs/{job['id']}").status_code==404
    assert change(client,h,job).status_code==404
    h=login(client,'employee')
    assert change(client,{'Origin':ORIGIN},job).status_code==403
    assert change(client,{**h,'Origin':'http://evil.test'},job).status_code==403


def test_employee_file_access_is_job_scoped(client,test_users,order,gate,db_session,app_instance):
    job=assigned(client,test_users,order)
    file=RFQFile(rfq_id=order.rfq_id,uploaded_by_user_id=test_users['customer_1'].id,file_name='drawing.pdf',storage_key='private/drawing',content_type='application/pdf',file_size_bytes=10)
    other=RFQ(rfq_number='S10-OTHER',customer_id=test_users['customer_2'].id,title='Other customer drawing',material='Metal',quantity=1)
    db_session.add_all([file,other]);db_session.flush()
    otherfile=RFQFile(rfq_id=other.id,uploaded_by_user_id=test_users['customer_2'].id,file_name='other.pdf',storage_key='private/other',content_type='application/pdf',file_size_bytes=10)
    db_session.add(otherfile);db_session.commit()
    app_instance.dependency_overrides[get_storage_service]=lambda:SimpleNamespace(get_file=lambda key:b'%PDF-test')
    h=login(client,'employee')
    url=f"{P}/jobs/{job['id']}/files/{file.id}"
    assert client.get(url).content==b'%PDF-test'
    assert client.get(url+'?preview=true').headers['content-disposition'].startswith('inline;')
    assert client.get(f"{P}/jobs/{job['id']}/files/{otherfile.id}").status_code==404
    login(client,'customer')
    assert client.get(url).status_code==404


def test_failed_history_rolls_back_progress(client,test_users,order,gate,db_session,monkeypatch):
    job=assigned(client,test_users,order);h=login(client,'employee')
    original=db_session.flush
    def fail(*a,**kw):
        if any(isinstance(row,JobStageHistory) for row in db_session.new):raise OperationalError('stage history',{},RuntimeError('failure'))
        return original(*a,**kw)
    monkeypatch.setattr(db_session,'flush',fail)
    assert change(client,h,job).status_code==503
    monkeypatch.setattr(db_session,'flush',original)
    current=client.get(f"{P}/jobs/{job['id']}").json()
    assert current['version']==0 and current['progress']==0
    assert len(current['history'])==1


def test_concurrent_assignment_one_job(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'production.sqlite'),connect_args={'check_same_thread':False,'timeout':15})
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        a=User(email='admin@fixture.test',password_hash='not-a-login',role='admin',is_active=True)
        e=User(email='worker@fixture.test',password_hash='not-a-login',role='employee',is_active=True)
        c=User(email='customer@fixture.test',password_hash='not-a-login',role='customer',is_active=True)
        db.add_all([a,e,c]);db.flush()
        o=Order(order_number='RACE-S10',customer_id=c.id,total_amount=100,status='confirmed')
        db.add(o);db.commit();aid=a.id;eid=e.id;oid=o.id
    barrier=Barrier(2)
    def attempt(_):
        with Session(engine,expire_on_commit=False) as db:
            barrier.wait()
            try:
                assign_job(db,JobAssignmentInput(order_id=oid,employee_id=eid,instructions='Fixture instructions'),SimpleNamespace(id=aid),TestSettlement())
                return 201
            except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
    assert sorted(results)==[201,409],results
    with Session(engine) as db:
        assert db.query(ProductionJob).count()==1
        assert db.query(JobStageHistory).count()==1
    barrier2=Barrier(2)
    with Session(engine) as db: jid=db.query(ProductionJob).one().id
    def simultaneous_update(value):
        with Session(engine,expire_on_commit=False) as db:
            barrier2.wait()
            try:
                update_job(db,jid,JobUpdateInput(expected_version=0,action='progress',progress=value,note='Concurrent work note'),SimpleNamespace(id=eid,role='employee'))
                return 200
            except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(simultaneous_update,[10,20]))
    assert sorted(results)==[200,409],results
    with Session(engine) as db:
        assert db.get(ProductionJob,jid).version==1
        assert db.query(JobStageHistory).count()==2
    engine.dispose()


def test_cancelled_order_blocks_employee_changes(client,test_users,order,gate,db_session):
    job=assigned(client,test_users,order)
    order.status='cancelled';db_session.commit()
    h=login(client,'employee')
    assert change(client,h,job).status_code==409
    assert db_session.get(ProductionJob,job['id']).progress==0


def test_assignment_history_failure_rolls_back_job(client,test_users,order,gate,db_session,monkeypatch):
    h=login(client);original=db_session.flush
    def fail(*a,**kw):
        if any(isinstance(row,JobStageHistory) for row in db_session.new):raise OperationalError('stage history',{},RuntimeError('failure'))
        return original(*a,**kw)
    monkeypatch.setattr(db_session,'flush',fail)
    assert assign(client,h,order,test_users).status_code==503
    monkeypatch.setattr(db_session,'flush',original)
    assert db_session.query(ProductionJob).count()==0
    assert db_session.query(JobStageHistory).count()==0
