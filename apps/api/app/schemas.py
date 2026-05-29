from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MaterialSummary(BaseModel):
    material: str
    sample_count: int
    source_files: list[str]
    parameter_columns: list[str]
    quality_metrics: list[str]


class DatasetSummary(BaseModel):
    total_samples: int
    materials: list[MaterialSummary]
    raw_files: list[str]
    feedback_samples: int


class RecommendationRequest(BaseModel):
    material: str | None = Field(default=None, description="材料名称")
    target_depth_um: float | None = None
    target_diameter_um: float | None = None
    max_roughness_um: float | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    top_k: int = Field(default=3, ge=1, le=10)


class CaseMatch(BaseModel):
    case_id: str
    material: str
    source_file: str
    source_row: int | None = None
    parameters: dict[str, float]
    intermediate_metrics: dict[str, float]
    quality: dict[str, float]
    score: float


class ModelInfo(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    training_scope: str
    feature_columns: list[str]
    target_columns: list[str]
    extrapolation_policy: str


class ParameterRecommendation(BaseModel):
    rank: int
    generation_method: str
    model_name: str | None = None
    parameters: dict[str, float]
    intermediate_metrics: dict[str, float]
    predicted_quality: dict[str, float]
    uncertainty: dict[str, float]
    score: float
    rationale: str
    material_explanation: str
    similar_cases: list[CaseMatch]


class RecommendationResponse(BaseModel):
    dataset_size: int
    candidate_size: int
    model_info: ModelInfo
    recommendations: list[ParameterRecommendation]
    notes: list[str]


class ExperimentFeedback(BaseModel):
    task: RecommendationRequest
    selected_parameters: dict[str, float]
    measured_quality: dict[str, float]
    operator: str | None = None
    notes: str | None = None


class FeedbackReceipt(BaseModel):
    feedback_id: str
    created_at: datetime
    stored_jsonl: str
    stored_sqlite: str


# 数据管理相关模型
class ExperimentData(BaseModel):
    case_id: str | None = None
    material: str
    pulse_width_fs: float | None = None
    repetition_frequency_khz: float | None = None
    scan_speed_mm_s: float | None = None
    pulse_energy_mj: float | None = None
    laser_energy_percent: float | None = None
    defocus_amount_mm: float | None = None
    marking_count: float | None = None
    fill_spacing_um: float | None = None
    scan_interval_um: float | None = None
    processing_time_s: float | None = None
    average_power_w: float | None = None
    peak_power_kw: float | None = None
    depth_um: float | None = None
    diameter_um: float | None = None
    roughness_um: float | None = None
    is_active: bool = True
    data_source: str = "user"
    note: str | None = None


class MaterialInfo(BaseModel):
    material: str
    display_name: str | None = None
    description: str | None = None


class MaterialListResponse(BaseModel):
    materials: list[str]


class ExperimentDataListResponse(BaseModel):
    records: list[ExperimentData]
