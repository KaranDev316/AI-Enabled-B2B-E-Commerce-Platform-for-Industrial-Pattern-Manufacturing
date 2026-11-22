"""Real S07→S09→S10 flow, plus private S12 reporting contracts."""
from uuid import uuid4
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from app.models import ProductionJob, JobStageHistory, User
from app.issue_models import ProductionIssue, ProductionIssueFile, ProductionIssueEvent
from app.models_commercial import CommercialInvoice, OrderCommercialSnapshot, SimulatedPayment
from app.services.storage_service import get_storage_service
from test_acceptance_s08 import offer, sign_in
from test_payments_s09 import invoice, pay, db_session

ORIGIN='http://127.0.0.1:5173'

def employee(client):
    r=client.post('/api/auth/login',json={'email':'employee.one@example.test','password':'Employee@12345'},headers={'Origin':ORIGIN})
    assert r.status_code==200,r.text
    return {'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf_token']}

def assign(client, invoice, users):
    return client.post('/api/production/admin/jobs',headers=sign_in(client,'admin'),json={
        'order_id':invoice['order_id'],'employee_id':users['employee_1'].id,'instructions':'Manufacture to the approved drawing.'})

def fully_paid(client, invoice):
    r=pay(client,invoice['invoice_id'],sign_in(client),amount='35.58')
    assert r.status_code==200,r.text

def test_real_ledger_gates_assignment_and_progress(client,invoice,test_users,db_session):
    assert assign(client,invoice,test_users).status_code==409
    h=sign_in(client)
    assert pay(client,invoice['invoice_id'],h,amount='35.58',outcome='failed').status_code==200
    assert assign(client,invoice,test_users).status_code==409
    assert pay(client,invoice['invoice_id'],sign_in(client),amount='10.00').status_code==200
    assert assign(client,invoice,test_users).status_code==409
    assert pay(client,invoice['invoice_id'],sign_in(client),amount='25.58').status_code==200
    result=assign(client,invoice,test_users)
    assert result.status_code==201,result.text
    job=result.json()
    assert client.get(f"/api/orders/{invoice['order_id']}").json()['status']=='in_production'
    assert assign(client,invoice,test_users).status_code==409
    r=client.patch(f"/api/production/employee/jobs/{job['id']}",headers=employee(client),json={
        'expected_version':0,'action':'progress','progress':20,'note':'Internal machining instructions','customer_note':'Design work started.'})
    assert r.status_code==200,r.text
    sign_in(client)
    tracking=client.get('/api/production/customer/orders').json()[0]['production']
    assert tracking['progress']==20
    assert tracking['history'][-1]['message']=='Design work started.'
    assert 'Internal machining' not in str(tracking)
    assert 'instructions' not in tracking and 'employee_id' not in tracking

@pytest.mark.parametrize('tamper',['ledger','balance','ownership','count','total'])
def test_inconsistent_paid_summary_cannot_assign(client,invoice,test_users,db_session,tamper):
    fully_paid(client,invoice)
    inv=db_session.get(CommercialInvoice,invoice['invoice_id'])
    snap=db_session.query(OrderCommercialSnapshot).filter_by(order_id=invoice['order_id']).one()
    if tamper=='ledger': db_session.query(SimulatedPayment).delete()
    elif tamper=='balance': inv.paid_amount=Decimal('0')
    elif tamper=='ownership': inv.customer_id=test_users['customer_2'].id
    elif tamper=='count': snap.successful_payment_count=9
    else: snap.total_amount=Decimal('1')
    db_session.commit()
    assert assign(client,invoice,test_users).status_code==409
    assert db_session.query(ProductionJob).count()==0

class Store:
    def __init__(self): self.files={};self.fail=False
    def is_supabase_configured(self):return True
    def save_file(self,key,content,kind):
        self.files[key]=content
        if self.fail: raise RuntimeError('Storage down')
    def get_file(self,key):return self.files[key]
    def delete_file(self,key):self.files.pop(key,None)

@pytest.fixture
def store(app_instance):
    storage=Store();app_instance.dependency_overrides[get_storage_service]=lambda:storage;return storage

def report(client,headers,**extra):
    data={'title':'Machine spindle fault','description':'The spindle stops during machining.','issue_type':'machine','priority':'high',**extra}
    return client.post('/api/production/issues',headers=headers,data=data)

def test_report_handle_and_private_attachment(client,test_users,db_session,store):
    h=employee(client)
    r=client.post('/api/production/issues',headers=h,data={'title':'Drawing unclear','description':'Critical dimensions are missing.','issue_type':'drawing','priority':'medium'},files={'files':('drawing.pdf',b'%PDF-1.4\nprivate evidence','application/pdf')})
    assert r.status_code==201,r.text
    issue=r.json();assert issue['status']=='open'
    url=issue['files'][0]['url']
    assert client.get(url).content==b'%PDF-1.4\nprivate evidence'
    assert 'storage_key' not in str(issue)
    sign_in(client)
    assert client.get('/api/production/issues').status_code==403
    assert client.get(url).status_code==404
    admin=sign_in(client,'admin')
    assert client.get(url).status_code==200
    r=client.patch(f"/api/production/issues/{issue['id']}",headers=admin,json={'expected_version':0,'status':'in_progress','note':'Maintenance inspection scheduled.'})
    assert r.status_code==200,r.text
    assert client.patch(f"/api/production/issues/{issue['id']}",headers=admin,json={'expected_version':0,'status':'resolved','note':'Stale update'}).status_code==409
    employee(client)
    own=client.get('/api/production/issues').json()[0]
    assert own['status']=='in_progress' and len(own['history'])==2
    assert db_session.query(ProductionIssueFile).count()==1
    assert db_session.query(ProductionIssueEvent).count()==2

@pytest.mark.parametrize('files',[
 [('files',('a.pdf',b'%PDF-a','application/pdf'))]*3,
 [('files',('a.png',b'MZ executable','image/png'))],
 [('files',('a.exe',b'%PDF-a','application/pdf'))],
 [('files',('a.pdf',b'','application/pdf'))],
 [('files',('a.pdf',b'%PDF-'+b'a'*(20*1024*1024),'application/pdf'))],
])
def test_invalid_upload_creates_no_issue_or_files(client,test_users,db_session,store,files):
    h=employee(client)
    r=client.post('/api/production/issues',headers=h,data={'title':'Material problem','description':'Material does not meet required tolerance.','issue_type':'material','priority':'high'},files=files)
    assert r.status_code==422,r.text
    assert not db_session.query(ProductionIssue).count() and not store.files

def test_storage_failure_compensates_metadata_and_bytes(client,test_users,db_session,store):
    store.fail=True
    r=client.post('/api/production/issues',headers=employee(client),data={'title':'Material problem','description':'Material does not meet required tolerance.','issue_type':'material','priority':'high'},files={'files':('a.pdf',b'%PDF-valid','application/pdf')})
    assert r.status_code==503
    assert not db_session.query(ProductionIssue).count()
    assert not db_session.query(ProductionIssueFile).count() and not store.files

def test_other_employee_cannot_read_or_link_job(client,invoice,test_users,db_session,store):
    fully_paid(client,invoice);job=assign(client,invoice,test_users).json()
    issue=report(client,employee(client),job_id=str(job['id'])).json()
    from app.services.security import hash_password
    other=User(email='other.employee@example.test',role='employee',password_hash=hash_password('Employee@12345'),is_active=True)
    db_session.add(other);db_session.commit()
    r=client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':other.email,'password':'Employee@12345'})
    h={'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf_token']}
    assert client.get('/api/production/issues').json()==[]
    assert client.get(f"/api/production/issues/{issue['id']}").status_code==404
    assert report(client,h,job_id=str(job['id'])).status_code==404
    assert client.patch(f"/api/production/issues/{issue['id']}",headers=h,json={'expected_version':0,'status':'resolved','note':'Forbidden action'}).status_code==403

def test_csrf_and_roles(client,test_users,db_session):
    assert report(client,{}).status_code in (401,403)
    admin=sign_in(client,'admin');assert report(client,admin).status_code==403
    h=employee(client)
    assert report(client,{'Origin':ORIGIN}).status_code==403
    assert report(client,{**h,'Origin':'https://untrusted.invalid'}).status_code==403
    assert report(client,h,title='  ',description='  ').status_code==422
    assert report(client,h).status_code==201 # No storage configuration needed without files.

def test_preflight_detects_legacy_revision_without_changing_data(tmp_path):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine, text, inspect
    spec=importlib.util.spec_from_file_location('check_samonta_database',Path(__file__).resolve().parents[1]/'check_samonta_database.py')
    check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
    engine=create_engine(f'sqlite:///{tmp_path / "legacy.db"}')
    with engine.begin() as c:
        c.execute(text('CREATE TABLE alembic_version(version_num VARCHAR(32))'))
        c.execute(text("INSERT INTO alembic_version VALUES ('006')"))
        c.execute(text('CREATE TABLE inventory_materials(id INTEGER, quantity INTEGER)'))
        c.execute(text('INSERT INTO inventory_materials VALUES(1,42)'))
    assert check.check(engine)==2
    with engine.connect() as c:
        assert c.execute(text('SELECT quantity FROM inventory_materials')).scalar()==42
        assert c.execute(text('SELECT version_num FROM alembic_version')).scalar()=='006'
    assert set(inspect(engine).get_table_names())=={'alembic_version','inventory_materials'}
    engine.dispose()
