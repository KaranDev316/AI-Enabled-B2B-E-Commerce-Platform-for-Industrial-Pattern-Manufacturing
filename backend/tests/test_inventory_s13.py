from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.database import Base
from app.models import InventoryMaterial, StockAdjustment, User
from app.schemas.inventory import AdjustmentInput
from app.services.inventory_service import adjust_stock

ORIGIN='http://127.0.0.1:5173'
PREFIX='/api/admin/inventory'

@pytest.fixture
def db_session(test_db_engine):
    connection=test_db_engine.connect(); transaction=connection.begin()
    if connection.dialect.name=='sqlite': connection.exec_driver_sql('BEGIN')
    session=Session(bind=connection,autoflush=False,expire_on_commit=False,join_transaction_mode='create_savepoint')
    try: yield session
    finally: session.close();transaction.rollback();connection.close()

def login(client,role='admin'):
    r=client.post('/api/auth/login',json={'email':f'{role}.one@example.test','password':role.title()+'@12345'},headers={'Origin':ORIGIN})
    assert r.status_code==200,r.text
    return {'Origin':ORIGIN,'X-CSRF-Token':r.json()['csrf_token']}

def material(**kwargs):
    return {'code':'RM-001','name':'Cast Iron','category':'Raw Material','unit':'kg','minimum_stock':'5',**kwargs}

def create(client,h,**kw):
    r=client.post(PREFIX+'/materials',json=material(**kw),headers=h)
    assert r.status_code==201,r.text
    return r.json()

def adjust(client,h,id,amount='10',direction='addition',reason='Opening stock',request_id=None):
    return client.post(f'{PREFIX}/materials/{id}/adjustments',json={'amount':amount,'direction':direction,'reason':reason,'request_id':request_id or str(uuid4())},headers=h)

def detail(client,id):return client.get(f'{PREFIX}/materials/{id}').json()
def history(client,id):return client.get(f'{PREFIX}/materials/{id}/adjustments').json()

def test_material_and_reasoned_opening_stock(client,test_users):
    h=login(client);m=create(client,h)
    assert Decimal(m['quantity'])==0
    assert m['stock_status']=='out_of_stock'
    assert history(client,m['id'])==[]
    r=adjust(client,h,m['id'])
    assert r.status_code==200,r.text
    entry=r.json()
    assert Decimal(entry['quantity_before'])==0
    assert Decimal(entry['quantity_after'])==10
    assert entry['actor_email']=='admin.one@example.test'
    assert entry['created_at']
    assert detail(client,m['id'])['stock_status']=='in_stock'
    assert history(client,m['id'])[0]['reason']=='Opening stock'
    assert client.get(PREFIX+'/summary').json()=={'total':1,'in_stock':1,'low_stock':0,'out_of_stock':0}

@pytest.mark.parametrize('role',['customer','employee'])
def test_inventory_is_admin_only(client,test_users,role):
    h=login(client,role)
    assert client.get(PREFIX+'/materials').status_code==403
    assert client.get(PREFIX+'/summary').status_code==403
    assert client.get(PREFIX+'/materials/1/adjustments').status_code==403
    assert client.post(PREFIX+'/materials',json=material(),headers=h).status_code==403
    assert adjust(client,h,1).status_code==403

def test_anonymous_and_csrf_origin_checks(client,test_users):
    assert client.get(PREFIX+'/materials').status_code==401
    h=login(client)
    for headers in ({'Origin':ORIGIN},{'X-CSRF-Token':h['X-CSRF-Token']},{**h,'Origin':'http://untrusted.test'}):
        assert client.post(PREFIX+'/materials',json=material(),headers=headers).status_code==403

@pytest.mark.parametrize('change',[{'name':'  '},{'code':'../no'},{'minimum_stock':'-1'},{'minimum_stock':'1.0001'},{'unit':'box'},{'quantity':50},{'unit':'piece','minimum_stock':'1.5'}])
def test_invalid_material_does_not_save(client,test_users,change):
    h=login(client)
    assert client.post(PREFIX+'/materials',json=material(**change),headers=h).status_code==422
    assert client.get(PREFIX+'/materials').json()==[]

def test_duplicate_code_and_edits_preserve_balance_unit_history(client,test_users):
    h=login(client);m=create(client,h)
    assert client.post(PREFIX+'/materials',json=material(code='rm-001'),headers=h).status_code==409
    adjust(client,h,m['id'])
    old=history(client,m['id'])
    r=client.put(f"{PREFIX}/materials/{m['id']}",json=material(name='Renamed Iron',code='RM-002',minimum_stock='12'),headers=h)
    assert r.status_code==200
    assert Decimal(r.json()['quantity'])==10
    assert r.json()['stock_status']=='low_stock'
    assert history(client,m['id'])==old
    assert old[0]['material_code']=='RM-001'
    assert client.put(f"{PREFIX}/materials/{m['id']}",json=material(unit='g'),headers=h).status_code==422
    assert detail(client,m['id'])['unit']=='kg'

@pytest.mark.parametrize('amount,reason',[('0','zero'),('-1','negative'),('1.0001','precision'),('1','  '),('NaN','invalid'),('Infinity','invalid')])
def test_invalid_adjustments(client,test_users,amount,reason):
    h=login(client);m=create(client,h)
    assert adjust(client,h,m['id'],amount=amount,reason=reason).status_code==422
    assert Decimal(detail(client,m['id'])['quantity'])==0
    assert history(client,m['id'])==[]

def test_deduction_status_boundaries_and_nonnegative_balance(client,test_users):
    h=login(client);m=create(client,h)
    adjust(client,h,m['id'])
    adjust(client,h,m['id'],amount='5',direction='deduction',reason='Production use')
    assert detail(client,m['id'])['stock_status']=='in_stock'  # equality is adequate
    adjust(client,h,m['id'],amount='1',direction='deduction',reason='Production use')
    assert detail(client,m['id'])['stock_status']=='low_stock'
    before=history(client,m['id'])
    assert adjust(client,h,m['id'],amount='5',direction='deduction').status_code==409
    assert history(client,m['id'])==before
    assert Decimal(detail(client,m['id'])['quantity'])==4
    adjust(client,h,m['id'],amount='4',direction='deduction',reason='Remaining usage')
    assert detail(client,m['id'])['stock_status']=='out_of_stock'


def test_fractional_roundtrip(client,test_users):
    h=login(client);m=create(client,h)
    for direction,amount in [('addition','0.3'),('deduction','0.1'),('deduction','0.2')]:
        assert adjust(client,h,m['id'],amount=amount,direction=direction).status_code==200
    assert Decimal(detail(client,m['id'])['quantity'])==0
    entries=history(client,m['id'])
    for e in entries:
        delta=Decimal(e['amount'])*(1 if e['direction']=='addition' else -1)
        assert Decimal(e['quantity_before'])+delta==Decimal(e['quantity_after'])


def test_retry_idempotency_and_conflicting_reuse(client,test_users):
    h=login(client);m=create(client,h);key=str(uuid4())
    a=adjust(client,h,m['id'],request_id=key)
    b=adjust(client,h,m['id'],request_id=key)
    assert a.status_code==b.status_code==200
    assert a.json()==b.json()
    assert len(history(client,m['id']))==1
    assert Decimal(detail(client,m['id'])['quantity'])==10
    assert adjust(client,h,m['id'],amount='11',request_id=key).status_code==409


def test_piece_whole_units_and_maximum(client,test_users):
    h=login(client);m=create(client,h,unit='piece')
    assert adjust(client,h,m['id'],amount='1.5').status_code==422
    assert adjust(client,h,m['id'],amount='99999999999').status_code==200
    assert adjust(client,h,m['id'],amount='1').status_code==409
    assert len(history(client,m['id']))==1


def test_adjustment_history_is_read_only_and_not_deletable(client,test_users):
    h=login(client);m=create(client,h)
    entry=adjust(client,h,m['id']).json()
    assert client.delete(f"{PREFIX}/materials/{m['id']}",headers=h).status_code in (404,405)
    assert client.put(f"{PREFIX}/materials/{m['id']}/adjustments/{entry['id']}",json={},headers=h).status_code in (404,405)
    assert len(history(client,m['id']))==1


def test_database_failure_rolls_back_quantity_and_history(client,test_users,db_session,monkeypatch):
    h=login(client);m=create(client,h);adjust(client,h,m['id'])
    original_flush=db_session.flush
    def fail_flush(*args,**kwargs):
        if any(isinstance(row,StockAdjustment) for row in db_session.new):
            raise OperationalError('INSERT stock history',{},RuntimeError('simulated db outage'))
        return original_flush(*args,**kwargs)
    monkeypatch.setattr(db_session,'flush',fail_flush)
    assert adjust(client,h,m['id'],amount='2',reason='Failing addition').status_code==503
    monkeypatch.setattr(db_session,'flush',original_flush)
    assert Decimal(detail(client,m['id'])['quantity'])==10
    assert len(history(client,m['id']))==1


def test_concurrent_deductions_cannot_overspend(tmp_path):
    engine=create_engine('sqlite:///'+str(tmp_path/'stock.sqlite'),connect_args={'check_same_thread':False,'timeout':15})
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        actor=User(email='race@example.test',password_hash='not-a-login',role='admin',is_active=True)
        m=InventoryMaterial(code='RACE-1',name='Concurrency fixture',category='Raw Material',unit='kg',quantity=Decimal('10'),minimum_stock=Decimal('0'))
        db.add_all([actor,m]);db.commit();aid=actor.id;mid=m.id
    barrier=Barrier(2)
    def deduct(_):
        with Session(engine,expire_on_commit=False) as db:
            barrier.wait()
            try:
                adjust_stock(db,mid,AdjustmentInput(request_id=uuid4(),amount='7',direction='deduction',reason='Concurrent use'),SimpleNamespace(id=aid,email='race@example.test'))
                return 200
            except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(deduct,range(2)))
    assert sorted(results)==[200,409],results
    with Session(engine) as db:
        assert db.get(InventoryMaterial,mid).quantity==Decimal('3')
        assert db.query(StockAdjustment).count()==1
    engine.dispose()
