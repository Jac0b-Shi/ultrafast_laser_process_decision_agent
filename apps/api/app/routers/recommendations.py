from fastapi import APIRouter, HTTPException, Depends
from app.services.agent_store import current_user
from app.services.agent_decision import decide, dataset
from app.services.agent_store import append

from app.schemas import ModelInfo, RecommendationRequest, RecommendationResponse
from app.services.recommender import MODEL_INFO

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])
AGENT_MODEL_INFO = MODEL_INFO.model_copy(update={"model_name": "knowledge_guided_grouped_selection", "model_version": "1.0.0", "model_type": "机理中间量 + 14 类算法注册表 + 分组验证选模 + 历史优先单组推荐", "training_scope": "公共原始数据与当前用户有效反馈；训练折内计算中间量和预处理。", "extrapolation_policy": "不跨材料回退，不忽略约束；无合格历史时要求设备步长与数据支持。"})


@router.post("")
def create_recommendation(request: RecommendationRequest, user=Depends(current_user)):
    mapping = {"target_depth_um": ("depth_um", "eq"), "target_diameter_um": ("diameter_um", "eq"), "max_roughness_um": ("roughness_um", "le"), "target_min_depth_um": ("min_depth_um", "ge"), "target_max_depth_um": ("max_depth_um", "le"), "max_sq_um": ("sq_um", "le"), "max_sz_um": ("sz_um", "le")}
    targets = {c: {"value": getattr(request, key), "operator": op, "unit": "um", "tolerance": 0} for key, (c, op) in mapping.items() if getattr(request, key) is not None}
    result = decide(user["id"], {"material": request.material, "targets": targets, "constraints": request.constraints, "algorithm": request.algorithm})
    result["id"] = append(user["id"], "recommendation", result)
    return {"model_info": AGENT_MODEL_INFO, "dataset_size": len(dataset(user["id"])), "candidate_size": 1, "recommendations": [{**result, "rank": 1, "generation_method": result["source"], "candidate_source": result["source"], "execution_eligibility": "reviewable", "predicted_quality": result["quality"], "uncertainty": result["confidence"].get("validation_rmse", {}), "score": result["match_score"], "rationale": "历史优先，单组参数推荐", "material_explanation": request.material}], "notes": ["兼容接口使用零容差；显式容差请使用智能体接口。"]}


@router.get("/model-info", response_model=ModelInfo)
def get_model_info() -> ModelInfo:
    return AGENT_MODEL_INFO
