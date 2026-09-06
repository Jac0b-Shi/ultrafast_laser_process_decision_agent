"""Account administration, model settings, cost reporting and credit management."""
import csv
import hashlib
import io
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from app.services import agent_store as store, agent_billing as billing, agent_model_config as models, email_registration as email

router=APIRouter(prefix='/api/agent',tags=['administration'])

@router.get('/admin/email')
def email_settings(user=Depends(store.administrator)):
    return email.config()

@router.put('/admin/email')
def email_settings_update(body:dict,user=Depends(store.administrator)):
    return email.save(body,user['id'])

@router.post('/admin/email/test')
def email_test(body:dict,user=Depends(store.administrator)):
    email.send_test(body.get('recipient'))
    return {'ok':True}

class NewUser(BaseModel):
    username:str=Field(min_length=1,max_length=80)
    password:str=Field(min_length=12,max_length=256)
    email:str
    admin:bool=False

@router.post('/users')
def create_user(body:NewUser,user=Depends(store.administrator)):
    if not store.normalize_email(body.email):raise HTTPException(422,'请填写邮箱')
    result=store.create_user(body.username,body.password,body.admin,body.email)
    store.bootstrap()
    return result

@router.get('/users')
def users(user=Depends(store.administrator)):
    with store.database() as conn:rows=conn.execute('SELECT * FROM users ORDER BY username').fetchall()
    return [store.public_user(r)|{'wallet':billing.wallet(r['id'])} for r in rows]

def update_account(entity,body,actor,administrator):
    allowed={'email','password'}|({'username','enabled','admin','credit_limit'} if administrator else set())
    if set(body)-allowed:raise HTTPException(422,'包含不可修改的账号字段')
    changes={}
    if 'email' in body:
        email=store.normalize_email(body['email'])
        if not email:raise HTTPException(422,'邮箱不能为空')
        changes['email']=email
    if 'username' in body:
        if not isinstance(body['username'],str) or not 1<=len(body['username'].strip())<=80:raise HTTPException(422,'用户名无效')
        changes['username']=body['username'].strip()
    if 'password' in body:
        if not isinstance(body['password'],str) or not 12<=len(body['password'])<=256:raise HTTPException(422,'密码须为 12–256 字符')
        changes['password']=store.password_hash(body['password'])
    for k in ('enabled','admin'):
        if k in body:
            if not isinstance(body[k],bool):raise HTTPException(422,'状态必须为布尔值')
            changes[k]=int(body[k])
    if 'credit_limit' in body:changes['credit_limit']=billing.amount(body['credit_limit'])
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM users WHERE id=?',(entity,)).fetchone()
        if not row:raise HTTPException(404,'账号不存在')
        if row['bootstrap'] and any(k in changes for k in ('username','password','enabled','admin')):raise HTTPException(422,'初始账号身份由初始化配置管理，请创建数据库管理员')
        if 'credit_limit' in changes:
            w=billing.wallet_row(conn,entity)
            if changes['credit_limit']<max(0,w['reserved']-w['balance']):raise HTTPException(409,'信用额度不能低于欠费及预留占用')
        if changes:
            try:conn.execute('UPDATE users SET '+','.join(k+'=?' for k in changes)+' WHERE id=?',(*changes.values(),entity))
            except sqlite3.IntegrityError:raise HTTPException(409,'用户名或邮箱已存在')
        if any(k in changes for k in ('password','enabled','admin')):conn.execute('DELETE FROM sessions WHERE owner=?',(entity,))
        conn.execute('INSERT INTO admin_audit(actor,action,entity,detail,created) VALUES(?,?,?,?,?)',(actor,'account.update',entity,json.dumps({k:v for k,v in body.items() if k!='password'}),store.now().isoformat()))
    store.bootstrap()
    return {'ok':True}

@router.patch('/users/{entity}')
def edit_user(entity:str,body:dict,user=Depends(store.administrator)):
    return update_account(entity,body,user['id'],True)

@router.patch('/profile')
def profile(body:dict,user=Depends(store.current_user)):
    if 'password' in body:
        current=body.pop('current_password',None)
        with store.database() as conn:row=conn.execute('SELECT password FROM users WHERE id=?',(user['id'],)).fetchone()
        import hmac
        if not isinstance(current,str) or not hmac.compare_digest(store.password_hash(current,row['password'].split(':')[0]),row['password']):raise HTTPException(403,'当前密码不正确')
    return update_account(user['id'],body,user['id'],False)

@router.get('/models')
def available_models(user=Depends(store.current_user)):return models.listing()

@router.get('/admin/models')
def model_list(user=Depends(store.administrator)):return models.listing(True)

@router.post('/admin/models')
def model_create(body:dict,user=Depends(store.administrator)):return {'id':models.save(body,user['id'])}

@router.put('/admin/models/{entity}')
def model_update(entity:str,body:dict,user=Depends(store.administrator)):
    with store.database() as conn:
        if not conn.execute('SELECT 1 FROM models WHERE id=?',(entity,)).fetchone():raise HTTPException(404,'模型不存在')
    return {'id':models.save(body,user['id'],entity)}

@router.post('/admin/models/{entity}/test')
def model_test(entity:str,body:dict,user=Depends(store.administrator)):
    from app.services.agent_gateway import invoke
    result=invoke(user['id'],'connection_test',body.get('request_key'),[{'role':'user','content':'Return the word OK.'}],entity,True)
    if result.get('disabled'):raise HTTPException(422,'请先启用模型')
    if 'replay' in result:return result['replay']
    answer={'ok':True,'call_id':result['call_id']}
    billing.finish(result['call_id'],True,answer)
    return answer

@router.get('/wallet')
def wallet(user=Depends(store.current_user)):
    billing.recover();return billing.wallet(user['id'])

@router.get('/wallet/ledger')
def ledger(user=Depends(store.current_user)):
    with store.database() as conn:rows=conn.execute('SELECT * FROM ledger WHERE owner=? ORDER BY id DESC LIMIT 500',(user['id'],)).fetchall()
    return [{**dict(r),'amount':r['amount']/billing.MICRO,'reserved_delta':r['reserved_delta']/billing.MICRO} for r in rows]

@router.get('/wallet/calls')
def personal_calls(user=Depends(store.current_user)):
    with store.database() as conn:rows=conn.execute('SELECT * FROM calls WHERE owner=? ORDER BY created DESC LIMIT 500',(user['id'],)).fetchall()
    return [{'id':r['id'],'purpose':r['purpose'],'status':r['status'],'created':r['created'],'usage':json.loads(r['usage']) if r['usage'] else None,'charged_credit':r['charged']/billing.MICRO,'model':json.loads(r['price_snapshot'])['name'],'sale':json.loads(r['price_snapshot'])['sale']} for r in rows]

@router.post('/users/{entity}/recharge')
def recharge(entity:str,body:dict,user=Depends(store.administrator)):
    if body.get('kind','recharge') not in ('recharge','gift'):raise HTTPException(422,'充值类型无效')
    return billing.recharge(entity,body.get('credit'),user['id'],body.get('request_key'),body.get('reason'),body.get('kind','recharge'))

@router.post('/wallet/redeem')
def redeem(body:dict,user=Depends(store.current_user)):
    if not isinstance(body.get('code'),str) or not isinstance(body.get('request_key'),str) or not body['request_key']:raise HTTPException(422,'请填写激活码与操作标识')
    return billing.redeem(user['id'],body['code'],body['request_key'])

@router.get('/admin/codes')
def codes(user=Depends(store.administrator)):
    with store.database() as conn:rows=conn.execute('SELECT c.id,c.label,c.credit,c.total_limit,c.per_user_limit,c.expires,c.enabled,c.created,count(r.id) used FROM codes c LEFT JOIN redemptions r ON r.code_id=c.id GROUP BY c.id ORDER BY c.created DESC').fetchall()
    return [{**dict(r),'credit':r['credit']/billing.MICRO} for r in rows]

@router.post('/admin/codes')
def create_codes(body:dict,user=Depends(store.administrator)):
    credit=billing.amount(body.get('credit'));count=body.get('count',1)
    for v in (count,body.get('total_limit',1),body.get('per_user_limit',1)):
        if isinstance(v,bool) or not isinstance(v,int) or not 1<=v<=10000:raise HTTPException(422,'数量和次数须为 1–10000 的整数')
    if count>1000 or credit<=0:raise HTTPException(422,'每批最多 1000 个，额度须大于零')
    expiry=body.get('expires')
    if expiry:
        try:
            dt=datetime.fromisoformat(expiry.replace('Z','+00:00'))
            if dt.tzinfo is None or dt<=store.now():raise ValueError()
            expiry=dt.isoformat()
        except Exception:raise HTTPException(422,'有效期须为将来的带时区时间')
    if body.get('code') and count!=1:raise HTTPException(422,'指定码只能单个创建')
    result=[]
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        for _ in range(count):
            code=body.get('code') or secrets.token_urlsafe(24)
            if not isinstance(code,str) or not 8<=len(code)<=128:raise HTTPException(422,'指定码长度须为 8–128 字符')
            entity=str(uuid4());label=str(body.get('label') or 'Credit 激活码')[:100]
            try:conn.execute('INSERT INTO codes VALUES(?,?,?,?,?,?,?,?,?)',(entity,hashlib.sha256(code.strip().encode()).hexdigest(),label,credit,body.get('total_limit',1),body.get('per_user_limit',1),expiry,1,store.now().isoformat()))
            except sqlite3.IntegrityError:raise HTTPException(409,'激活码已经存在')
            result.append({'id':entity,'code':code,'credit':credit/billing.MICRO})
        conn.execute('INSERT INTO admin_audit(actor,action,detail,created) VALUES(?,?,?,?)',(user['id'],'codes.create',json.dumps({'count':count,'credit':credit}),store.now().isoformat()))
    return result

@router.patch('/admin/codes/{entity}')
def switch_code(entity:str,body:dict,user=Depends(store.administrator)):
    if not isinstance(body.get('enabled'),bool):raise HTTPException(422,'请指定启停状态')
    with store.database() as conn:
        if not conn.execute('UPDATE codes SET enabled=? WHERE id=?',(int(body['enabled']),entity)).rowcount:raise HTTPException(404,'激活码不存在')
    return {'ok':True}

@router.get('/admin/costs')
def costs(start:str|None=None,end:str|None=None,owner:str|None=None,model:str|None=None,purpose:str|None=None,format:str='json',user=Depends(store.administrator)):
    if end and len(end)==10:end+='T23:59:59.999999+00:00'
    conditions=[];values=[]
    for column,operator,value in [('created','>=',start),('created','<=',end),('owner','=',owner),('model_id','=',model),('purpose','=',purpose)]:
        if value:conditions.append(column+operator+'?');values.append(value)
    query='SELECT * FROM calls'+(' WHERE '+' AND '.join(conditions) if conditions else '')+' ORDER BY created DESC'
    with store.database() as conn:
        rows=[dict(r) for r in conn.execute(query,values)]
        funding_conditions=[];funding_values=[]
        for column,operator,value in [('created','>=',start),('created','<=',end),('owner','=',owner)]:
            if value:funding_conditions.append(column+operator+'?');funding_values.append(value)
        funding={r['kind']:r['total']/billing.MICRO for r in conn.execute("SELECT kind,SUM(amount) total FROM ledger WHERE kind IN ('recharge','gift','redeem')"+(' AND '+' AND '.join(funding_conditions) if funding_conditions else '')+' GROUP BY kind',funding_values)}
    safe=[]
    from decimal import Decimal
    cost=Decimal(0);charged=0;failed=Decimal(0);tokens=dict.fromkeys(('cached','uncached','output'),0)
    for r in rows:
        usage=json.loads(r['usage']) if r['usage'] else {}
        for k in tokens:tokens[k]+=usage.get(k,0)
        c=Decimal(r['cost_rmb']) if r['cost_rmb'] is not None else None
        if c is not None:cost+=c
        if c is not None and r['status']=='failed':failed+=c
        charged+=r['charged']
        safe.append({k:r[k] for k in ('id','owner','purpose','model_id','status','cost_rmb','created')}|{'charged_credit':r['charged']/billing.MICRO,**usage})
    if format=='csv':
        buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=['id','owner','purpose','model_id','status','cost_rmb','charged_credit','cached','uncached','output','created']);writer.writeheader();writer.writerows(safe)
        return Response('\ufeff'+buffer.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=costs.csv'})
    revenue=Decimal(charged)/billing.MICRO/100
    return {'rows':safe,'summary':{'cost_rmb':str(cost),'consumption_rmb':str(revenue),'margin_rmb':str(revenue-cost),'failed_cost_rmb':str(failed),'unknown_usage':sum(r['cost_rmb'] is None for r in rows),'tokens':tokens,'recharge_credit':funding.get('recharge',0),'gift_credit':funding.get('gift',0),'redeem_credit':funding.get('redeem',0)}}
