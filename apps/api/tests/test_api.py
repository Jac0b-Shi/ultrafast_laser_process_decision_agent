import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.settings import get_settings
from app.services.data_loader import load_dataset
from app.services.recommender import _add_intermediate_columns, INTERMEDIATE_METRIC_COLUMNS

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('LASER_EXPERIMENTS_DIR', str(tmp_path))
    monkeypatch.setenv('LASER_ADMIN_USERNAME', 'contract')
    monkeypatch.setenv('LASER_ADMIN_PASSWORD', 'contract-password-123')
    get_settings.cache_clear()
    with TestClient(app) as c:
        c.post('/api/agent/login', json={'username':'contract','password':'contract-password-123'})
        yield c
    get_settings.cache_clear()

def test_health(client):
    assert client.get('/health').json()['status'] == 'ok'

def test_site_config_comes_from_runtime_environment(client,monkeypatch):
    monkeypatch.setenv('LASER_ICP_NUMBER','test-icp')
    monkeypatch.setenv('LASER_POLICE_NUMBER','test-police')
    payload=client.get('/api/site-config').json()
    assert payload['icp_number']=='test-icp' and payload['police_number']=='test-police'

def test_dataset_summary(client):
    payload=client.get('/api/datasets/summary').json()
    materials={item['material']:item for item in payload['materials']}
    assert {'AlSiC','CFRP','SiC','ZrO2'}.issubset(materials)
    assert materials['CFRP']['sample_count']==128
    assert {'sq_um','sz_um','min_depth_um','max_depth_um'}.issubset(materials['AlSiC']['quality_metrics'])

def test_legacy_recommendation_requires_login():
    assert TestClient(app).post('/api/recommendations',json={'material':'BF33'}).status_code==401

def test_public_comparison_is_anonymous_and_read_only():
    frame=load_dataset()
    row=frame.loc[(frame.material=='BF33') & (frame.depth_um>0)].iloc[0]
    response=TestClient(app).post('/api/recommendations/public',json={'material':'BF33','target_depth_um':float(row.depth_um),'top_k':3})
    assert response.status_code==200,response.text
    assert response.json()['recommendations'][0]['candidate_source']=='historical'

def test_legacy_recommendation_single_historical(client):
    frame=load_dataset()
    row=frame.loc[(frame.material=='BF33') & (frame.depth_um>0)].iloc[0]
    response=client.post('/api/recommendations',json={'material':'BF33','target_depth_um':float(row.depth_um),'top_k':5})
    assert response.status_code==200,response.text
    recs=response.json()['recommendations']
    assert len(recs)==1 and recs[0]['source']=='historical' and recs[0]['score']==1

def test_no_empty_or_unknown_fallback(client):
    assert client.post('/api/recommendations',json={'material':'BF33'}).status_code==422
    assert client.post('/api/recommendations',json={'material':'unknown','target_depth_um':10}).status_code==422
    assert client.post('/api/recommendations',json={'material':'4H碳化硅','target_diameter_um':10}).status_code==422

def test_negative_measurements_retained_in_source():
    frame=load_dataset()
    flagged=frame.loc[(frame.material=='AlSiC') & (frame.depth_um<0)]
    assert len(flagged)>0
    assert all(bool(flags) for flags in flagged.quality_flags)

@pytest.mark.parametrize('material,metrics',[
 ('BF33',{'line_pulse_density_pulses_mm','pulse_spacing_um'}),
 ('4H碳化硅',{'threshold_relative_density'}),
 ('金刚石',{'cumulative_pulse_density','dose_index'}),
 ('微晶玻璃',{'pulse_time_interaction'}),
 ('高温合金',{'duty_cycle','power_chain_proxy_w','marking_energy_proxy'})])
def test_material_intermediates(material,metrics):
    frame=load_dataset()
    result=_add_intermediate_columns(frame.loc[frame.material==material],material=material)
    assert all(result[column].notna().any() for column in metrics)

def test_removed_global_write_routes(client):
    # Shared mutable JSONL endpoints must not remain callable.
    assert client.post('/api/feedback',json={}).status_code==404
    assert client.delete('/api/data-management/experiments/user:1').status_code==404
