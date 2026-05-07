from fastapi import APIRouter

from app.schemas import DatasetSummary
from app.services.data_loader import dataset_summary

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/summary", response_model=DatasetSummary)
def get_dataset_summary() -> dict:
    return dataset_summary()
