from fastapi import APIRouter

from app.schemas import ExperimentFeedback, FeedbackReceipt
from app.services.feedback import append_feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackReceipt)
def create_feedback(feedback: ExperimentFeedback) -> FeedbackReceipt:
    return append_feedback(feedback)
