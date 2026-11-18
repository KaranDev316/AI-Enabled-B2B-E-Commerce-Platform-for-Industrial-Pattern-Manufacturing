"""Independent checks: real HTTP server + migrated disposable PostgreSQL; no existing test fixtures."""
import os, json, uuid, secrets, base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.models import User
from app.services.security import hash_password

url=os.environ['DATABASE_URL']
u=make_url(url)
assert u.host in ('127.0.0.1','localhost') and u.database.endswith('_test')
engine=create_engine(url)
base='http://127.0.0.1:8019'
run=uuid.uuid4().hex[:8]
password=secrets.token_urlsafe(24)
results=[]
Path('/private/tmp/kpc-test-verification').mkdir(parents=True, exist_ok=True)
def check(name, ok, detail):
    results.append(dict(name=name,passed=bool(ok),detail=detail))
    print(('PASS ' if ok else 'FAIL ')+name+': '+str(detail),flush=True)
def client(): return httpx.Client(base_url=base,headers={'Origin':base},timeout=30,limits=httpx.Limits(max_keepalive_connections=0))
def register(c,label,**overrides):
    data=dict(email=f'{label}.{run}@example.test',password=password,company_name='Audit Foundry',contact_person='Audit Customer',phone='1234567890')
    data.update(overrides)
    return c.post('/api/auth/register',json=data)
def login(c,email,pw=password):
    r=c.post('/api/auth/login',json={'email':email,'password':pw})
    if r.status_code==200: c.headers['X-CSRF-Token']=r.json()['csrf_token']
    return r
def rfq(c,title='Independent test pattern'):
    return c.post('/api/rfqs',json=dict(title=title,rfq_type='custom',material='Aluminium',quantity=2,description='A real audit request'))
def ticket(c,**kw):
    return c.post('/api/support/tickets',json=dict(subject='Audit inquiry',message='Please confirm the specification',**kw))
def db_count(sql,**kw):
    with engine.connect() as conn: return conn.execute(text(sql),kw).scalar_one()

anon=client(); a=client(); b=client(); admin=client()
r=register(a,'a'); aid=r.json()['id']; email=r.json()['email']
check('registration persists user and owned profile',r.status_code==201 and db_count('select count(*) from customer_profiles where user_id=:id',id=aid)==1,f'HTTP {r.status_code}')
r=register(b,'b'); bid=r.json()['id']; bemail=r.json()['email']
for c,e in [(a,email),(b,bemail)]:
    r=login(c,e)
    check('login '+e.split('.')[0],r.status_code==200,f'HTTP {r.status_code}')
check('cookie attributes',all(x in r.headers.get('set-cookie','').lower() for x in ['httponly','samesite=lax']), 'HttpOnly and SameSite=Lax on local HTTP')
with Session(engine) as db:
    user=User(email=f'admin.{run}@example.test',password_hash=hash_password(password),role='admin',is_active=True,must_change_password=False)
    db.add(user); db.commit()
login(admin,f'admin.{run}@example.test')
r=register(anon,'a',email=email.upper())
check('duplicate registration rejected',r.status_code==409 and db_count('select count(*) from users where lower(email)=:email',email=email)==1,f'HTTP {r.status_code}')
r=register(anon,'bad',company_name='   ',contact_person='  ',phone='       ')
check('blank required business details rejected',r.status_code==422,f'HTTP {r.status_code}; whitespace-only values')
r=register(anon,'privileged',role='admin')
check('public role escalation rejected',r.status_code==422,f'HTTP {r.status_code}')
r=a.get('/api/admin/users'); check('customer denied admin data',r.status_code==403,f'HTTP {r.status_code}')
r=anon.get('/api/rfqs/my'); check('anonymous denied RFQs',r.status_code==401,f'HTTP {r.status_code}')
count=db_count('select count(*) from rfqs')
r=a.post('/api/rfqs',headers={'X-CSRF-Token':b.headers['X-CSRF-Token']},json=dict(title='Cross session',material='Wood',quantity=1))
check('cross-session CSRF cannot mutate',r.status_code==403 and count==db_count('select count(*) from rfqs'),f'HTTP {r.status_code}')
r=a.patch('/api/profile/me',headers={'Origin':'https://untrusted.example.test'},json={'company_name':'Changed'})
check('untrusted origin cannot mutate',r.status_code==403,f'HTTP {r.status_code}')
r=rfq(a); rid=r.json()['id']; check('custom RFQ stored on PostgreSQL',r.status_code==201,f'HTTP {r.status_code}')
r=b.get(f'/api/rfqs/{rid}'); check('cross-customer RFQ read denied',r.status_code==403,f'HTTP {r.status_code}')
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j5XkAAAAASUVORK5CYII=')
r=a.post(f'/api/rfqs/{rid}/files',files={'file':('drawing.png',png,'image/png')}); fid=r.json()['id']
r2=a.get(f'/api/rfqs/{rid}/files/{fid}')
check('PNG upload and download preserve bytes',r.status_code==201 and r2.content==png,f'upload {r.status_code}, download {r2.status_code}')
r=b.get(f'/api/rfqs/{rid}/files/{fid}'); check('cross-customer file denied',r.status_code==403,f'HTTP {r.status_code}')
r=rfq(a); malformed_id=r.json()['id']
r=a.post(f'/api/rfqs/{malformed_id}/files',files={'file':('not-cad.iges',b'This is ordinary text, not an IGES document.','model/iges')})
check('non-CAD text masquerading as IGES rejected',r.status_code==400,f'HTTP {r.status_code}')
r=a.post(f'/api/rfqs/{malformed_id}/files',files={'file':('not-cad.stl',b'x'*100,'model/stl')})
check('arbitrary bytes masquerading as STL rejected',r.status_code==400,f'HTTP {r.status_code}')
r=rfq(a); unicode_id=r.json()['id']
r=a.post(f'/api/rfqs/{unicode_id}/files',files={'file':('चित्र.png',png,'image/png')})
r2=a.get(f"/api/rfqs/{unicode_id}/files/{r.json()['id']}")
check('Unicode filename remains downloadable',r.status_code==201 and r2.status_code==200 and r2.content==png,f'upload {r.status_code}, download {r2.status_code}')
r=ticket(a); tid=r.json()['id']; check('support ticket stored',r.status_code==201,f'HTTP {r.status_code}')
r=b.post(f'/api/support/tickets/{tid}/messages',json={'message':'Intruding message'})
check('cross-customer support reply denied',r.status_code==403,f'HTTP {r.status_code}')
r=a.post('/api/support/tickets',json={'subject':'   ','message':'   '})
check('blank support content rejected',r.status_code==422,f'HTTP {r.status_code}')
r=a.patch('/api/profile/me',json={'company_name':'x'*256})
check('overlength profile rejected with validation',r.status_code==422,f'HTTP {r.status_code}')
r=admin.post(f'/api/admin/users/{aid}/reset-password',json={'new_password':password+'reset'})
check('admin reset succeeds',r.status_code==200,f'HTTP {r.status_code}')
r=a.get('/api/auth/me'); check('reset revokes old session',r.status_code==401,f'HTTP {r.status_code}')
r=login(a,email,password+'reset'); check('reset login requires password change',r.status_code==200 and r.json()['user']['must_change_password'],f'HTTP {r.status_code}')
r=rfq(a,'Must not submit before required password change')
check('mandatory password change blocks business mutation',r.status_code==403,f'HTTP {r.status_code}')
# Independent simultaneous HTTP requests, real connections and real transactions.
r=rfq(b,'Concurrent uploads'); concurrent_id=r.json()['id']
def upload(i):
    with client() as c:
        c.cookies.update(b.cookies); c.headers['X-CSRF-Token']=b.headers['X-CSRF-Token']
        return c.post(f'/api/rfqs/{concurrent_id}/files',files={'file':(f'parallel-{i}.png',png,'image/png')}).status_code
with ThreadPoolExecutor(max_workers=6) as pool: codes=list(pool.map(upload,range(6)))
n=db_count('select count(*) from rfq_files where rfq_id=:id',id=concurrent_id)
check('concurrent uploads respect two-file invariant',n<=2,dict(statuses=codes,persisted_files=n))
# Preserve synthetic browser fixture credentials locally; never include them in evidence report.
Path('/private/tmp/kpc-test-verification/browser-fixture.json').write_text(json.dumps({'email':bemail,'password':password}))
Path('/private/tmp/kpc-test-verification/independent-results.json').write_text(json.dumps(results,indent=2))
print(f'{sum(x["passed"] for x in results)} passed; {sum(not x["passed"] for x in results)} failed')

raise SystemExit(1 if any(not r["passed"] for r in results) else 0)
