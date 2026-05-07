from fastapi import APIRouter, HTTPException

from app.schemas import ModelInfo, RecommendationRequest, RecommendationResponse
from app.services.recommender import MODEL_INFO, OutOfRangeError, recommend_parameters

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    try:
        return recommend_parameters(request)
    except OutOfRangeError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": exc.message,
                "violations": exc.details,
            },
        ) from exc


@router.get("/model-info", response_model=ModelInfo)
def get_model_info() -> ModelInfo:
    return MODEL_INFO
