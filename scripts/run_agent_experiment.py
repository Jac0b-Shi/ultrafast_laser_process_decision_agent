"""Frozen group holdout. Outputs are independent from the earlier research pipeline."""
import hashlib
import json
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.services.data_loader import load_dataset, PARAMETER_COLUMNS
from app.services.agent_models import groups, select_model, pipeline

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/"configs/agent_experiment.json").read_text())
OUT = ROOT/"data/processed/agent_experiment"


def metrics(y, p):
    return {"rmse": float(mean_squared_error(y,p)**.5), "mae": float(mean_absolute_error(y,p)), "r2": float(r2_score(y,p))}


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    frame = load_dataset()
    reports, predictions, split_records, audits, replay, skipped = [], [], [], [], [], []
    for material, material_frame in frame.groupby("material"):
        material_frame = material_frame.reset_index(drop=True)
        gid = groups(material_frame)
        if len(set(gid)) < CONFIG["minimum_groups"]:
            skipped.append({"material":material,"reason":"insufficient independent groups"})
            continue
        dev_index, test_index = next(GroupShuffleSplit(n_splits=1,test_size=CONFIG["test_fraction"],random_state=CONFIG["seed"]).split(material_frame, groups=gid))
        assert not set(gid[dev_index]) & set(gid[test_index])
        split_records.extend({"material":material,"case_id":str(row.case_id),"group":gid[i],"split":"development" if i in set(dev_index) else "test"} for i,row in material_frame.iterrows())
        for target in CONFIG["targets"]:
            development = material_frame.iloc[dev_index].dropna(subset=[target])
            test = material_frame.iloc[test_index].dropna(subset=[target])
            development = development.loc[development[target]>=0]
            test = test.loc[test[target]>=0]
            if len(development)<CONFIG["minimum_samples"] or len(test)<4:
                skipped.append({"material":material,"target":target,"reason":"insufficient observed responses"})
                continue
            print(material,target,len(development),len(test),flush=True)
            for mode in CONFIG["modes"]:
                for family in ("simple","complex") if mode in ("raw","fusion") else ("simple",):
                    model,audit=select_model(development,target,CONFIG[family+"_models"],mode,CONFIG["selection_budget_seconds"])
                    pred=model.predict(test)
                    variant=mode+"_"+family
                    reports.append({"material":material,"target":target,"variant":variant,"algorithm":audit["selected"],"n_development":len(development),"n_test":len(test),**metrics(test[target],pred)})
                    audits.append({"material":material,"target":target,"variant":variant,**audit})
                    predictions.extend({"material":material,"target":target,"variant":variant,"case_id":str(row.case_id),"measured":float(row[target]),"predicted":float(p)} for (_,row),p in zip(test.iterrows(),pred))
            # Nearest historical case baseline, distance fitted on development inputs.
            cols=[c for c in PARAMETER_COLUMNS if development[c].notna().any()]
            med=development[cols].median(); scale=(development[cols].quantile(.75)-development[cols].quantile(.25)).replace(0,1)
            ref=(development[cols].fillna(med)-med)/scale
            baseline=[]
            for _,row in test.iterrows():
                point=(row[cols].fillna(med)-med)/scale
                best=((ref-point)**2).mean(axis=1).idxmin()
                baseline.append(float(development.loc[best,target]))
            reports.append({"material":material,"target":target,"variant":"historical_nearest","algorithm":"nearest_case","n_development":len(development),"n_test":len(test),**metrics(test[target],baseline)})
            predictions.extend({"material":material,"target":target,"variant":"historical_nearest","case_id":str(row.case_id),"measured":float(row[target]),"predicted":float(p)} for (_,row),p in zip(test.iterrows(),baseline))
            # Feedback experiment has its own fixed validation groups INSIDE development.
            dg=groups(development)
            pool_i,val_i=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=43).split(development,groups=dg))
            pool=development.iloc[pool_i]; validation=development.iloc[val_i]
            ordered=np.array(sorted(set(groups(pool)))); np.random.default_rng(42).shuffle(ordered)
            for mode in ("raw","fusion"):
                for fraction in CONFIG["feedback_fractions"]:
                    selected=ordered[:max(3,int(len(ordered)*fraction))]
                    training=pool.loc[np.isin(groups(pool),selected)]
                    if len(training)<8 or len(validation)<2:
                        continue
                    model,audit=select_model(training,target,CONFIG["simple_models"],mode,CONFIG["selection_budget_seconds"])
                    replay.append({"material":material,"target":target,"mode":mode,"fraction":fraction,"n_train":len(training),**metrics(validation[target],model.predict(validation))})
    pd.DataFrame(reports).to_csv(OUT/"metrics.csv",index=False)
    pd.DataFrame(predictions).to_csv(OUT/"predictions.csv",index=False)
    pd.DataFrame(split_records).to_csv(OUT/"split_manifest.csv",index=False)
    pd.DataFrame(replay).to_csv(OUT/"feedback.csv",index=False)
    (OUT/"selection_audit.json").write_text(json.dumps(audits,indent=2),encoding="utf-8")
    (OUT/"provenance.json").write_text(json.dumps({"config":CONFIG,"skipped":skipped,"rows":len(frame),"data_hash":hashlib.sha256(pd.util.hash_pandas_object(frame.astype(str),index=False).values.tobytes()).hexdigest()},indent=2),encoding="utf-8")
    print("Saved",OUT,flush=True)


if __name__ == "__main__":
    warnings.filterwarnings("ignore",category=UserWarning)
    run()
