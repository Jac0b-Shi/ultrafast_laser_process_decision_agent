"""A small typed calculation language; no eval, imports, or executable documents."""
import numpy as np
from fastapi import HTTPException
from app.services import agent_store as store
from app.services.data_loader import PARAMETER_COLUMNS


def validate(spec):
    if spec.get("operation") not in {"ratio", "product"}:
        raise HTTPException(422, "公式仅支持经审核的乘积与比值")
    if not isinstance(spec.get("inputs"), list) or len(spec["inputs"]) != 2 or any(c not in PARAMETER_COLUMNS for c in spec["inputs"]):
        raise HTTPException(422, "公式输入必须是两个已定义工艺字段")
    if not isinstance(spec.get("source"), str) or not spec["source"] or not isinstance(spec.get("unit"), str) or not spec["unit"] or not isinstance(spec.get("materials"), list) or not spec["materials"] or not all(isinstance(m, str) for m in spec["materials"]):
        raise HTTPException(422, "需注明来源、输出单位和适用材料")
    factor = spec.get("factor", 1)
    if not isinstance(factor, (float, int)) or not np.isfinite(factor):
        raise HTTPException(422, "单位换算系数无效")


def approved():
    return [r for r in store.records("public", "formula") if r.get("status") == "approved"]


def calculate(frame, formulas):
    result = frame.copy()
    for spec in formulas:
        a, b = spec["inputs"]
        if a not in frame or b not in frame:
            continue
        value = frame[a]*frame[b] if spec["operation"] == "product" else frame[a]/frame[b].replace(0, np.nan)
        result["knowledge_"+spec["id"]] = (value*spec.get("factor", 1)).where(frame.material.isin(spec["materials"])).replace([np.inf, -np.inf], np.nan)
    return result
