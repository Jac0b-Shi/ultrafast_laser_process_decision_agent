"""Validated conversation tools for the machining assistant.

The language model may explain a turn, but it never receives authority to make
up process values or invoke arbitrary code.  This module is the only registry
used by the conversational endpoint.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from app.services.agent_decision import decide, dataset, validate_task
from app.services.agent_knowledge import orchestrate, search
from app.services.agent_models import groups
from app.services.data_loader import PARAMETER_COLUMNS

MAX_TOOL_CALLS = 6
TOOL_NAMES = {"材料与数据概况", "填写加工目标", "查询相似案例", "检索知识", "生成参数推荐"}
_METRICS = {
    "深度": "depth_um", "直径": "diameter_um", "粗糙度": "roughness_um",
    "最小深度": "min_depth_um", "最大深度": "max_depth_um", "sq": "sq_um", "sz": "sz_um",
}


def _event(tool: str, summary: str, data: dict[str, Any] | None = None):
    return {"tool": tool, "summary": summary, "data": data or {}}


def _task_from_text(message: str, current: dict[str, Any], frame) -> dict[str, Any]:
    task = {**current, "targets": dict(current.get("targets") or {})}
    lower = message.lower()
    for material in frame.material.dropna().unique():
        if str(material).lower() in lower:
            task["material"] = str(material)
            break
    # Only use explicit values and units. A tolerance applies to the named
    # target, or to the only existing target when the user says "改成容差".
    for label, key in _METRICS.items():
        found = re.search(rf"{re.escape(label)}[^0-9]{{0,12}}(\d+(?:\.\d+)?)\s*(?:μm|um)", lower)
        if found:
            task["targets"][key] = {"value": float(found.group(1)), "operator": "eq", "unit": "um"}
            tolerance = re.search(r"(?:容差|误差)[^0-9]{0,8}(\d+(?:\.\d+)?)\s*(?:μm|um)", lower)
            if tolerance:
                task["targets"][key]["tolerance"] = float(tolerance.group(1))
    tolerance = re.search(r"(?:容差|误差)[^0-9]{0,8}(\d+(?:\.\d+)?)\s*(?:μm|um)", lower)
    if tolerance and len(task["targets"]) == 1:
        only = next(iter(task["targets"].values()))
        only["tolerance"] = float(tolerance.group(1))
    task.setdefault("algorithm", "auto")
    task.setdefault("constraints", {})
    return task


def _missing(task: dict[str, Any]) -> str | None:
    if not task.get("material"):
        return "请补充加工材料。"
    targets = task.get("targets") or {}
    if not targets:
        return "请说明质量指标、目标值和单位，例如“深度 15 μm，容差 1 μm”。"
    for target in targets.values():
        if not isinstance(target, dict) or "value" not in target or "tolerance" not in target:
            return "还需要每个质量指标的容差；我不会擅自补充。"
    return None


def run_turn(owner: str, message: str, current_task: dict[str, Any], model_id: str | None,
             request_key: str | None, images: list[dict[str, Any]], frame) -> dict[str, Any]:
    """Run at most one pass through the fixed registry and return a safe transcript."""
    if not message.strip() and not images:
        raise HTTPException(422, "请输入问题、加工需求或图片")
    events: list[dict[str, Any]] = [_event("材料与数据概况", f"当前可用 {len(frame)} 条实测记录、{frame.material.nunique()} 类材料")]
    task = _task_from_text(message, current_task, frame)
    if task != current_task:
        events.append(_event("填写加工目标", "已从本轮明确描述中更新目标草稿", {"task": task}))
    recommendation_words = ("推荐", "参数", "加工", "生成一组", "怎么设")
    wants_recommendation = bool(task.get("targets")) and any(word in message for word in recommendation_words)
    recommendation = None
    if wants_recommendation:
        missing = _missing(task)
        if missing:
            return {"reply": missing, "task": task, "events": events, "recommendation": None}
        validate_task(task, frame)
        applicable = frame.loc[frame.material == task["material"]]
        events.append(_event("查询相似案例", f"找到 {len(applicable)} 条同材料实测记录", {"material": task["material"], "count": len(applicable)}))
        citations = search(owner, message + " " + str(task["material"]))
        if citations:
            events.append(_event("检索知识", f"找到 {len(citations)} 条相关知识片段", {"sources": [c["file"] for c in citations]}))
        result = decide(owner, task, history_only=True)
        provider = {"status": "disabled", "message": "历史优先／本地确定性推荐", "candidates": []}
        if result is None:
            context = {**task, "data_conditions": {"samples": len(applicable), "parameter_groups": len(set(groups(applicable))), "recorded_parameters": [c for c in PARAMETER_COLUMNS if applicable[c].notna().any()]}}
            provider = orchestrate(message, context, citations, owner=owner, request_key=request_key, model_id=model_id, images=images)
            if "operation_result" in provider:
                return provider["operation_result"]
            result = decide(owner, task, provider.get("candidates"))
        result.update({"citations": citations, "provider": provider})
        recommendation = result
        events.append(_event("生成参数推荐", "已按历史案例与确定性模型生成一组参数", {"source": result["source"], "similar_cases": len(result["similar_cases"])}))
        reply = f"已生成 {task['material']} 的一组参数。结果附有 {len(result['similar_cases'])} 条同材料实测案例，可在下方展开查看依据。"
        return {"reply": reply, "task": task, "events": events, "recommendation": recommendation, "call_id": provider.get("call_id")}
    citations = search(owner, message)
    if citations:
        events.append(_event("检索知识", f"找到 {len(citations)} 条相关知识片段", {"sources": [c["file"] for c in citations]}))
    # A provider is used for ordinary conversation when configured. The local
    # fallback deliberately explains its limitation instead of pretending to answer.
    response = orchestrate(message, {"task": task, "materials": sorted(str(x) for x in frame.material.dropna().unique())}, citations,
                           purpose="chat", owner=owner, request_key=request_key, model_id=model_id, images=images)
    if "operation_result" in response:
        return response["operation_result"]
    reply = response.get("reply") or "当前为本地确定性模式，只能根据已记录的数据推荐参数；请选择已启用的 AI 模型进行通用问答。"
    return {"reply": reply, "task": task, "events": events, "recommendation": None, "call_id": response.get("call_id")}
