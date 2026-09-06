"""Integer micro-credit ledger and request-idempotent reservations."""
import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import timedelta, datetime
from uuid import uuid4
from fastapi import HTTPException
from app.services import agent_store as store

MICRO=1_000_000

def amount(value):
    try:
        n=Decimal(str(value))
        if not n.is_finite() or n<0 or n>Decimal('1000000000'):raise ValueError()
        return int((n*MICRO).quantize(Decimal(1),rounding=ROUND_HALF_UP))
    except (ValueError,InvalidOperation):raise HTTPException(422,'金额必须为有限非负数')

def wallet_row(conn,owner):
    conn.execute('INSERT OR IGNORE INTO wallets(owner) VALUES(?)',(owner,))
    row=conn.execute('SELECT w.*,u.credit_limit FROM wallets w JOIN users u ON u.id=w.owner WHERE owner=?',(owner,)).fetchone()
    if not row:raise HTTPException(404,'账号不存在')
    return row

def entry(conn,owner,kind,delta,held,reference,actor,reason):
    wallet_row(conn,owner)
    conn.execute('INSERT INTO ledger(owner,kind,amount,reserved_delta,reference,actor,reason,created) VALUES(?,?,?,?,?,?,?,?)',(owner,kind,delta,held,reference,actor,reason,store.now().isoformat()))
    conn.execute('UPDATE wallets SET balance=balance+?,reserved=reserved+? WHERE owner=?',(delta,held,owner))

def wallet(owner):
    with store.database() as conn:
        row=dict(wallet_row(conn,owner))
    return {k:row[k]/MICRO for k in ('balance','reserved','credit_limit')} | {'available':(row['balance']+row['credit_limit']-row['reserved'])/MICRO,'payment_blocked':row['balance']<0 or row['reserved']>row['balance']}

def recharge(owner,credit,actor,key,reason,kind='recharge'):
    n=amount(credit)
    if n<=0 or not key or not reason:raise HTTPException(422,'请填写正数额度、操作标识和原因')
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT amount,reason FROM ledger WHERE owner=? AND kind=? AND reference=?',(owner,kind,key)).fetchone()
        if old:
            if old['amount']!=n or old['reason']!=reason:raise HTTPException(409,'同一操作标识不能改变充值内容')
        else:entry(conn,owner,kind,n,0,key,actor,reason)
    return wallet(owner)

def price(snapshot,usage,kind):
    return sum(Decimal(str(snapshot[kind][key]))*Decimal(usage[key])/Decimal(1_000_000) for key in ('cached','uncached','output'))

def normalize_usage(body,protocol):
    if protocol=='ollama':
        u={'prompt_tokens':body.get('prompt_eval_count'),'completion_tokens':body.get('eval_count')}
    else:u=body.get('usage') or {}
    total=u.get('prompt_tokens',u.get('input_tokens'))
    output=u.get('completion_tokens',u.get('output_tokens'))
    cached=u.get('prompt_cache_hit_tokens',(u.get('prompt_tokens_details') or u.get('input_tokens_details') or {}).get('cached_tokens',0))
    uncached=u.get('prompt_cache_miss_tokens',None)
    if total is None and uncached is not None and isinstance(cached,int):total=uncached+cached
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (total,output,cached)) or cached>total:return None
    if uncached is not None and uncached!=total-cached:return None
    return {'cached':cached,'uncached':total-cached,'output':output}

def begin(owner,purpose,key,fingerprint,model,input_bound,platform=False):
    if not isinstance(key,str) or not key.strip() or len(key)>100:raise HTTPException(422,'付费请求需要唯一操作标识')
    snapshot={k:model[k] for k in ('cost','sale','version','name','model','max_output','max_input')}
    if input_bound>model['max_input']:raise HTTPException(422,'输入超过模型配置限制，请减少内容')
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        prior=conn.execute('SELECT * FROM calls WHERE owner=? AND purpose=? AND request_key=?',(owner,purpose,key)).fetchone()
        if prior:
            if prior['fingerprint']!=fingerprint:raise HTTPException(409,'重复操作标识的内容不同')
            if prior['status'] in ('pending','received'):raise HTTPException(409,'该请求仍在处理，请稍后查询')
            return {'replay':True,**dict(prior)}
        w=wallet_row(conn,owner)
        max_output=model['max_output'];reserved=0
        if not platform:
            if w['balance']<0 or w['reserved']>w['balance']:raise HTTPException(402,'已有欠费或透支预留，请先充值')
            available=w['balance']+w['credit_limit']-w['reserved']
            expensive_input='cached' if Decimal(snapshot['sale']['cached'])>Decimal(snapshot['sale']['uncached']) else 'uncached'
            input_usage={'cached':0,'uncached':0,'output':0};input_usage[expensive_input]=input_bound
            input_cost=amount(100*price(snapshot,input_usage,'sale'))
            per_output=Decimal(str(snapshot['sale']['output']))*100
            if available<input_cost:raise HTTPException(402,'余额与信用额度不足以覆盖输入')
            if per_output>0:max_output=min(max_output,int(Decimal(available-input_cost)/per_output))
            if max_output<1:raise HTTPException(402,'可用额度不足以生成输出')
            reserved=amount(100*price(snapshot,input_usage|{'output':max_output},'sale'))
            if reserved>available:raise HTTPException(402,'额度不足')
        snapshot['output_budget']=max_output;snapshot['input_bound']=input_bound;snapshot['platform']=platform
        call_id=str(uuid4());instant=store.now().isoformat()
        conn.execute('INSERT INTO calls(id,owner,request_key,purpose,fingerprint,model_id,price_snapshot,status,reserved,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(call_id,owner,key,purpose,fingerprint,model['id'],json.dumps(snapshot),'pending',reserved,instant,instant))
        entry(conn,owner,'reserve',0,reserved,call_id,owner,purpose)
    return {'id':call_id,'output_budget':max_output,'replay':False}

def received(call_id,usage):
    with store.database() as conn:
        row=conn.execute('SELECT * FROM calls WHERE id=?',(call_id,)).fetchone()
        snapshot=json.loads(row['price_snapshot'])
        cost=str(price(snapshot,usage,'cost')) if usage else None
        conn.execute("UPDATE calls SET usage=?,cost_rmb=?,status='received',updated=? WHERE id=? AND status='pending'",(json.dumps(usage) if usage else None,cost,store.now().isoformat(),call_id))

def finish(call_id,success,result=None,reason=''):
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM calls WHERE id=?',(call_id,)).fetchone()
        if not row or row['status'] not in ('pending','received'):return
        snap=json.loads(row['price_snapshot']);usage=json.loads(row['usage']) if row['usage'] else None
        charge=amount(100*price(snap,usage,'sale')) if success and usage and not snap['platform'] else 0
        # Never pass a user charge beyond the reservation, even if upstream over-reports.
        charge=min(charge,row['reserved'])
        entry(conn,row['owner'],'settle' if success else 'release',-charge,-row['reserved'],call_id,row['owner'],reason or row['purpose'])
        status=('success' if usage else 'unknown_usage') if success else 'failed'
        conn.execute('UPDATE calls SET status=?,charged=?,result=?,updated=? WHERE id=?',(status,charge,json.dumps(result,ensure_ascii=False) if result is not None else None,store.now().isoformat(),call_id))

def recover():
    # Calls have bounded network timeouts; expired reservations cannot be charged later.
    cutoff=(store.now()-timedelta(minutes=15)).isoformat()
    with store.database() as conn:ids=[r[0] for r in conn.execute("SELECT id FROM calls WHERE status IN ('pending','received') AND updated<?",(cutoff,))]
    for call_id in ids:finish(call_id,False,reason='进程异常或请求过期，释放预留；成本待核对')

def redeem(owner,code,key):
    if not isinstance(code,str) or not 8<=len(code.strip())<=128 or not isinstance(key,str) or not key.strip() or len(key)>100:
        raise HTTPException(422,'请填写有效激活码和唯一核销标识')
    digest=hashlib.sha256(code.strip().encode()).hexdigest()
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        prior=conn.execute('SELECT code_id FROM redemptions WHERE owner=? AND request_key=?',(owner,key)).fetchone()
        c=conn.execute('SELECT * FROM codes WHERE hash=?',(digest,)).fetchone()
        if prior:
            if not c or prior['code_id']!=c['id']:raise HTTPException(409,'核销标识已用于其他激活码')
            return {'ok':True}
        if not c or not c['enabled'] or (c['expires'] and datetime.fromisoformat(c['expires'])<=store.now()):raise HTTPException(422,'激活码无效或已过期')
        total=conn.execute('SELECT count(*) FROM redemptions WHERE code_id=?',(c['id'],)).fetchone()[0]
        personal=conn.execute('SELECT count(*) FROM redemptions WHERE code_id=? AND owner=?',(c['id'],owner)).fetchone()[0]
        if total>=c['total_limit'] or personal>=c['per_user_limit']:raise HTTPException(409,'激活码核销次数已用完')
        conn.execute('INSERT INTO redemptions(code_id,owner,request_key,created) VALUES(?,?,?,?)',(c['id'],owner,key,store.now().isoformat()))
        entry(conn,owner,'redeem',c['credit'],0,key,owner,c['label'])
    return {'ok':True}
