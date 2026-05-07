from __future__ import annotations

import math
from typing import Any

import pandas as pd

from app.schemas import CaseMatch, ParameterRecommendation, RecommendationRequest, RecommendationResponse
from app.services.data_loader import PARAMETER_COLUMNS, QUALITY_COLUMNS, load_dataset


def _finite(value: Any) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def _number_dict(row: pd.Series, columns: list[str]) -> dict[str, float]:
    output: dict[str, float] = {}
    for column in columns:
        value = row.get(column)
        if _finite(value):
            output[column] = float(value)
    return output


def _scale(frame: pd.DataFrame, column: str) -> float:
    values = frame[column].dropna()
    if len(values) < 2:
        return 1.0
    std = float(values.std())
    return std if std > 0 else max(abs(float(values.mean())), 1.0)


def _apply_constraints(frame: pd.DataFrame, constraints: dict[str, Any]) -> pd.DataFrame:
    filtered = frame
    for column, rule in constraints.items():
        if column not in PARAMETER_COLUMNS or column not in filtered:
            continue
        if isinstance(rule, dict):
            minimum = rule.get("min", rule.get("gte"))
            maximum = rule.get("max", rule.get("lte"))
            if minimum is not None:
                filtered = filtered[filtered[column].notna() & (filtered[column] >= float(minimum))]
            if maximum is not None:
                filtered = filtered[filtered[column].notna() & (filtered[column] <= float(maximum))]
        elif rule is not None:
            filtered = filtered[filtered[column].notna() & (filtered[column] == float(rule))]
    return filtered


def _score_row(row: pd.Series, frame: pd.DataFrame, request: RecommendationRequest) -> float:
    score = 0.0
    terms = 0

    targets = [
        ("depth_um", request.target_depth_um),
        ("diameter_um", request.target_diameter_um),
    ]
    for column, target in targets:
        if target is None:
            continue
        terms += 1
        value = row.get(column)
        if not _finite(value):
            score += 2.0
            continue
        score += abs(float(value) - target) / _scale(frame, column)

    if request.max_roughness_um is not None:
        terms += 1
        value = row.get("roughness_um")
        if not _finite(value):
            score += 1.5
        elif float(value) <= request.max_roughness_um:
            score += 0.2 * (float(value) / max(request.max_roughness_um, 1e-9))
        else:
            score += 1.0 + (float(value) - request.max_roughness_um) / max(request.max_roughness_um, 1e-9)

    if terms == 0:
        roughness = row.get("roughness_um")
        depth = row.get("depth_um")
        score += float(roughness) if _finite(roughness) else 1.0
        score -= 0.05 * float(depth) if _finite(depth) else 0.0

    missing_quality = sum(1 for column in QUALITY_COLUMNS if not _finite(row.get(column)))
    return score + 0.05 * missing_quality


def _case_match(row: pd.Series, score: float) -> CaseMatch:
    return CaseMatch(
        case_id=str(row["case_id"]),
        material=str(row["material"]),
        source_file=str(row["source_file"]),
        source_row=int(row["source_row"]) if _finite(row.get("source_row")) else None,
        parameters=_number_dict(row, PARAMETER_COLUMNS),
        quality=_number_dict(row, QUALITY_COLUMNS),
        score=round(1.0 / (1.0 + max(score, 0.0)), 4),
    )


def _uncertainty(frame: pd.DataFrame) -> dict[str, float]:
    output: dict[str, float] = {}
    for column in QUALITY_COLUMNS:
        values = frame[column].dropna()
        if len(values) >= 2:
            output[column] = round(float(values.std()), 4)
    return output


def recommend_parameters(request: RecommendationRequest) -> RecommendationResponse:
    dataset = load_dataset()
    notes: list[str] = []
    if dataset.empty:
        return RecommendationResponse(dataset_size=0, candidate_size=0, recommendations=[], notes=["未找到原始数据。"])

    candidates = dataset
    if request.material:
        exact = candidates[candidates["material"] == request.material]
        if exact.empty:
            fuzzy = candidates[candidates["material"].str.contains(request.material, case=False, na=False)]
            candidates = fuzzy if not fuzzy.empty else candidates
            if fuzzy.empty:
                notes.append(f"未找到材料 {request.material} 的样本，已回退到全量数据。")
        else:
            candidates = exact

    constrained = _apply_constraints(candidates, request.constraints)
    if constrained.empty:
        notes.append("参数约束过滤后无样本，已忽略约束并使用材料候选集。")
    else:
        candidates = constrained

    scored_rows = [
        (index, _score_row(row, candidates, request))
        for index, row in candidates.iterrows()
    ]
    scored_rows.sort(key=lambda item: item[1])
    top = scored_rows[: request.top_k]
    similar_rows = scored_rows[: min(3, len(scored_rows))]
    similar_cases = [_case_match(candidates.loc[index], score) for index, score in similar_rows]
    uncertainty = _uncertainty(candidates)

    recommendations: list[ParameterRecommendation] = []
    for rank, (index, raw_score) in enumerate(top, start=1):
        row = candidates.loc[index]
        quality = _number_dict(row, QUALITY_COLUMNS)
        score = round(1.0 / (1.0 + max(raw_score, 0.0)), 4)
        rationale = (
            f"基于 {row['material']} 的历史案例 {row['case_id']}，"
            f"该参数组合在目标质量约束下的相似度得分为 {score}。"
        )
        recommendations.append(
            ParameterRecommendation(
                rank=rank,
                parameters=_number_dict(row, PARAMETER_COLUMNS),
                predicted_quality=quality,
                uncertainty=uncertainty,
                score=score,
                rationale=rationale,
                similar_cases=similar_cases,
            )
        )

    return RecommendationResponse(
        dataset_size=int(len(dataset)),
        candidate_size=int(len(candidates)),
        recommendations=recommendations,
        notes=notes,
    )
