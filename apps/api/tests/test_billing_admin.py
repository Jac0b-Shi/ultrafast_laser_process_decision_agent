import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import get_settings
from app.services import agent_store as store,agent_billing as bill,agent_model_config as models

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setenv('LASER_EXPERIMENTS_DIR',str(tmp_path));monkeypatch.setenv('LASER_CONFIG_DIR',str(tmp_path));monkeypatch.setenv('LASER_ADMIN_USERNAME','initial');monkeypatch.setenv('LASER_ADMIN_PASSWORD','initial-password-123');get_settings.cache_clear()
    a=TestClient(create_app());a.post('/api/agent/login',json={'username':'initial','password':'initial-password-123'})
    a.post('/api/agent/users',json={'username':'person','password':'person-password-123','email':'person@example.com'})
    b=TestClient(create_app());b.post('/api/agent/login',json={'username':'person','password':'person-password-123'})
    owner=b.get('/api/agent/me').json()['id']
    yield a,b,owner,tmp_path
    get_settings.cache_clear()

def config():
    return {'name':'Fixture','protocol':'chat_completions','base_url':'https://model.invalid/v1','model':'fixture','enabled':True,'visible':True,'default':True,'max_input':20000,'max_output':100,'timeout':20,'cost':{'cached':'1','uncached':'2','output':'3'},'sale':{'cached':'2','uncached':'4','output':'6'},'api_key':'private-secret-fixture'}

def test_admin_switch_and_recovery(setup):
    a,b,owner,_=setup
    result=a.post('/api/agent/users',json={'username':'manager','password':'manager-password-123','email':'manager@example.com','admin':True})
    manager=result.json()['id']
    assert a.get('/api/agent/me').status_code==401
    assert a.post('/api/agent/login',json={'username':'initial','password':'initial-password-123'}).status_code==401
    assert b.patch('/api/agent/users/'+manager,json={'enabled':False}).status_code==403
    c=TestClient(create_app());c.post('/api/agent/login',json={'username':'manager','password':'manager-password-123'})
    assert c.patch('/api/agent/users/'+manager,json={'enabled':False}).status_code==200
    assert c.get('/api/agent/me').status_code==401
    assert a.post('/api/agent/login',json={'username':'initial','password':'initial-password-123'}).status_code==200
    assert a.patch('/api/agent/users/'+manager,json={'enabled':True}).status_code==200
    assert a.get('/api/agent/me').status_code==401

def test_user_credentials_profile_and_isolation(setup):
    a,b,owner,_=setup
    assert a.post('/api/agent/users',json={'username':'noemail','password':'long-password-123'}).status_code==422
    assert b.get('/api/agent/users').status_code==403
    assert b.patch('/api/agent/profile',json={'email':'NEW@Example.com'}).status_code==200
    p=b.get('/api/agent/me').json();assert p['email']=='new@example.com' and '/avatar/' in p['avatar_url']
    assert a.patch('/api/agent/users/'+owner,json={'password':'new-password-123'}).status_code==200
    assert b.get('/api/agent/me').status_code==401

def test_model_secrets_prices_and_usage(setup):
    a,b,owner,_=setup
    m=a.post('/api/agent/admin/models',json=config()).json()['id']
    assert 'private-secret' not in a.get('/api/agent/admin/models').text
    assert 'cost' not in b.get('/api/agent/models').json()[0]
    assert b.get('/api/agent/admin/models').status_code==403
    edited={**config(),'sale':{'cached':'3','uncached':'5','output':'7'},'api_key':''}
    a.put('/api/agent/admin/models/'+m,json=edited)
    with store.database() as conn:
        rows=conn.execute('SELECT * FROM model_versions WHERE id=? ORDER BY version',(m,)).fetchall()
        assert len(rows)==2 and json.loads(rows[0]['config'])['sale']['cached']=='2'
        assert 'private-secret' not in conn.execute('SELECT secret FROM models WHERE id=?',(m,)).fetchone()[0]
    u=bill.normalize_usage({'usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':30}}},'chat_completions')
    assert u=={'cached':30,'uncached':70,'output':20}
    assert bill.price(config(),u,'cost')==Decimal('0.00023')
    assert bill.normalize_usage({'usage':{'prompt_tokens':100,'prompt_cache_hit_tokens':30,'prompt_cache_miss_tokens':90,'completion_tokens':2}},'chat_completions') is None

def test_reserve_settle_failure_idempotence_and_debt(setup):
    a,b,owner,_=setup
    a.patch('/api/agent/users/'+owner,json={'credit_limit':'1'})
    m=config()|{'id':'test','version':1}
    call=bill.begin(owner,'selection','first','same',m,100)
    assert bill.wallet(owner)['payment_blocked']
    with pytest.raises(HTTPException):bill.begin(owner,'selection','other','different',m,100)
    bill.received(call['id'],{'cached':30,'uncached':70,'output':20})
    bill.finish(call['id'],True,{'ok':True})
    assert bill.wallet(owner)['balance']==pytest.approx(-.046)
    assert bill.wallet(owner)['reserved']==0
    assert bill.begin(owner,'selection','first','same',m,100)['replay']
    bill.finish(call['id'],True)
    assert bill.wallet(owner)['balance']==pytest.approx(-.046)
    assert a.patch('/api/agent/users/'+owner,json={'credit_limit':0}).status_code==409
    bill.recharge(owner,1,'admin','topup','test')
    bill.recharge(owner,1,'admin','topup','test')
    assert bill.wallet(owner)['balance']==pytest.approx(.954)
    call=bill.begin(owner,'selection','failure','failure',m,100)
    bill.received(call['id'],{'cached':0,'uncached':100,'output':10});bill.finish(call['id'],False)
    assert bill.wallet(owner)['balance']==pytest.approx(.954)
    stats=a.get('/api/agent/admin/costs').json()['summary'];assert Decimal(stats['failed_cost_rmb'])>0

def test_concurrent_credit_reservations(setup):
    a,b,owner,_=setup
    a.patch('/api/agent/users/'+owner,json={'credit_limit':1})
    m=config()|{'id':'test','version':1}
    def attempt(i):
        try:return bill.begin(owner,'selection',str(i),str(i),m,100)
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(4)))
    assert sum(isinstance(r,dict) for r in results)==1
    assert all(r==402 for r in results if isinstance(r,int))

def test_codes_multiuser_and_parallel_limits(setup):
    a,b,owner,_=setup
    created=a.post('/api/agent/admin/codes',json={'code':'MULTI-FIXTURE','credit':25,'total_limit':2,'per_user_limit':1,'count':1}).json()
    assert created[0]['code']=='MULTI-FIXTURE'
    def redeem(i):
        try:bill.redeem(owner,'MULTI-FIXTURE',str(i));return 200
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(redeem,range(2)))
    assert sorted(results)==[200,409]
    assert bill.wallet(owner)['balance']==25
    initial=a.get('/api/agent/me').json()['id'];bill.redeem(initial,'MULTI-FIXTURE','initial')
    assert bill.wallet(initial)['balance']==25
    assert 'MULTI-FIXTURE' not in a.get('/api/agent/admin/codes').text
    assert b.get('/api/agent/admin/costs').status_code==403

def test_unknown_usage_and_abandoned_hold(setup,monkeypatch):
    a,b,owner,_=setup
    bill.recharge(owner,1,'admin','fund','fixture')
    m=config()|{'id':'test','version':1}
    call=bill.begin(owner,'selection','unknown','unknown',m,100);bill.received(call['id'],None);bill.finish(call['id'],True,{'ok':True})
    assert bill.wallet(owner)['balance']==1
    call=bill.begin(owner,'selection','abandoned','abandoned',m,100)
    instant=store.now();monkeypatch.setattr(store,'now',lambda:instant+timedelta(minutes=16));bill.recover()
    assert bill.wallet(owner)['reserved']==0 and bill.wallet(owner)['balance']==1


@pytest.mark.parametrize('mode',['success','unknown','invalid_json','truncated','over_budget','broken_key'])
def test_metered_operation_stream(setup,monkeypatch,mode):
    from contextlib import contextmanager
    from app.services import agent_gateway
    a,b,owner,_=setup
    model=a.post('/api/agent/admin/models',json=config()).json()['id']
    bill.recharge(owner,100,'fixture','fund','test')
    called=[]
    @contextmanager
    def stream(*args,**kwargs):
        called.append(kwargs)
        class Reply:
            def raise_for_status(self):pass
            def iter_lines(self):
                content='bad-json' if mode=='invalid_json' else json.dumps({'draft':{'material':'BF33'},'explanation':'Review target fields.'})
                yield 'data: '+json.dumps({'choices':[{'delta':{'content':content},'finish_reason':'length' if mode=='truncated' else 'stop'}],**({'usage':{'prompt_tokens':100,'completion_tokens':101 if mode=='over_budget' else 20,'prompt_tokens_details':{'cached_tokens':30}}} if mode!='unknown' else {})})
                yield 'data: [DONE]'
        yield Reply()
    monkeypatch.setattr(agent_gateway.httpx,'stream',stream)
    if mode=='broken_key':
        with store.database() as conn:conn.execute('UPDATE models SET secret=? WHERE id=?',('invalid-ciphertext',model))
    body={'message':'BF33 depth target ten micrometres','model_id':model,'request_key':'operation'}
    response=b.post('/api/agent/interpret',json=body)
    success=mode in ('success','unknown')
    assert response.status_code==(200 if success else 502)
    assert bill.wallet(owner)['reserved']==0
    assert bill.wallet(owner)['balance']==pytest.approx(99.954 if mode=='success' else 100)
    if success:
        assert b.post('/api/agent/interpret',json=body).json()==response.json()
        assert len(called)==1
    with store.database() as conn:
        row=conn.execute('SELECT * FROM calls WHERE owner=?',(owner,)).fetchone()
        assert row['cost_rmb'] is None if mode in ('unknown','broken_key') else Decimal(row['cost_rmb'])>0
    if mode=='success':
        response=a.post('/api/agent/admin/models/'+model+'/test',json={'request_key':'platform-test'})
        assert response.status_code==200
        assert a.get('/api/agent/wallet').json()['balance']==0


def test_zero_credit_and_cached_price_upper_bound(setup):
    a,b,owner,_=setup
    m=config()|{'id':'test','version':1}
    with pytest.raises(HTTPException) as err:bill.begin(owner,'selection','zero','zero',m,100)
    assert err.value.status_code==402
    bill.recharge(owner,1,'admin','fund','test')
    m['sale']={'cached':'40','uncached':'1','output':'1'}
    call=bill.begin(owner,'selection','cached','cached',m,100)
    assert bill.wallet(owner)['reserved']==pytest.approx(.41)
    bill.received(call['id'],{'cached':100,'uncached':0,'output':100});bill.finish(call['id'],True)
    assert bill.wallet(owner)['balance']==pytest.approx(.59)


def test_code_expiry_disable_replay_and_total_limit(setup,monkeypatch):
    a,b,owner,_=setup
    item=a.post('/api/agent/admin/codes',json={'code':'BOUNDARY-CODE','credit':1,'total_limit':1,'per_user_limit':1,'expires':(store.now()+timedelta(days=1)).isoformat()}).json()[0]
    a.patch('/api/agent/admin/codes/'+item['id'],json={'enabled':False})
    assert b.post('/api/agent/wallet/redeem',json={'code':'BOUNDARY-CODE','request_key':'r'}).status_code==422
    a.patch('/api/agent/admin/codes/'+item['id'],json={'enabled':True})
    body={'code':'BOUNDARY-CODE','request_key':'r'}
    assert b.post('/api/agent/wallet/redeem',json=body).status_code==200
    assert b.post('/api/agent/wallet/redeem',json=body).status_code==200
    assert bill.wallet(owner)['balance']==1
    assert a.post('/api/agent/wallet/redeem',json=body).status_code==409
    instant=store.now();monkeypatch.setattr(store,'now',lambda:instant+timedelta(days=1))
    with pytest.raises(HTTPException) as err:bill.redeem(owner,'BOUNDARY-CODE','expired')
    assert err.value.status_code==422


def test_legacy_migration_preserves_owner_and_backup(tmp_path,monkeypatch):
    import sqlite3
    from app.services.agent_schema import migrate
    monkeypatch.setenv('LASER_ADMIN_USERNAME','legacy')
    path=tmp_path/'state.sqlite3';conn=sqlite3.connect(path)
    conn.executescript("CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT,password TEXT,admin INTEGER); INSERT INTO users VALUES('same-id','legacy','hash',1); CREATE TABLE events(owner TEXT,payload TEXT); INSERT INTO events VALUES('same-id','original feedback');")
    migrate(conn,path)
    assert conn.execute('SELECT id,email,bootstrap FROM users').fetchone()==('same-id',None,1)
    assert conn.execute('SELECT * FROM events').fetchone()==('same-id','original feedback')
    assert conn.execute('PRAGMA user_version').fetchone()[0]==2
    backups=list((tmp_path/'backups').glob('*.sqlite3'));assert len(backups)==1
    migrate(conn,path);assert len(list((tmp_path/'backups').glob('*.sqlite3')))==1
    with sqlite3.connect(backups[0]) as old:assert len(old.execute('PRAGMA table_info(users)').fetchall())==4
    conn.close()
