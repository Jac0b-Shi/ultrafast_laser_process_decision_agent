from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
import pandas as pd


DEFAULT_SCORE_WEIGHTS = {
    "uncertainty": 0.20,
    "domain_distance": 0.20,
    "missing": 0.05,
}


def _finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def score_from_loss(loss: float) -> float:
    return 1.0 / (1.0 + max(float(loss), 0.0))


def robust_scale(frame: pd.DataFrame, column: str) -> float:
    if column not in frame:
        return 1.0
    values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return 1.0
    if len(values) >= 2:
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = float(q3 - q1)
        if iqr > 1e-12:
            return iqr
        std = float(values.std())
        if math.isfinite(std) and std > 1e-12:
            return std
    median = abs(float(values.median()))
    return median if median > 1e-12 else 1.0


def _legacy_scale(frame: pd.DataFrame, column: str) -> float:
    if column not in frame:
        return 1.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if len(values) < 2:
        return 1.0
    std = float(values.std())
    return std if std > 0 else max(abs(float(values.mean())), 1.0)


def _request_value(request: Any, field: str) -> float | None:
    value = getattr(request, field, None)
    return float(value) if _finite(value) else None


def requested_quality_columns(request: Any) -> list[str]:
    columns: list[str] = []
    if _request_value(request, "target_depth_um") is not None:
        columns.append("depth_um")
    if _request_value(request, "target_diameter_um") is not None:
        columns.append("diameter_um")
    if _request_value(request, "max_roughness_um") is not None:
        columns.append("roughness_um")
    if _request_value(request, "target_min_depth_um") is not None:
        columns.append("min_depth_um")
    if _request_value(request, "target_max_depth_um") is not None:
        columns.append("max_depth_um")
    if _request_value(request, "max_sq_um") is not None:
        columns.append("sq_um")
    if _request_value(request, "max_sz_um") is not None:
        columns.append("sz_um")
    return columns


def legacy_quality_loss(quality: dict[str, float], frame: pd.DataFrame, request: Any) -> float:
    loss = 0.0
    terms = 0
    for column, request_field in (
        ("depth_um", "target_depth_um"),
        ("diameter_um", "target_diameter_um"),
        ("min_depth_um", "target_min_depth_um"),
        ("max_depth_um", "target_max_depth_um"),
    ):
        target = _request_value(request, request_field)
        if target is None:
            continue
        terms += 1
        value = quality.get(column)
        if not _finite(value):
            loss += 2.0
        else:
            loss += abs(float(value) - target) / _legacy_scale(frame, column)

    for column, request_field in (
        ("roughness_um", "max_roughness_um"),
        ("sq_um", "max_sq_um"),
        ("sz_um", "max_sz_um"),
    ):
        roughness_limit = _request_value(request, request_field)
        if roughness_limit is None:
            continue
        terms += 1
        value = quality.get(column)
        if not _finite(value):
            loss += 1.5
        elif float(value) <= roughness_limit:
            loss += 0.2 * (float(value) / max(roughness_limit, 1e-9))
        else:
            loss += 1.0 + (float(value) - roughness_limit) / max(roughness_limit, 1e-9)

    if terms == 0:
        roughness = quality.get("roughness_um")
        depth = quality.get("depth_um")
        loss += float(roughness) if _finite(roughness) else 1.0
        loss -= 0.05 * float(depth) if _finite(depth) else 0.0

    missing_quality = sum(1 for column in requested_quality_columns(request) if not _finite(quality.get(column)))
    return max(loss + DEFAULT_SCORE_WEIGHTS["missing"] * missing_quality, 0.0)


def constraint_loss(
    quality: dict[str, float],
    frame: pd.DataFrame,
    request: Any,
    scales: dict[str, float] | None = None,
) -> tuple[float, int, dict[str, float]]:
    loss = 0.0
    missing = 0
    components: dict[str, float] = {}
    for column, request_field in (
        ("depth_um", "target_depth_um"),
        ("diameter_um", "target_diameter_um"),
        ("min_depth_um", "target_min_depth_um"),
        ("max_depth_um", "target_max_depth_um"),
    ):
        target = _request_value(request, request_field)
        if target is None:
            continue
        value = quality.get(column)
        if not _finite(value):
            missing += 1
            components[column] = 0.0
            continue
        scale = (scales or {}).get(column) or robust_scale(frame, column)
        component = abs(float(value) - target) / scale
        components[column] = component
        loss += component

    for column, request_field in (
        ("roughness_um", "max_roughness_um"),
        ("sq_um", "max_sq_um"),
        ("sz_um", "max_sz_um"),
    ):
        roughness_limit = _request_value(request, request_field)
        if roughness_limit is None:
            continue
        value = quality.get(column)
        if not _finite(value):
            missing += 1
            components[column] = 0.0
        else:
            scale = (scales or {}).get(column) or robust_scale(frame, column)
            component = max(0.0, (float(value) - roughness_limit) / scale)
            components[column] = component
            loss += component

    return loss, missing, components


def normalized_uncertainty(
    uncertainty: dict[str, float] | None,
    frame: pd.DataFrame,
    request: Any,
    scales: dict[str, float] | None = None,
) -> float:
    if not uncertainty:
        return 0.0
    values = []
    for column in requested_quality_columns(request):
        value = uncertainty.get(column)
        if _finite(value):
            scale = (scales or {}).get(column) or robust_scale(frame, column)
            values.append(float(value) / scale)
    return float(np.mean(values)) if values else 0.0


def parameter_domain_distance(
    parameters: dict[str, float] | None,
    train_frame: pd.DataFrame,
    parameter_columns: Iterable[str],
) -> float:
    if not parameters or train_frame.empty:
        return 0.0
    columns = [
        column
        for column in parameter_columns
        if column in train_frame and _finite(parameters.get(column)) and train_frame[column].notna().any()
    ]
    if not columns:
        return 0.0
    reference = train_frame[columns].apply(pd.to_numeric, errors="coerce")
    medians = reference.median()
    scales = pd.Series({column: robust_scale(reference, column) for column in columns})
    reference = reference.fillna(medians)
    candidate = pd.Series({column: float(parameters[column]) for column in columns})
    distances = np.sqrt((((reference - candidate) / scales) ** 2).mean(axis=1))
    finite = distances.replace([np.inf, -np.inf], np.nan).dropna()
    return float(finite.min()) if not finite.empty else 0.0


def score_quality(
    quality: dict[str, float],
    frame: pd.DataFrame,
    request: Any,
    *,
    variant: str = "full_score",
    uncertainty: dict[str, float] | None = None,
    parameters: dict[str, float] | None = None,
    parameter_columns: Iterable[str] = (),
    weights: dict[str, float] | None = None,
    scales: dict[str, float] | None = None,
    domain_distance_override: float | None = None,
) -> dict[str, Any]:
    configured = {**DEFAULT_SCORE_WEIGHTS, **(weights or {})}
    legacy_loss = legacy_quality_loss(quality, frame, request)
    base_loss, missing, components = constraint_loss(quality, frame, request, scales)
    if not requested_quality_columns(request):
        base_loss = legacy_loss
        components = {"default_preference": legacy_loss}
    uncertainty_loss = (
        normalized_uncertainty(uncertainty, frame, request, scales)
        if variant in {"constraint_uncertainty", "full_score"}
        else 0.0
    )
    domain_distance = (
        (
            float(domain_distance_override)
            if domain_distance_override is not None
            else parameter_domain_distance(parameters, frame, parameter_columns)
        )
        if variant == "full_score"
        else 0.0
    )

    if variant == "legacy":
        total_loss = legacy_loss
    elif variant == "constraint_only":
        total_loss = base_loss + configured["missing"] * missing
    elif variant == "constraint_uncertainty":
        total_loss = (
            base_loss
            + configured["uncertainty"] * uncertainty_loss
            + configured["missing"] * missing
        )
    elif variant == "full_score":
        total_loss = (
            base_loss
            + configured["uncertainty"] * uncertainty_loss
            + configured["domain_distance"] * domain_distance
            + configured["missing"] * missing
        )
    else:
        raise ValueError(f"Unknown scoring variant: {variant}")

    return {
        "variant": variant,
        "score": score_from_loss(total_loss),
        "total_loss": float(total_loss),
        "constraint_loss": float(base_loss),
        "legacy_loss": float(legacy_loss),
        "uncertainty_loss": float(uncertainty_loss),
        "domain_distance": float(domain_distance),
        "missing_targets": int(missing),
        "constraint_components": components,
    }
