from fastapi import APIRouter

from app.schemas import RecommendationRequest, RecommendationResponse
from app.services.recommender import recommend_parameters

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    return recommend_parameters(request)
