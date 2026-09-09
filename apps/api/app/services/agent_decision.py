from __future__ import annotations

import hashlib
import json
import numpy as np
import pandas as pd
from fastapi import HTTPException
from app.services import agent_store as store
from app.services.agent_models import REGISTRY, groups, select_model
from app.services.data_loader import load_dataset, PARAMETER_COLUMNS, QUALITY_COLUMNS
from app.services.recommender import _add_intermediate_columns


def dataset(owner):
    public = load_dataset()
    private = []
    for item in store.records(owner, "feedback"):
        private.append({"case_id": item["id"], "material": item["material"], "source_file": "personal feedback", **item["parameters"], **item["quality"]})
    return pd.concat([public, pd.DataFrame(private)], ignore_index=True) if private else public


def validate_task(task, frame):
    if not isinstance(task.get("material"), str) or not task.get("material") or not isinstance(task.get("targets"), dict) or not task.get("targets"):
        raise HTTPException(422, "请选择材料并填写至少一个质量目标及容差（单位 μm）")
    if task["material"] not in set(frame.material):
        raise HTTPException(422, "该材料没有可用案例，请先添加加工记录")
    if not isinstance(task.get("algorithm", "auto"), str) or task.get("algorithm", "auto") not in {"auto", *REGISTRY}:
        raise HTTPException(422, "未知算法")
    for column, spec in task["targets"].items():
        if not isinstance(spec, dict) or column not in QUALITY_COLUMNS or spec.get("unit") != "um" or spec.get("operator") not in ("eq", "le", "ge"):
            raise HTTPException(422, "质量指标、比较方式或单位不正确（必须为 um）")
        for key in ("value", "tolerance"):
            value = spec.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
                raise HTTPException(422, "目标和容差必须为有限非负数")
    if not isinstance(task.get("constraints", {}), dict):
        raise HTTPException(422, "设备约束必须包含参数字段与范围")
    for column, bounds in task.get("constraints", {}).items():
        if column not in PARAMETER_COLUMNS or not isinstance(bounds, dict) or set(bounds)-{"min", "max", "step"}:
            raise HTTPException(422, "参数约束字段无效")
        if not all(not isinstance(v, bool) and isinstance(v, (int, float)) and np.isfinite(v) for v in bounds.values()):
            raise HTTPException(422, "约束必须为有限数值")
        if bounds.get("min", -np.inf) > bounds.get("max", np.inf) or bounds.get("step", 1) <= 0:
            raise HTTPException(422, "约束范围或设备步长无效")
        if column != "defocus_amount_mm" and any(bounds.get(k, 0) < 0 for k in ("min", "max")):
            raise HTTPException(422, "该工艺参数不能为负数")


def quality_loss(quality, targets):
    losses, fits = [], []
    for column, spec in targets.items():
        actual = quality.get(column)
        if actual is None or not np.isfinite(actual) or actual < 0:
            return float("inf"), False
        delta = actual-spec["value"]
        deviation = abs(delta) if spec["operator"] == "eq" else max(0, delta if spec["operator"] == "le" else -delta)
        fits.append(deviation <= spec["tolerance"]+1e-10)
        losses.append(deviation/max(spec["tolerance"], abs(spec["value"])*.01, .001))
    return float(np.mean(losses)), all(fits)


def numbers(row, columns):
    return {c: float(row[c]) for c in columns if c in row and pd.notna(row[c]) and np.isfinite(row[c])}


def decide(owner, task, proposed=None, history_only=False):
    full = dataset(owner)
    validate_task(task, full)
    frame = full.loc[full.material == task["material"]].copy()
    for c in QUALITY_COLUMNS:
        if c in frame:
            frame.loc[frame[c] < 0, c] = np.nan
    for c, bounds in task.get("constraints", {}).items():
        frame = frame.loc[frame[c].between(bounds.get("min", -np.inf), bounds.get("max", np.inf))]
    if frame.empty:
        raise HTTPException(422, "当前参数约束下没有支持案例，请调整约束或补充实验")
    raw_columns = [c for c in PARAMETER_COLUMNS if frame[c].notna().any()]
    scored = [(quality_loss(row, task["targets"])[0], i, quality_loss(row, task["targets"])[1]) for i, row in frame.iterrows()]
    scored = sorted((s for s in scored if np.isfinite(s[0])), key=lambda x: (x[0], str(frame.loc[x[1], "case_id"])))
    if not scored:
        raise HTTPException(422, "历史记录缺少所需质量测量，请补充实测数据")
    group_ids = groups(frame)
    group_map = dict(zip(frame.index, group_ids))
    def tie(item):
        group = frame.loc[group_ids == group_map[item[1]]]
        spread = group[list(task["targets"])].std(ddof=0).fillna(0).mean()
        return item[0], float(spread), -len(group), str(frame.loc[item[1], "case_id"])
    historical = sorted([s for s in scored if s[2]], key=tie)
    references = [{"case_id": str(frame.loc[i, "case_id"]), "parameters": numbers(frame.loc[i], PARAMETER_COLUMNS), "measured_quality": numbers(frame.loc[i], QUALITY_COLUMNS)} for _, i, _ in scored[:3]]
    audit = {}
    model_versions = {}
    fitted_intermediates = {}
    if historical:
        loss, index, _ = historical[0]
        row = frame.loc[index]
        quality = numbers(row, QUALITY_COLUMNS)
        parameters = numbers(row, PARAMETER_COLUMNS)
        source, uncertainty = "historical", {}
        confidence = {"basis": "measured", "case_id": str(row.case_id), "support_count": int(sum(group_ids == group_map[index]))}
        references = [{"case_id": str(row.case_id), "parameters": parameters, "measured_quality": quality}, *[r for r in references if r["case_id"] != str(row.case_id)]][:3]
    else:
        if history_only:return None
        if not any("step" in bounds for bounds in task.get("constraints", {}).values()):
            raise HTTPException(422, "没有满足目标的历史参数；请补充可调参数的设备范围与步长")
        # Generate only within observed per-axis bounds, preserving discrete settings.
        seeds = frame.loc[[i for _, i, _ in scored[:8]], raw_columns].dropna()
        if len(seeds) < 2:
            raise HTTPException(422, "完整参数案例不足，无法生成新参数")
        candidates = []
        for _, left in seeds.iterrows():
            for _, right in seeds.iterrows():
                for fraction in (.25, .5, .75):
                    point = left*(1-fraction)+right*fraction
                    for c in raw_columns:
                        # Only supplied continuous dimensions with an explicit device step are interpolated.
                        bounds = task.get("constraints", {}).get(c, {})
                        if "step" in bounds:
                            origin = bounds.get("min", float(frame[c].min()))
                            point[c] = origin+round((point[c]-origin)/bounds["step"])*bounds["step"]
                        else:
                            point[c] = left[c]
                    candidates.append(point)
        generated = pd.DataFrame(candidates).drop_duplicates()
        for c in raw_columns:
            generated = generated.loc[generated[c].between(frame[c].min(), frame[c].max())]
        generated["material"] = task["material"]
        known = set(map(tuple, frame[raw_columns].fillna(-1e300).to_numpy()))
        generated = generated.loc[[tuple(row) not in known for row in generated[raw_columns].to_numpy()]]
        if generated.empty:
            raise HTTPException(422, "设备步长与案例范围内没有有效候选")
        selected = [task["algorithm"]] if task.get("algorithm", "auto") != "auto" else proposed
        predictions, uncertainty = {}, {}
        for target in task["targets"]:
            try:
                from app.services.agent_model_versions import active_model
                active=active_model(owner,task['material'],target)
                if active:
                    model,version=active
                    audit[target]=version['audit']
                    model_versions[target]=version['id']
                else:model, audit[target] = select_model(frame, target, selected)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            predictions[target] = model.predict(generated)
            fitted_intermediates[target] = model.named_steps["mechanism"]
            uncertainty[target] = audit[target]["validation_rmse"]
        medians = frame[raw_columns].median()
        scale = (frame[raw_columns].quantile(.75)-frame[raw_columns].quantile(.25)).replace(0, 1)
        reference = (frame[raw_columns].fillna(medians)-medians)/scale
        distances = []
        for _, point in generated.iterrows():
            normalized = (pd.to_numeric(point[raw_columns])-medians)/scale
            distances.append(float(np.sqrt(((reference-normalized)**2).mean(axis=1).to_numpy(dtype=float)).min()))
        ranked = []
        for offset, (_, point) in enumerate(generated.iterrows()):
            q = {c: float(v[offset]) for c, v in predictions.items()}
            loss, fits = quality_loss(q, task["targets"])
            if not fits or distances[offset] > 1:
                continue
            risk = np.mean([uncertainty[c]/max(task["targets"][c]["tolerance"], abs(task["targets"][c]["value"])*.01, .001) for c in q])
            ranked.append((loss+.2*risk+.2*distances[offset], loss, offset, q))
        if not ranked:
            raise HTTPException(422, "验证模型未找到满足全部目标的受支持参数，请调整目标或补充测量")
        _, loss, offset, quality = min(ranked, key=lambda x: x[0])
        row = generated.iloc[offset]
        parameters = numbers(row, PARAMETER_COLUMNS)
        source = "model"
        confidence = {"basis": "grouped_validation", "domain_distance": distances[offset], "validation_rmse": uncertainty}
        normalized = (pd.to_numeric(row[raw_columns])-medians)/scale
        nearest = ((reference-normalized)**2).mean(axis=1).nsmallest(3).index
        references = [{"case_id": str(frame.loc[i, "case_id"]), "parameters": numbers(frame.loc[i], PARAMETER_COLUMNS), "measured_quality": numbers(frame.loc[i], QUALITY_COLUMNS)} for i in nearest]
    enriched = _add_intermediate_columns(pd.DataFrame([{**parameters, "material": task["material"]}]), reference_frame=frame)
    intermediate = numbers(enriched.iloc[0], [c for c in enriched if c not in PARAMETER_COLUMNS and c != "material"])
    by_target = {}
    for target, transformer in fitted_intermediates.items():
        transformed = transformer.transform(pd.DataFrame([{**parameters, "material": task["material"]}]))
        by_target[target] = numbers(transformed.iloc[0], [c for c in transformed if c not in PARAMETER_COLUMNS])
    if by_target:
        intermediate = next(iter(by_target.values()))
    from app.services.agent_formulas import approved
    formula_snapshot = approved()
    formula_version = hashlib.sha256(json.dumps(formula_snapshot, sort_keys=True).encode()).hexdigest()[:12]
    signature = hashlib.sha256(pd.util.hash_pandas_object(full.astype(str), index=False).values.tobytes()).hexdigest()[:16]
    return {"source": source, "parameters": parameters, "quality": quality, "match_score": 1/(1+loss), "confidence": confidence, "similar_cases": references, "intermediate_metrics": intermediate, "intermediate_by_target": by_target, "formula_snapshot": formula_snapshot, "model_audit": audit, "model_versions": model_versions, "data_version": signature+":"+store.version(owner), "model_version": "mechanism-grouped-v1:"+formula_version, "task": task}
