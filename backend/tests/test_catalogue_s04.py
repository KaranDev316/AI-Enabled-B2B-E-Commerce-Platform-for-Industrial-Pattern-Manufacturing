import io
import pytest
from PIL import Image
from sqlalchemy.orm import Session
from app.models import Product, ProductImage, RFQ
from app.services.catalogue_storage import get_catalogue_storage
from app.api import catalogue_admin

ORIGIN = 'http://127.0.0.1:5173'

@pytest.fixture
def db_session(test_db_engine):
    # SAVEPOINTs let request rollbacks preserve previously committed setup/actions.
    # The inherited fixture otherwise rolls back the entire enclosing SQLite test.
    connection = test_db_engine.connect()
    transaction = connection.begin()
    if connection.dialect.name == 'sqlite':
        connection.exec_driver_sql('BEGIN')
    session = Session(bind=connection, autoflush=False, expire_on_commit=False,
                      join_transaction_mode='create_savepoint')
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def login(client, role='admin'):
    r = client.post('/api/auth/login', json={'email': f'{role}.one@example.test', 'password': role.title()+'@12345'}, headers={'Origin': ORIGIN})
    assert r.status_code == 200, r.text
    return {'Origin': ORIGIN, 'X-CSRF-Token': r.json()['csrf_token']}

def data(**kw):
    return dict(name='Wood pattern', slug='wood-s04', material_type='Wood', specifications='Length: 100 mm', **kw)

def png():
    out = io.BytesIO()
    Image.new('RGB', (8,8), 'orange').save(out, format='PNG')
    return out.getvalue()

class Store:
    configured=True
    fail=False
    def __init__(self): self.files={}
    def is_supabase_configured(self): return self.configured
    def save_file(self,k,v,m):
        self.files[k]=v
        if self.fail: raise RuntimeError('upload failure')
    def get_file(self,k):
        if k not in self.files: raise FileNotFoundError(k)
        return self.files[k]
    def delete_file(self,k): self.files.pop(k,None)

@pytest.fixture
def store(app_instance):
    s=Store()
    app_instance.dependency_overrides[get_catalogue_storage]=lambda:s
    return s

def create(client,h):
    r=client.post('/api/admin/catalogue/products',json=data(),headers=h)
    assert r.status_code==201,r.text
    return r.json()

def test_persisted_category_product_and_visibility(client,test_users,db_session):
    h=login(client)
    r=client.post('/api/admin/catalogue/categories',json={'name':'Wood'},headers=h)
    assert r.status_code==201
    cid=r.json()['id']
    r=client.post('/api/admin/catalogue/products',json=data(category_id=cid),headers=h)
    assert r.status_code==201,r.text
    pid=r.json()['id']
    assert client.get('/api/products/wood-s04').json()['specifications']=='Length: 100 mm'
    assert client.get('/api/products/wood-s04').json()['indicative_price'] is None
    assert client.put(f'/api/admin/catalogue/categories/{cid}',json={'name':'Patterns'},headers=h).status_code==200
    assert client.get('/api/products/wood-s04').json()['category_name']=='Patterns'
    rfq=RFQ(rfq_number='S04-EXISTING',customer_id=test_users['customer_1'].id,product_id=pid,title='Historical requirement',material='Wood',quantity=1)
    db_session.add(rfq)
    db_session.commit()
    assert client.put(f'/api/admin/catalogue/products/{pid}',json=data(is_active=False,indicative_price='123.45'),headers=h).status_code==200
    db_session.refresh(rfq)
    assert rfq.product_id==pid
    assert rfq.title=='Historical requirement'
    assert client.get('/api/products/wood-s04').status_code==404
    assert not client.get('/api/products').json()
    assert client.get('/api/admin/catalogue/products').json()[0]['id']==pid
    assert db_session.get(Product,pid) is not None

@pytest.mark.parametrize('role',['customer','employee'])
def test_admin_only(client,test_users,role):
    h=login(client,role)
    assert client.get('/api/admin/catalogue/products').status_code==403
    assert client.post('/api/admin/catalogue/products',json=data(),headers=h).status_code==403
    assert client.post('/api/admin/catalogue/categories',json={'name':'No'},headers=h).status_code==403
    assert client.post('/api/admin/catalogue/products/1/images',files={'files':('x.png',png(),'image/png')},headers=h).status_code==403

def test_csrf_origin_anonymous(client,test_users):
    assert client.get('/api/admin/catalogue/products').status_code==401
    h=login(client)
    for headers in [{'Origin':ORIGIN},{'X-CSRF-Token':h['X-CSRF-Token']},{**h,'Origin':'http://evil.test'}]:
        assert client.post('/api/admin/catalogue/products',json=data(),headers=headers).status_code==403

@pytest.mark.parametrize('field,value',[('name',' '),('slug','../x'),('indicative_price','-1'),('indicative_price','1.001'),('category_id',99999)])
def test_invalid_product(client,test_users,db_session,field,value):
    h=login(client); body=data();body[field]=value
    assert client.post('/api/admin/catalogue/products',json=body,headers=h).status_code==422
    assert db_session.query(Product).count()==0

def test_duplicates(client,test_users):
    h=login(client)
    assert client.post('/api/admin/catalogue/categories',json={'name':'WOOD'},headers=h).status_code==201
    assert client.post('/api/admin/catalogue/categories',json={'name':'wood'},headers=h).status_code==409
    create(client,h)
    assert client.post('/api/admin/catalogue/products',json=data(),headers=h).status_code==409


def test_image_roundtrip_and_deactivation(client,test_users,store):
    h=login(client);p=create(client,h);base=f"/api/admin/catalogue/products/{p['id']}"
    r=client.post(base+'/images',files={'files':('a.png',png(),'image/png')},headers=h)
    assert r.status_code==200,r.text
    image=r.json()['images'][0]
    assert 'storage_key' not in image
    assert client.get(image['url']).content==png()
    assert client.get('/api/products/wood-s04').json()['images']==[image]
    client.put(base,json=data(is_active=False),headers=h)
    assert client.get(image['url']).status_code==404
    assert client.get(base+f"/images/{image['id']}").content==png()
    assert client.delete(base+f"/images/{image['id']}",headers=h).status_code==204
    assert not store.files

@pytest.mark.parametrize('name,mime,body',[('bad.svg','image/svg+xml',b'<svg/>'),('bad.png','image/png',b'fake'),('bad.jpg','image/jpeg',png()),('bad.png','image/jpeg',png()),('empty.png','image/png',b'')])
def test_bad_upload(client,test_users,store,db_session,name,mime,body):
    h=login(client);p=create(client,h)
    r=client.post(f"/api/admin/catalogue/products/{p['id']}/images",files={'files':(name,body,mime)},headers=h)
    assert r.status_code==422,r.text
    assert not store.files
    assert db_session.query(ProductImage).count()==0

def test_limits_and_cleanup(client,test_users,store,db_session,monkeypatch):
    h=login(client);p=create(client,h);url=f"/api/admin/catalogue/products/{p['id']}/images"
    files=[('files',('a.png',png(),'image/png'))]*3
    assert client.post(url,files=files,headers=h).status_code==422
    monkeypatch.setattr(catalogue_admin,'MAX_IMAGE_BYTES',10)
    assert client.post(url,files=files[:1],headers=h).status_code==422
    monkeypatch.setattr(catalogue_admin,'MAX_IMAGE_BYTES',20*1024*1024)
    store.fail=True
    assert client.post(url,files=files[:2],headers=h).status_code==503
    assert not store.files
    assert db_session.query(ProductImage).count()==0

def test_db_failure_cleanup(client,test_users,store,db_session,monkeypatch):
    h=login(client);p=create(client,h)
    original_commit = db_session.commit
    def fail():
        if any(isinstance(row, ProductImage) for row in db_session.new):
            raise RuntimeError('database failure')
        return original_commit()
    monkeypatch.setattr(db_session,'commit',fail)
    r=client.post(f"/api/admin/catalogue/products/{p['id']}/images",files={'files':('a.png',png(),'image/png')},headers=h)
    assert r.status_code==503
    assert not store.files
    assert db_session.query(ProductImage).count()==0

def test_unconfigured_storage(client,test_users,store):
    h=login(client);p=create(client,h);store.configured=False
    r=client.post(f"/api/admin/catalogue/products/{p['id']}/images",files={'files':('a.png',png(),'image/png')},headers=h)
    assert r.status_code==503
    assert 'Supabase' in r.json()['detail']


def test_two_images_and_second_write_failure(client,test_users,store,db_session):
    h=login(client);p=create(client,h);url=f"/api/admin/catalogue/products/{p['id']}/images"
    files=[('files',('a.png',png(),'image/png')),('files',('b.png',png(),'image/png'))]
    r=client.post(url,files=files,headers=h)
    assert r.status_code==200
    assert len(r.json()['images'])==2
    original=store.save_file
    count=0
    def second_fails(key,content,mime):
        nonlocal count
        count+=1
        original(key,content,mime)
        if count==2: raise RuntimeError('second upload failed')
    store.save_file=second_fails
    r=client.post(url,files=files,headers=h)
    assert r.status_code==503
    assert len(store.files)==2
    assert db_session.query(ProductImage).count()==2


def test_jpeg_upload_and_missing_object_fallback(client,test_users,store):
    h=login(client);p=create(client,h)
    out=io.BytesIO();Image.new('RGB',(8,8),'blue').save(out,format='JPEG')
    r=client.post(f"/api/admin/catalogue/products/{p['id']}/images",files={'files':('photo.jpeg',out.getvalue(),'image/jpeg')},headers=h)
    assert r.status_code==200
    url=r.json()['images'][0]['url']
    assert client.get(url).headers['content-type']=='image/jpeg'
    store.files.clear()
    assert client.get(url).status_code==404


def test_storage_delete_failure_is_not_silently_ignored(monkeypatch,tmp_path):
    import httpx
    from app.config import Settings
    from app.services.catalogue_storage import CatalogueStorage
    storage=CatalogueStorage(Settings(supabase_url='https://storage.example.test',supabase_service_role_key='test-only',private_storage_dir=tmp_path))
    monkeypatch.setattr(httpx,'delete',lambda *a,**kw: httpx.Response(503))
    with pytest.raises(RuntimeError): storage.delete_file('catalogue/1/test.png')
