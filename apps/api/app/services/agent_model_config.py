"""Database-owned provider configuration and encrypted, write-only credentials."""
import json
import os
from pathlib import Path
from uuid import uuid4
from decimal import Decimal
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from fastapi import HTTPException
import yaml
from app.services import agent_store as store
from app.settings import get_settings

PRICE_KEYS=('cached','uncached','output')

def cipher():
    path=get_settings().experiments_dir/'agent'/'secrets'/'model.key'
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with store.database() as conn:
            if conn.execute("SELECT 1 FROM models WHERE secret IS NOT NULL LIMIT 1").fetchone():
                raise HTTPException(503,'模型密钥文件缺失，请从配套备份恢复')
        try:
            with path.open('xb') as f:f.write(Fernet.generate_key())
            path.chmod(0o600)
        except FileExistsError:pass
    return Fernet(path.read_bytes())

def clean(body):
    result={k:body[k] for k in ('name','protocol','base_url','model','enabled','visible','default','supports_images','max_input','max_output','timeout','cost','sale') if k in body}
    if result.get('protocol') not in ('chat_completions','ollama'):raise HTTPException(422,'未知模型协议')
    url=urlparse(result.get('base_url',''))
    if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:raise HTTPException(422,'服务地址必须是无凭据的 HTTP(S) 地址')
    if not result.get('name') or not result.get('model'):raise HTTPException(422,'请填写显示名称和模型标识')
    for k,lo,hi in [('max_input',1,2_000_000),('max_output',1,1_000_000),('timeout',1,600)]:
        if isinstance(result.get(k),bool) or not isinstance(result.get(k),int) or not lo<=result[k]<=hi:raise HTTPException(422,'模型限制超出有效范围')
    for kind in ('cost','sale'):
        values=result.get(kind,{})
        try:
            if set(values)!=set(PRICE_KEYS):raise ValueError()
            for key in PRICE_KEYS:
                d=Decimal(str(values[key]))
                if not d.is_finite() or d<0 or d>1_000_000:raise ValueError()
            result[kind]={k:str(Decimal(str(values[k]))) for k in PRICE_KEYS}
        except Exception:raise HTTPException(422,'请填写三项有效非负单价')
    for k in ('enabled','visible','default','supports_images'):
        if not isinstance(result.get(k,False),bool):raise HTTPException(422,'启停设置无效')
        result.setdefault(k,False)
    result['base_url']=result['base_url'].rstrip('/')
    return result

def save(body,actor,entity=None):
    config=clean(body);entity=entity or str(uuid4());instant=store.now().isoformat()
    key=body.get('api_key')
    if key is not None and (not isinstance(key,str) or len(key)>8192):raise HTTPException(422,'API Key 格式无效')
    encrypted=cipher().encrypt(key.encode()).decode() if key else None
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        prior=conn.execute('SELECT * FROM models WHERE id=?',(entity,)).fetchone()
        version=prior['version']+1 if prior else 1
        if prior and not body.get('clear_key') and not key:encrypted=prior['secret']
        if config['default']:
            for r in conn.execute('SELECT * FROM models WHERE id<>?',(entity,)).fetchall():
                other=json.loads(r['config'])
                if other.get('default'):
                    other['default']=False
                    conn.execute('UPDATE models SET config=? WHERE id=?',(json.dumps(other),r['id']))
        conn.execute('INSERT OR REPLACE INTO models VALUES(?,?,?,?,?)',(entity,version,json.dumps(config),encrypted,instant))
        conn.execute('INSERT INTO model_versions VALUES(?,?,?,?)',(entity,version,json.dumps(config),instant))
        conn.execute('INSERT INTO admin_audit(actor,action,entity,detail,created) VALUES(?,?,?,?,?)',(actor,'model.save',entity,json.dumps(config),instant))
    return entity

def import_legacy():
    with store.database() as conn:
        if conn.execute("SELECT 1 FROM settings WHERE key='provider_imported'").fetchone():return
    path=get_settings().config_dir/'providers.yaml'
    data=yaml.safe_load(path.read_text(encoding='utf-8')) if path.exists() else {}
    for name,c in (data or {}).get('providers',{}).items():
        if c.get('type') not in ('chat_completions','ollama'):continue
        entity='import-'+name
        with store.database() as conn:
            if conn.execute('SELECT 1 FROM models WHERE id=?',(entity,)).fetchone():continue
        save({'name':name,'protocol':c['type'],'base_url':c['base_url'],'model':c.get('model',c.get('chat_model')),'enabled':bool(c.get('enabled',False)),'visible':True,'default':name==os.getenv('LASER_LLM_PROVIDER',data.get('default_provider')),'supports_images':False,'max_input':16384,'max_output':1024,'timeout':20,'cost':dict.fromkeys(PRICE_KEYS,'0'),'sale':dict.fromkeys(PRICE_KEYS,'0'),'api_key':os.getenv(c.get('api_key_env',''),'')},'migration',entity)
    with store.database() as conn:conn.execute("INSERT OR IGNORE INTO settings VALUES('provider_imported','true')")

def listing(admin=False):
    import_legacy()
    with store.database() as conn:rows=conn.execute('SELECT * FROM models ORDER BY updated,id').fetchall()
    result=[]
    for row in rows:
        c=json.loads(row['config'])
        if not admin and (not c['visible'] or not c['enabled']):continue
        c.setdefault('supports_images',False)
        if not admin:c={k:c[k] for k in ('name','model','sale','default','supports_images')}
        result.append({**c,'id':row['id'],'version':row['version'],**({'has_key':bool(row['secret'])} if admin else {})})
    return result

def resolve(entity=None,platform=False):
    import_legacy()
    with store.database() as conn:rows=conn.execute('SELECT * FROM models').fetchall()
    available=[{**json.loads(r['config']),'id':r['id'],'version':r['version'],'secret':r['secret']} for r in rows]
    if entity=='local':return None
    if entity:
        found=next((m for m in available if m['id']==entity and m['enabled'] and (m['visible'] or platform)),None)
        if not found:raise HTTPException(422,'模型未开放或已停用')
    else:found=next((m for m in available if m['default'] and m['enabled'] and (m['visible'] or platform)),None)
    return found
