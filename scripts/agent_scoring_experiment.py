"""Evaluate target ranking using frozen held-out predictions; never tune on test outcomes."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from app.services.data_loader import load_dataset, PARAMETER_COLUMNS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data/processed/agent_experiment"


def run():
    frame=load_dataset().set_index("case_id")
    split=pd.read_csv(OUT/"split_manifest.csv")
    pred=pd.read_csv(OUT/"predictions.csv")
    audit=json.loads((OUT/"selection_audit.json").read_text())
    rows=[]
    for (material,target),p in pred.loc[pred.variant=="fusion_simple"].groupby(["material","target"]):
        ids=split.loc[(split.material==material)&(split.split=="development"),"case_id"]
        dev=frame.loc[ids].dropna(subset=[target]);dev=dev.loc[dev[target]>=0]
        cols=[c for c in PARAMETER_COLUMNS if dev[c].notna().any()]
        med=dev[cols].median();scale=(dev[cols].quantile(.75)-dev[cols].quantile(.25)).replace(0,1)
        reference=(dev[cols].fillna(med)-med)/scale
        distances=[]
        for cid in p.case_id:
            point=(frame.loc[cid,cols].fillna(med)-med)/scale
            distances.append(float(np.sqrt(((reference-point)**2).mean(axis=1)).min()))
        a=next(a for a in audit if a["material"]==material and a["target"]==target and a["variant"]=="fusion_simple")
        tolerance=max(float(dev[target].quantile(.75)-dev[target].quantile(.25))*.1,.001)
        for quantile in (.25,.5,.75):
            nominal=float(dev[target].quantile(quantile))
            losses=abs(p.predicted.to_numpy()-nominal)/max(tolerance,abs(nominal)*.01,.001)
            for variant in ("constraint_only","constraint_uncertainty","full_score"):
                score=losses.copy()
                if variant!="constraint_only":score+=.2*a["validation_rmse"]/max(tolerance,abs(nominal)*.01,.001)
                if variant=="full_score":score+=.2*np.asarray(distances)
                index=int(np.argmin(score));chosen=p.iloc[index]
                rows.append({"material":material,"target":target,"variant":variant,"nominal":nominal,"tolerance":tolerance,"case_id":chosen.case_id,"predicted":chosen.predicted,"measured":chosen.measured,"absolute_target_error":abs(chosen.measured-nominal),"normalized_target_error":abs(chosen.measured-nominal)/tolerance,"satisfied":abs(chosen.measured-nominal)<=tolerance,"domain_distance":distances[index]})
    pd.DataFrame(rows).to_csv(OUT/"scoring.csv",index=False)
    print("Scoring tasks:",len(rows))

if __name__=="__main__":run()
