"""Verify saved experiment outputs against raw records and the frozen split protocol."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from app.services.data_loader import load_dataset
from app.services.agent_models import groups

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed/agent_experiment'
frame=load_dataset()
provenance=json.loads((OUT/'provenance.json').read_text())
config=json.loads((ROOT/'configs/agent_experiment.json').read_text())
assert provenance['config']==config
assert hashlib.sha256(pd.util.hash_pandas_object(frame.astype(str),index=False).values.tobytes()).hexdigest()==provenance['data_hash']
split=pd.read_csv(OUT/'split_manifest.csv',dtype={'group':str})
pred=pd.read_csv(OUT/'predictions.csv')
metrics=pd.read_csv(OUT/'metrics.csv')
feedback=pd.read_csv(OUT/'feedback.csv')
assert split.groupby(['material','group'])['split'].nunique().max()==1
assert frame.case_id.is_unique
by_id=frame.set_index('case_id')
for material,part in frame.groupby('material'):
    gid=groups(part)
    if len(set(gid))<config['minimum_groups']:continue
    dev,test=next(GroupShuffleSplit(n_splits=1,test_size=config['test_fraction'],random_state=config['seed']).split(part,groups=gid))
    assert set(part.iloc[test].case_id)==set(split.loc[(split.material==material)&(split.split=='test'),'case_id'])
for row in metrics.itertuples():
    part=pred.loc[(pred.material==row.material)&(pred.target==row.target)&(pred.variant==row.variant)]
    allowed=split.loc[(split.material==row.material)&(split.split=='test'),'case_id']
    expected=by_id.loc[allowed,row.target].dropna();expected=expected.loc[expected>=0]
    assert set(part.case_id)==set(expected.index)
    assert np.allclose(part.measured,by_id.loc[part.case_id,row.target])
    assert np.isclose(row.rmse,mean_squared_error(part.measured,part.predicted)**.5)
    assert np.isclose(row.mae,mean_absolute_error(part.measured,part.predicted))
    assert np.isclose(row.r2,r2_score(part.measured,part.predicted))
feedback_manifest=[]
for (material,target), rows in feedback.groupby(['material','target']):
    ids=split.loc[(split.material==material)&(split.split=='development'),'case_id']
    dev=by_id.loc[ids].dropna(subset=[target]);dev=dev.loc[dev[target]>=0]
    dg=groups(dev)
    pool_i,val_i=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(dev,groups=dg))
    pool=dev.iloc[pool_i];validation=dev.iloc[val_i]
    ordered=np.array(sorted(set(groups(pool))));np.random.default_rng(42).shuffle(ordered)
    for fraction in config['feedback_fractions']:
        selected=ordered[:max(3,int(len(ordered)*fraction))]
        train=pool.loc[np.isin(groups(pool),selected)]
        observed=rows.loc[rows.fraction==fraction]
        if observed.empty:continue
        assert set(train.index).isdisjoint(validation.index)
        assert set(groups(train)).isdisjoint(groups(validation))
        assert observed.n_train.eq(len(train)).all()
        feedback_manifest.append({'material':material,'target':target,'fraction':fraction,'training_ids':list(train.index),'validation_ids':list(validation.index)})
(OUT/'feedback_split_manifest.json').write_text(json.dumps(feedback_manifest,indent=2))
result={'passed':True,'rows':len(frame),'tasks':len(metrics[['material','target']].drop_duplicates()),'comparisons':len(metrics),'feedback_stages':len(feedback_manifest),'checks':['raw data hash','fixed group holdout','same test rows across models','raw measurements','all saved metrics recomputed','feedback wholly inside development'],'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','scipy','matplotlib']}}
(OUT/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
