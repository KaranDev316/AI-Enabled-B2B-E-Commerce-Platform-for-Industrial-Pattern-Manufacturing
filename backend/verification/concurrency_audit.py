import os, json, threading, secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
from sqlalchemy import create_engine,text
from sqlalchemy.orm import Session
from app.models import User
from app.services.security import hash_password
from app.services.rfq_service import attach_rfq_file
from app.services.storage_service import get_storage_service
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert u.host in ('127.0.0.1', 'localhost') and u.database.endswith('_test')
engine=create_engine(os.environ['DATABASE_URL'])
fixture=json.loads(Path('/private/tmp/kpc-test-verification/browser-fixture.json').read_text())
c=httpx.Client(base_url='http://127.0.0.1:8019',headers={'Origin':'http://127.0.0.1:8019'},timeout=30)
r=c.post('/api/auth/login',json=fixture); uid=r.json()['user']['id']; c.headers['X-CSRF-Token']=r.json()['csrf_token']
r=c.post('/api/rfqs',json={'title':'Overlapping transactions','material':'Aluminium','quantity':1}); rid=r.json()['id']
# Synchronize after each transaction checks capacity, then perform actual local storage writes.
storage=get_storage_service(); original=storage.save_file; barrier=threading.Barrier(3)
def synchronized_save(*args,**kwargs):
    barrier.wait(timeout=10)
    return original(*args,**kwargs)
storage.save_file=synchronized_save
def upload(i):
    with Session(engine) as db:
        return attach_rfq_file(db,rid,db.get(User,uid),f'part{i}.step',b'ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;').id
with ThreadPoolExecutor(max_workers=3) as pool: ids=list(pool.map(upload,range(3)))
storage.save_file=original
with engine.connect() as conn:
    count=conn.execute(text('select count(*) from rfq_files where rfq_id=:id'),{'id':rid}).scalar_one()
print(json.dumps({'check':'overlapping upload transactions enforce limit','saved':count,'passed':count<=2}))
results=json.loads(Path('/private/tmp/kpc-test-verification/independent-results.json').read_text())
results.append({'name':'overlapping upload transactions enforce two-file limit','passed':count<=2,'detail':f'{count} files persisted from three real PostgreSQL transactions; barrier before real storage writes'})
# Concurrent ticket creation through real HTTP (no synchronization inside application).
def submit_ticket(i):
    with httpx.Client(base_url=str(c.base_url),headers=dict(c.headers),cookies=c.cookies,timeout=30) as other:
        return other.post('/api/support/tickets',json={'subject':f'Parallel inquiry {i}','message':'Concurrent independent request'}).status_code
with ThreadPoolExecutor(max_workers=6) as pool: statuses=list(pool.map(submit_ticket,range(6)))
print(json.dumps({'check':'concurrent ticket creation','statuses':statuses}))
results.append({'name':'concurrent independent ticket submissions succeed','passed':all(s==201 for s in statuses),'detail':statuses})
Path('/private/tmp/kpc-test-verification/independent-results.json').write_text(json.dumps(results,indent=2))

raise SystemExit(1 if any(not r["passed"] for r in results) else 0)
