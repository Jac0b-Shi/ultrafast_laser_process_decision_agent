import json
import numpy as np
import pandas as pd
import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings
from app.services import agent_store as store


@pytest.fixture
def clients(tmp_path,monkeypatch):
    monkeypatch.setenv('LASER_EXPERIMENTS_DIR',str(tmp_path))
    monkeypatch.setenv('LASER_ADMIN_USERNAME','admin')
    monkeypatch.setenv('LASER_ADMIN_PASSWORD','admin-password-123')
    get_settings.cache_clear();a=TestClient(create_app())
    a.post('/api/agent/login',json={'username':'admin','password':'admin-password-123'})
    a.post('/api/agent/users',json={'username':'other','password':'other-password-123','email':'other@example.com'})
    b=TestClient(create_app());b.post('/api/agent/login',json={'username':'other','password':'other-password-123'})
    yield a,b,tmp_path
    get_settings.cache_clear()


def frame():
    from app.services.data_loader import PARAMETER_COLUMNS,QUALITY_COLUMNS
    data=pd.DataFrame({'material':['BF33']*24,'case_id':[f'c{i}' for i in range(24)],'scan_speed_mm_s':np.repeat(np.arange(1,13),2),'repetition_frequency_khz':[100]*24,'depth_um':np.repeat(np.arange(1,13),2)*2})
    return data.reindex(columns=[*data.columns,*[c for c in PARAMETER_COLUMNS+QUALITY_COLUMNS if c not in data]])


def test_stream_events_persist_and_replay(clients,monkeypatch):
    from app.routers import agent
    monkeypatch.setattr(agent,'dataset',lambda owner:frame())
    a,b,_=clients;entity=a.post('/api/agent/conversations').json()['id']
    body={'message':'数据集里有哪些材料？','request_key':'stream-1','model_id':'local'}
    first=a.post(f'/api/agent/conversations/{entity}/turns/stream',json=body)
    assert first.status_code==200
    assert 'event: tool' in first.text and 'event: answer' in first.text and 'event: done' in first.text
    assert len(a.get(f'/api/agent/conversations/{entity}').json()['messages'])==1
    replay=a.post(f'/api/agent/conversations/{entity}/turns/stream',json=body)
    assert 'event: done' in replay.text
    assert len(a.get(f'/api/agent/conversations/{entity}').json()['messages'])==1
    assert b.post(f'/api/agent/conversations/{entity}/turns/stream',json=body).status_code==404
    assert a.post(f'/api/agent/conversations/{entity}/turns/stream',json={**body,'message':'different'}).status_code==409
    ordinary=a.post('/api/agent/conversations').json()['id']
    plain=a.post(f'/api/agent/conversations/{ordinary}/turns/stream',json={'message':'飞秒和皮秒有什么差异？','request_key':'stream-plain','model_id':'local'})
    assert '材料与数据概况' not in plain.text


def test_evaluation_version_activation_and_isolation(clients,monkeypatch):
    from app.services import agent_model_versions as versions
    a,b,tmp=clients;owner=a.get('/api/agent/me').json()['id']
    monkeypatch.setattr(versions,'dataset',lambda user:frame())
    job=a.post('/api/agent/analysis/evaluations',json={'material':'BF33','target':'depth_um','algorithms':['linear_regression']})
    assert job.status_code==200,job.text
    completed=versions.process_job(owner,job.json()['id'])
    assert completed['status']=='succeeded'
    listed=a.get('/api/agent/analysis/models').json();assert len(listed)==1 and not listed[0]['active']
    version=listed[0]
    activated=a.post('/api/agent/analysis/models/activate',json={'material':'BF33','target':'depth_um','version_id':version['id']})
    assert activated.status_code==200 and a.get('/api/agent/analysis/models').json()[0]['active']
    assert b.get('/api/agent/analysis/models').json()==[]
    assert b.post('/api/agent/analysis/models/activate',json={'material':'BF33','target':'depth_um','version_id':version['id']}).status_code==404
    model,metadata=versions.active_model(owner,'BF33','depth_um');assert metadata['id']==version['id'] and len(model.predict(frame().iloc[:1]))==1
    assert a.post('/api/agent/analysis/models/rollback',json={'material':'BF33','target':'depth_um'}).status_code==200
    assert not a.get('/api/agent/analysis/models').json()[0]['active']


def test_feedback_keeps_original_prediction_snapshot(clients):
    a,_,_=clients;owner=a.get('/api/agent/me').json()['id']
    rec={'task':{'material':'BF33'},'parameters':{'scan_speed_mm_s':10},'quality':{'depth_um':20},'source':'model','model_versions':{'depth_um':'version-1'}}
    entity=store.append(owner,'recommendation',rec)
    response=a.post('/api/agent/feedback',json={'recommendation_id':entity,'quality':{'depth_um':21.5}})
    assert response.status_code==200,response.text
    row=a.get('/api/agent/analysis/feedback-comparison').json()[0]
    assert row['predicted_quality']['depth_um']==20 and row['delta']['depth_um']==1.5
    assert row['model_versions']['depth_um']=='version-1'


@pytest.mark.parametrize('protocol',['chat_completions','ollama'])
def test_gateway_forwards_real_provider_fragments(monkeypatch,protocol):
    from app.services import agent_gateway as gateway
    model={'id':'m','protocol':protocol,'base_url':'http://model','model':'fixture','timeout':10,'secret':None,'supports_images':False,'max_input':10000,'max_output':100,'version':1,'name':'fixture','cost':{'cached':'0','uncached':'0','output':'0'},'sale':{'cached':'0','uncached':'0','output':'0'}}
    monkeypatch.setattr(gateway.models,'resolve',lambda *args:model)
    monkeypatch.setattr(gateway.billing,'recover',lambda:None)
    monkeypatch.setattr(gateway.billing,'begin',lambda *args,**kwargs:{'id':'call','output_budget':100})
    monkeypatch.setattr(gateway.billing,'received',lambda *args:None)
    @contextmanager
    def stream(*args,**kwargs):
        class Reply:
            def raise_for_status(self):pass
            def iter_lines(self):
                if protocol=='ollama':yield json.dumps({'message':{'content':'第一段'},'done':False});yield json.dumps({'message':{'content':'第二段'},'done':True,'prompt_eval_count':3,'eval_count':2})
                else:yield 'data: '+json.dumps({'choices':[{'delta':{'content':'第一段'}}]});yield 'data: '+json.dumps({'choices':[{'delta':{'content':'第二段'},'finish_reason':'stop'}],'usage':{'prompt_tokens':3,'completion_tokens':2}});yield 'data: [DONE]'
        yield Reply()
    monkeypatch.setattr(gateway.httpx,'stream',stream)
    fragments=[];result=gateway.invoke('owner','chat','key',[{'role':'user','content':'hi'}],on_fragment=fragments.append,json_output=False)
    assert fragments==['第一段','第二段'] and result['text']=='第一段第二段'


def test_gateway_cancellation_releases_reservation(monkeypatch):
    from app.services import agent_gateway as gateway
    model={'id':'m','protocol':'chat_completions','base_url':'http://model','model':'fixture','timeout':10,'secret':None,'supports_images':False,'max_input':10000,'max_output':100,'version':1,'name':'fixture','cost':{'cached':'0','uncached':'0','output':'0'},'sale':{'cached':'0','uncached':'0','output':'0'}}
    monkeypatch.setattr(gateway.models,'resolve',lambda *args:model)
    monkeypatch.setattr(gateway.billing,'recover',lambda:None)
    monkeypatch.setattr(gateway.billing,'begin',lambda *args,**kwargs:{'id':'call','output_budget':100})
    received=[];finished=[]
    monkeypatch.setattr(gateway.billing,'received',lambda *args:received.append(args))
    monkeypatch.setattr(gateway.billing,'finish',lambda *args,**kwargs:finished.append((args,kwargs)))
    @contextmanager
    def stream(*args,**kwargs):
        class Reply:
            def raise_for_status(self):pass
            def iter_lines(self):yield 'data: '+json.dumps({'choices':[{'delta':{'content':'不应发送'}}]})
        yield Reply()
    monkeypatch.setattr(gateway.httpx,'stream',stream)
    with pytest.raises(gateway.InvocationCancelled):
        gateway.invoke('owner','chat','key',[{'role':'user','content':'hi'}],cancelled=lambda:True)
    assert received==[('call',None)]
    assert finished==[(('call',False),{'reason':'用户停止生成'})]


def test_tool_plan_rejects_unregistered_calls(monkeypatch):
    from app.services import agent_gateway,agent_billing
    from app.services.agent_knowledge import orchestrate
    monkeypatch.setattr(agent_gateway,'invoke',lambda *args,**kwargs:{'text':json.dumps({'tools':['运行任意代码'],'explanation':'bad'}),'call_id':'call'})
    monkeypatch.setattr(agent_billing,'finish',lambda *args,**kwargs:None)
    with pytest.raises(Exception) as error:orchestrate('test',{},[],purpose='tools',owner='owner',request_key='key')
    assert getattr(error.value,'status_code',None)==502
