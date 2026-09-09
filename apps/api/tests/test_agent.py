from datetime import timedelta
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import get_settings
from app.services import agent_store as store
from app.services.agent_models import groups, select_model
from app.services.agent_decision import quality_loss


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv("LASER_EXPERIMENTS_DIR", str(tmp_path))
    monkeypatch.setenv("LASER_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LASER_ADMIN_PASSWORD", "admin-password-123")
    get_settings.cache_clear()
    app = create_app()
    a, b = TestClient(app), TestClient(app)
    assert a.post("/api/agent/login", json={"username": "admin", "password": "admin-password-123"}).status_code == 200
    assert a.post("/api/agent/users", json={"username": "second", "password": "second-password-123", "email":"second@example.com"}).status_code == 200
    assert b.post("/api/agent/login", json={"username": "second", "password": "second-password-123", "email":"second@example.com"}).status_code == 200
    yield a, b
    get_settings.cache_clear()


def test_isolation_and_recycle(clients, monkeypatch):
    a, b = clients
    conversation = a.post("/api/agent/conversations").json()["id"]
    assert b.get(f"/api/agent/conversations/{conversation}").status_code == 404
    body = {"material": "BF33", "parameters": {"scan_speed_mm_s": 10}, "quality": {"depth_um": 20}}
    record = a.post("/api/agent/feedback", json=body).json()["id"]
    assert b.get("/api/agent/feedback").json() == []
    assert b.delete(f"/api/agent/feedback/{record}").status_code == 404
    assert b.put(f"/api/agent/feedback/{record}", json={"quality": {"depth_um": 22}}).status_code == 404
    assert a.put(f"/api/agent/feedback/{record}", json={"quality": {"depth_um": 21}}).status_code == 200
    assert a.delete(f"/api/agent/feedback/{record}").status_code == 200
    assert a.get("/api/agent/feedback").json() == []
    assert a.post(f"/api/agent/feedback/{record}/restore").status_code == 200
    assert a.get("/api/agent/feedback").json()[0]["quality"]["depth_um"] == 21
    a.delete(f"/api/agent/feedback/{record}")
    instant = store.now()
    monkeypatch.setattr(store, "now", lambda: instant+timedelta(days=31))
    a.post("/api/agent/login", json={"username": "admin", "password": "admin-password-123"})
    assert a.post(f"/api/agent/feedback/{record}/restore").status_code == 409
    with store.database() as conn:
        rows = conn.execute("SELECT action FROM events WHERE entity=? ORDER BY seq", (record,)).fetchall()
    assert [r["action"] for r in rows] == ["create", "revise", "delete", "restore", "delete"]


def test_knowledge_and_auth(clients):
    a, b = clients
    doc = a.post("/api/agent/knowledge", files={"file": ("private.txt", b"pulse density frequency scan speed")}).json()["id"]
    assert b.get(f"/api/agent/knowledge/{doc}/download").status_code == 404
    assert b.delete(f"/api/agent/knowledge/{doc}").status_code == 404
    assert b.get("/api/agent/knowledge").json() == []
    assert a.get(f"/api/agent/knowledge/{doc}/download").content == b"pulse density frequency scan speed"
    assert a.post("/api/agent/knowledge", files={"file": ("bad.pdf", b"not a pdf")}).status_code == 422
    assert b.post("/api/agent/users", json={"username": "bad", "password": "password-123456"}).status_code == 403
    a.post("/api/agent/logout")
    assert a.get("/api/agent/me").status_code == 401


def test_history_self_match_and_empty_input(clients, monkeypatch):
    from app.services import agent_decision
    a, b = clients
    frame = pd.DataFrame([{ "material": "BF33", "case_id": "known", "scan_speed_mm_s": 10, "depth_um": 20}])
    from app.services.data_loader import PARAMETER_COLUMNS, QUALITY_COLUMNS
    frame = frame.reindex(columns=[*frame.columns, *[c for c in PARAMETER_COLUMNS+QUALITY_COLUMNS if c not in frame]])
    monkeypatch.setattr(agent_decision, "dataset", lambda owner: frame)
    entity = a.post("/api/agent/conversations").json()["id"]
    url = f"/api/agent/conversations/{entity}/messages"
    assert a.post(url, json={"task": {}}).status_code == 422
    task = {"material": "BF33", "targets": {"depth_um": {"value":20,"tolerance":0,"operator":"eq","unit":"um"}}}
    response = a.post(url,json={"task": task})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source"] == "historical" and result["match_score"] == 1
    assert b.get("/api/agent/recommendations/"+result["id"]).status_code == 404
    assert b.post("/api/agent/feedback", json={"recommendation_id":result["id"],"quality":{"depth_um":20}}).status_code == 404
    task["material"] = "unknown"
    assert a.post(url,json={"task":task}).status_code == 422
    task["material"] = "BF33"
    task["targets"]["depth_um"]["unit"] = ""
    assert a.post(url,json={"task":task}).status_code == 422


def test_grouped_model_and_score():
    frame = pd.DataFrame({"material": ["BF33"]*24, "scan_speed_mm_s": np.repeat(np.arange(1,13),2), "repetition_frequency_khz": [100]*24})
    frame["depth_um"] = frame.scan_speed_mm_s*2
    grouped = groups(frame)
    assert len(set(grouped)) == 12
    model, audit = select_model(frame, "depth_um", ["linear_regression"])
    assert audit["validation_rmse"] < 1e-8
    assert len(model.predict(frame.iloc[:2])) == 2
    assert quality_loss({"depth_um":20},{"depth_um":{"value":20,"tolerance":0,"operator":"eq"}}) == (0,True)


def test_generated_candidate_and_feedback_versions(clients, monkeypatch):
    from app.services import agent_decision
    from app.services.data_loader import PARAMETER_COLUMNS, QUALITY_COLUMNS
    a, b = clients
    frame = pd.DataFrame({"material": ["BF33"]*12, "case_id": [f"c{i}" for i in range(12)], "scan_speed_mm_s": np.arange(1,13), "depth_um": np.arange(1,13)*2})
    frame = frame.reindex(columns=[*frame.columns, *[c for c in PARAMETER_COLUMNS+QUALITY_COLUMNS if c not in frame]])
    monkeypatch.setattr(agent_decision,"dataset",lambda owner:frame)
    task={"material":"BF33","algorithm":"linear_regression","targets":{"depth_um":{"value":11,"tolerance":.01,"unit":"um","operator":"eq"}},"constraints":{"scan_speed_mm_s":{"min":1,"max":12,"step":.5}}}
    conversation=a.post("/api/agent/conversations").json()["id"]
    response=a.post(f"/api/agent/conversations/{conversation}/messages",json={"task":task})
    assert response.status_code==200,response.text
    result=response.json()
    assert result["source"]=="model"
    assert result["parameters"]["scan_speed_mm_s"]==5.5
    assert abs(result["quality"]["depth_um"]-11)<1e-8
    old_version=store.version(a.get('/api/agent/me').json()['id'])
    a.post('/api/agent/feedback',json={'recommendation_id':result['id'],'quality':{'depth_um':11.2}})
    assert store.version(a.get('/api/agent/me').json()['id'])!=old_version


def test_formula_approval_is_not_code_execution(clients):
    a,b=clients
    proposal={'operation':'ratio','inputs':['repetition_frequency_khz','scan_speed_mm_s'],'factor':1000,'unit':'pulses/mm','materials':['BF33'],'source':'doi:10.1038/s41598-018-35604-z'}
    assert b.post('/api/agent/formulas',json=proposal).status_code==403
    result=a.post('/api/agent/formulas',json=proposal)
    assert result.status_code==200
    entity=result.json()['id']
    assert a.post(f'/api/agent/formulas/{entity}/approve').status_code==200
    assert a.post('/api/agent/formulas',json={**proposal,'operation':'eval'}).status_code==422


def test_provider_failure_is_explicit(clients, tmp_path, monkeypatch):
    from app.services.agent_knowledge import orchestrate
    (tmp_path/'providers.yaml').write_text('default_provider: test\nproviders:\n  test:\n    enabled: true\n    type: chat_completions\n    base_url: https://unavailable.invalid\n    model: test\n')
    monkeypatch.setenv('LASER_CONFIG_DIR',str(tmp_path))
    monkeypatch.setenv('LASER_LLM_PROVIDER','test')
    get_settings.cache_clear()
    import httpx
    def fail(*args,**kwargs):
        raise httpx.ConnectError('test outage')
    monkeypatch.setattr(httpx,'stream',fail)
    from fastapi import HTTPException
    owner=clients[0].get('/api/agent/me').json()['id']
    with pytest.raises(HTTPException) as error:
        orchestrate('BF33',{},[],owner=owner,request_key='outage')
    assert error.value.status_code==502


def test_stale_revision_rejected(clients):
    a,_=clients
    owner=a.get('/api/agent/me').json()['id']
    entity=store.append(owner,'conversation',{'messages':[]})
    first=store.get_record(owner,'conversation',entity)
    store.append(owner,'conversation',{**first,'messages':['new']},entity,'revise')
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        store.append(owner,'conversation',first,entity,'revise')
    assert error.value.status_code==409


def test_origin_and_malformed_requests(clients):
    a, _ = clients
    assert a.post('/api/agent/conversations', headers={'Origin':'https://untrusted.invalid'}).status_code == 403
    entity=a.post('/api/agent/conversations').json()['id']
    url=f'/api/agent/conversations/{entity}/messages'
    assert a.post(url,json={'task':{'material':'BF33','targets':[]}}).status_code==422
    assert a.post('/api/agent/feedback',json={'material':'BF33','parameters':'invalid','quality':{}}).status_code==422


def test_draft_does_not_recommend_and_relation_requires_review(clients, monkeypatch):
    from app.routers import agent
    a,b=clients
    owner=a.get('/api/agent/me').json()['id']
    monkeypatch.setattr(agent,'orchestrate',lambda *args,**kwargs:{'status':'available','message':'review','draft':{'material':'BF33','targets':{'depth_um':{'value':10}}}})
    assert a.post('/api/agent/interpret',json={'message':'BF33 depth 10'}).json()['draft']['targets']['depth_um']=={'value':10}
    assert store.records(owner,'recommendation')==[]
    assert b.post('/api/agent/formulas/extract',json={'message':'relation','task':{'material':'BF33'}}).status_code==403
    proposal={'operation':'ratio','inputs':['repetition_frequency_khz','scan_speed_mm_s'],'factor':1000,'unit':'pulses/mm','materials':['BF33'],'source':'doc | page 1'}
    monkeypatch.setattr(agent,'search',lambda *args:[{'document_id':'doc','location':'page 1','text':'frequency divided by speed'}])
    monkeypatch.setattr(agent,'orchestrate',lambda *args,**kwargs:{'status':'available','message':'review','proposal':proposal})
    result=a.post('/api/agent/formulas/extract',json={'message':'relation','task':{'material':'BF33'}})
    assert result.status_code==200,result.text
    from app.services.agent_formulas import approved
    assert approved()==[]
    assert a.post('/api/agent/formulas/'+result.json()['id']+'/approve').status_code==200
    assert len(approved())==1


def test_conversation_turn_persists_safe_tool_events(clients, monkeypatch):
    from app.routers import agent
    from app.services.data_loader import PARAMETER_COLUMNS, QUALITY_COLUMNS
    a, b = clients
    frame = pd.DataFrame([{"material":"BF33", "case_id":"case-1", "scan_speed_mm_s":10, "depth_um":20}])
    frame = frame.reindex(columns=[*frame.columns, *[c for c in PARAMETER_COLUMNS+QUALITY_COLUMNS if c not in frame]])
    monkeypatch.setattr(agent, "dataset", lambda owner: frame)
    entity = a.post("/api/agent/conversations").json()["id"]
    url = f"/api/agent/conversations/{entity}/turns"
    response = a.post(url, json={"message":"飞秒激光和皮秒激光有什么差别？", "request_key":"ordinary-question"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendation"] is None
    assert body["events"] == []
    saved = a.get(f"/api/agent/conversations/{entity}").json()["messages"]
    assert saved[-1]["assistant"] == body["reply"]
    assert b.get(f"/api/agent/conversations/{entity}").status_code == 404
    assert a.post(url, json={"message":""}).status_code == 422


def test_transform_ignores_query_responses(clients):
    from app.services.agent_models import MechanismFeatures
    frame=pd.DataFrame({'material':['BF33']*12,'scan_speed_mm_s':np.arange(1,13),'repetition_frequency_khz':[100]*12,'depth_um':np.arange(12)*2})
    transformer=MechanismFeatures().fit(frame,frame.depth_um)
    expected=transformer.transform(frame)
    query=frame.copy();query['depth_um']=1e9
    pd.testing.assert_frame_equal(expected,transformer.transform(query))


@pytest.mark.parametrize('days,seconds,expected',[(29,86399,200),(30,0,409)])
def test_restore_exact_deadline(clients,monkeypatch,days,seconds,expected):
    a,_=clients
    body={'material':'BF33','parameters':{'scan_speed_mm_s':10},'quality':{'depth_um':20}}
    entity=a.post('/api/agent/feedback',json=body).json()['id']
    instant=store.now()
    monkeypatch.setattr(store,'now',lambda:instant)
    a.delete('/api/agent/feedback/'+entity)
    monkeypatch.setattr(store,'now',lambda:instant+timedelta(days=days,seconds=seconds))
    a.post('/api/agent/login',json={'username':'admin','password':'admin-password-123'})
    assert a.post('/api/agent/feedback/'+entity+'/restore').status_code==expected


def test_feedback_history_is_owner_scoped(clients):
    a,b=clients
    body={'material':'BF33','parameters':{'scan_speed_mm_s':10},'quality':{'depth_um':20}}
    entity=a.post('/api/agent/feedback',json=body).json()['id']
    a.put('/api/agent/feedback/'+entity,json={'quality':{'depth_um':21}})
    a.delete('/api/agent/feedback/'+entity)
    history=a.get('/api/agent/feedback/'+entity+'/history').json()
    assert [h['action'] for h in history]==['create','revise','delete']
    assert history[0]['data']['quality']['depth_um']==20
    assert history[1]['data']['quality']['depth_um']==21
    assert b.get('/api/agent/feedback/'+entity+'/history').status_code==404


def test_private_feedback_changes_only_owner_training_view(clients,monkeypatch):
    from app.services import agent_decision
    a,b=clients
    raw=pd.DataFrame({'case_id':['public'],'material':['BF33'],'scan_speed_mm_s':[1.0],'depth_um':[2.0]})
    monkeypatch.setattr(agent_decision,'load_dataset',lambda:raw.copy())
    owner=a.get('/api/agent/me').json()['id'];other=b.get('/api/agent/me').json()['id']
    body={'material':'BF33','parameters':{'scan_speed_mm_s':10},'quality':{'depth_um':20}}
    entity=a.post('/api/agent/feedback',json=body).json()['id']
    assert len(agent_decision.dataset(owner))==2
    assert len(agent_decision.dataset(other))==1
    a.put('/api/agent/feedback/'+entity,json={'quality':{'depth_um':21}})
    assert agent_decision.dataset(owner).iloc[-1].depth_um==21
    a.delete('/api/agent/feedback/'+entity)
    assert len(agent_decision.dataset(owner))==1
    a.post('/api/agent/feedback/'+entity+'/restore')
    assert agent_decision.dataset(owner).iloc[-1].depth_um==21
    assert len(agent_decision.dataset(other))==1
