"""Account-scoped evaluation jobs and immutable, checksummed model artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import platform
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import joblib
import pandas as pd
import sklearn
from fastapi import HTTPException

from app.settings import get_settings
from app.services import agent_store as store
from app.services.agent_decision import dataset
from app.services.agent_models import REGISTRY, select_model


def _artifact_dir(owner:str)->Path:
    path=get_settings().experiments_dir/'agent'/'model_artifacts'/owner
    path.mkdir(parents=True,exist_ok=True)
    return path


def _snapshot(frame:pd.DataFrame)->str:
    data=frame.sort_values([c for c in ('case_id','material') if c in frame]).to_json(orient='records',date_format='iso')
    return hashlib.sha256(data.encode()).hexdigest()


def create_job(owner:str,material:str,target:str,algorithms:list[str]):
    frame=dataset(owner)
    if material not in set(frame.material.dropna().astype(str)):raise HTTPException(422,'材料没有可用数据')
    if target not in frame or not frame.loc[frame.material==material,target].notna().any():raise HTTPException(422,'质量指标没有可用测量')
    selected=list(dict.fromkeys(algorithms))
    if not selected or any(item not in REGISTRY for item in selected):raise HTTPException(422,'请选择有效候选算法')
    limit=max(1,min(4,int(os.getenv('LASER_EVALUATION_PER_USER','1'))))
    job_id=str(uuid4())
    payload={'status':'queued','material':material,'target':target,'algorithms':selected,'created':store.now().isoformat()}
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        rows=conn.execute("SELECT * FROM events WHERE owner=? AND kind='evaluation_job' ORDER BY seq",(owner,)).fetchall()
        if sum(j.get('status') in ('queued','running') for j in store._project(rows).values())>=limit:raise HTTPException(409,'当前账号评估任务已达到上限')
        conn.execute("INSERT INTO events(owner,kind,entity,action,payload,created) VALUES(?,?,?,?,?,?)",(owner,'evaluation_job',job_id,'create',json.dumps(payload,ensure_ascii=False),store.now().isoformat()))
    return store.get_record(owner,'evaluation_job',job_id)


def jobs(owner:str):return store.records(owner,'evaluation_job')


def versions(owner:str):
    active={a['scope']:a.get('version_id') for a in store.records(owner,'model_activation')}
    current=store.version(owner)
    return [{**v,'active':active.get(v['scope'])==v['id'],'stale':v.get('data_version')!=current} for v in store.records(owner,'process_model')]


def process_job(owner:str,job_id:str):
    job=store.get_record(owner,'evaluation_job',job_id)
    if job['status'] not in ('queued','running'):return job
    if job['status']=='queued':store.append(owner,'evaluation_job',{**job,'status':'running','started':store.now().isoformat()},job_id,'revise')
    try:
        frame=dataset(owner);train=frame.loc[frame.material==job['material']].copy()
        model,audit=select_model(train,job['target'],job['algorithms'],budget_seconds=120)
        version_id=str(uuid4());path=_artifact_dir(owner)/(version_id+'.joblib')
        joblib.dump(model,path)
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        scope=job['material']+':'+job['target']
        metadata={'scope':scope,'material':job['material'],'target':job['target'],'algorithm':audit['selected'],'audit':audit,'data_version':store.version(owner),'training_snapshot':_snapshot(train),'feature_version':'mechanism-features-v1','environment':{'python':platform.python_version(),'sklearn':sklearn.__version__},'artifact':str(path.relative_to(get_settings().experiments_dir)),'checksum':checksum,'created':store.now().isoformat()}
        store.append(owner,'process_model',metadata,version_id)
        latest=store.get_record(owner,'evaluation_job',job_id)
        store.append(owner,'evaluation_job',{**latest,'status':'succeeded','version_id':version_id,'audit':audit,'finished':store.now().isoformat()},job_id,'revise')
    except Exception as exc:
        latest=store.get_record(owner,'evaluation_job',job_id)
        store.append(owner,'evaluation_job',{**latest,'status':'failed','error':str(exc)[:300],'finished':store.now().isoformat()},job_id,'revise')
    return store.get_record(owner,'evaluation_job',job_id)


def activate(owner:str,material:str,target:str,version_id:str|None):
    scope=material+':'+target
    if version_id:
        version=store.get_record(owner,'process_model',version_id)
        if version['scope']!=scope:raise HTTPException(422,'模型版本与材料或指标不匹配')
    existing=next((a for a in store.records(owner,'model_activation') if a['scope']==scope),None)
    payload={'scope':scope,'material':material,'target':target,'version_id':version_id,'changed':store.now().isoformat()}
    if existing:store.append(owner,'model_activation',{**existing,**payload},existing['id'],'revise')
    else:store.append(owner,'model_activation',payload,scope)
    return payload


def rollback(owner:str,material:str,target:str):
    scope=material+':'+target
    with store.database() as conn:
        rows=conn.execute("SELECT payload FROM events WHERE owner=? AND kind='model_activation' AND entity=? ORDER BY seq DESC",(owner,scope)).fetchall()
    if len(rows)<2:return activate(owner,material,target,None)
    previous=json.loads(rows[1]['payload']).get('version_id')
    return activate(owner,material,target,previous)


def active_model(owner:str,material:str,target:str):
    scope=material+':'+target
    activation=next((a for a in store.records(owner,'model_activation') if a['scope']==scope),None)
    if not activation or not activation.get('version_id'):return None
    version=store.get_record(owner,'process_model',activation['version_id'])
    path=get_settings().experiments_dir/version['artifact']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=version['checksum']:
        raise HTTPException(409,'已启用模型产物不可用或校验失败，请回滚或恢复自动选模')
    return joblib.load(path),version


def process_next():
    lease='process-model-evaluation';holder=str(uuid4());now=store.now();slots=max(1,min(4,int(os.getenv('LASER_EVALUATION_GLOBAL_SLOTS','1'))));slot=None
    with store.database() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM work_leases WHERE name=? AND expires<=?',(lease,now.isoformat()))
        for candidate in range(slots):
            conn.execute('INSERT OR IGNORE INTO work_leases(name,slot,owner,expires) VALUES(?,?,?,?)',(lease,candidate,holder,(now+timedelta(minutes=10)).isoformat()))
            held=conn.execute('SELECT owner FROM work_leases WHERE name=? AND slot=?',(lease,candidate)).fetchone()
            if held and held['owner']==holder:slot=candidate;break
        if slot is None:return None
    try:
        with store.database() as conn:rows=conn.execute("SELECT * FROM events WHERE kind='evaluation_job' ORDER BY seq").fetchall()
        by_owner={}
        for row in rows:by_owner.setdefault(row['owner'],[]).append(row)
        for owner,items in by_owner.items():
            for job in store._project(items).values():
                if job.get('status')=='queued':return process_job(owner,job['id'])
        return None
    finally:
        with store.database() as conn:conn.execute('DELETE FROM work_leases WHERE name=? AND slot=? AND owner=?',(lease,slot,holder))


def recover_jobs():
    with store.database() as conn:rows=conn.execute("SELECT * FROM events WHERE kind='evaluation_job' ORDER BY seq").fetchall()
    by_owner={}
    for row in rows:by_owner.setdefault(row['owner'],[]).append(row)
    for owner,items in by_owner.items():
        for job in store._project(items).values():
            if job.get('status')=='running':
                latest=store.get_record(owner,'evaluation_job',job['id'])
                store.append(owner,'evaluation_job',{**latest,'status':'queued','recovered':True},job['id'],'revise')
