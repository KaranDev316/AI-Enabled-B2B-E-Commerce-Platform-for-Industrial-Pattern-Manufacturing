import httpx
import pytest
from app.config import Settings
from app.services.catalogue_storage import CatalogueStorage, CatalogueStorageError

@pytest.mark.parametrize('status,body,expected',[
    (400,{'message':'Bucket not found'},'bucket does not exist'),
    (401,{'message':'Invalid JWT'},'rejected the backend key'),
    (400,{'message':'new row violates row-level security policy'},'denied upload access'),
    (413,{},'file-size limit'),
    (400,{'message':'mime type not supported'},'rejects this image type'),
    (503,{'message':'remote internal text'},'HTTP 503'),
])
def test_safe_storage_error(monkeypatch,tmp_path,status,body,expected):
    storage=CatalogueStorage(Settings(supabase_url='https://project.example.test',supabase_service_role_key='secret-never-reflected',private_storage_dir=tmp_path))
    monkeypatch.setattr(httpx,'post',lambda *a,**k:httpx.Response(status,json=body))
    with pytest.raises(CatalogueStorageError) as error:
        storage.save_file('catalogue/1/a.png',b'image','image/png')
    assert expected in str(error.value)
    assert 'secret-never-reflected' not in str(error.value)
    assert 'remote internal text' not in str(error.value)

def test_network_failure_safe(monkeypatch,tmp_path):
    storage=CatalogueStorage(Settings(supabase_url='https://project.example.test',supabase_service_role_key='secret',private_storage_dir=tmp_path))
    def fail(*a,**k):raise httpx.ConnectError('sensitive internal detail')
    monkeypatch.setattr(httpx,'post',fail)
    with pytest.raises(CatalogueStorageError,match='Cannot reach'):
        storage.save_file('catalogue/1/a.png',b'image','image/png')
