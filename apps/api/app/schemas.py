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
    algorithm: str = Field(default="random_forest")


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
    algorithm: str | None = None
    parameters: dict[str, float]
    intermediate_metrics: dict[str, float]
    predicted_quality: dict[str, float]
    uncertainty: dict[str, float]
    score: float
    rationale: str
    material_explanation: str
    similar_cases: list[CaseMatch]
    feature_importance: dict[str, float] | None = None
    error_metrics: dict[str, Any] | None = None
    training_info: dict[str, Any] | None = None


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
    pulse_width_fs: float | None = Field(default=None, ge=0, le=10000)
    repetition_frequency_khz: float | None = Field(default=None, ge=0, le=100000)
    scan_speed_mm_s: float | None = Field(default=None, ge=0, le=100000)
    pulse_energy_mj: float | None = Field(default=None, ge=0, le=1000)
    laser_energy_percent: float | None = Field(default=None, ge=0, le=100)
    defocus_amount_mm: float | None = Field(default=None, ge=-100, le=100)
    marking_count: float | None = Field(default=None, ge=0, le=1000)
    fill_spacing_um: float | None = Field(default=None, ge=0, le=10000)
    scan_interval_um: float | None = Field(default=None, ge=0, le=100000)
    processing_time_s: float | None = Field(default=None, ge=0, le=360000)
    average_power_w: float | None = Field(default=None, ge=0, le=100000)
    peak_power_kw: float | None = Field(default=None, ge=0, le=1000000)
    depth_um: float | None = Field(default=None, ge=0, le=100000)
    diameter_um: float | None = Field(default=None, ge=0, le=100000)
    roughness_um: float | None = Field(default=None, ge=0, le=1000)
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
