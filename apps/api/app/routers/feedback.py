from fastapi import APIRouter, HTTPException

from app.schemas import ExperimentFeedback, FeedbackReceipt
from app.services.feedback import append_feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackReceipt)
def create_feedback(feedback: ExperimentFeedback) -> FeedbackReceipt:
    if feedback.candidate_source != "historical" or feedback.execution_eligibility != "reviewable":
        raise HTTPException(
            status_code=409,
            detail="仅 historical / reviewable 候选可以写入实验反馈。生成候选仅用于诊断。",
        )
    return append_feedback(feedback)
