from __future__ import annotations

import pandas as pd

from app.schemas import RecommendationRequest
from app.services.scoring import parameter_domain_distance, score_quality


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth_um": [10.0, 20.0, 30.0, 40.0],
            "diameter_um": [100.0, 200.0, 300.0, 400.0],
            "roughness_um": [1.0, 2.0, 3.0, 4.0],
            "scan_speed_mm_s": [100.0, 200.0, 300.0, 400.0],
            "pulse_width_fs": [200.0, 300.0, 400.0, 500.0],
        }
    )


def test_constraint_score_is_monotonic_for_equality_target() -> None:
    frame = _frame()
    request = RecommendationRequest(target_depth_um=20.0)
    exact = score_quality({"depth_um": 20.0}, frame, request, variant="constraint_only")
    far = score_quality({"depth_um": 35.0}, frame, request, variant="constraint_only")
    assert exact["score"] == 1.0
    assert far["score"] < exact["score"]


def test_roughness_uses_one_sided_constraint() -> None:
    frame = _frame()
    request = RecommendationRequest(max_roughness_um=2.5)
    feasible = score_quality({"roughness_um": 2.0}, frame, request, variant="constraint_only")
    violated = score_quality({"roughness_um": 4.0}, frame, request, variant="constraint_only")
    assert feasible["constraint_loss"] == 0.0
    assert violated["constraint_loss"] > 0.0
    assert feasible["score"] > violated["score"]


def test_uncertainty_and_domain_distance_reduce_policy_score() -> None:
    frame = _frame()
    request = RecommendationRequest(target_depth_um=20.0)
    constraint = score_quality({"depth_um": 20.0}, frame, request, variant="constraint_only")
    uncertain = score_quality(
        {"depth_um": 20.0},
        frame,
        request,
        variant="constraint_uncertainty",
        uncertainty={"depth_um": 10.0},
    )
    full = score_quality(
        {"depth_um": 20.0},
        frame,
        request,
        variant="full_score",
        uncertainty={"depth_um": 10.0},
        domain_distance_override=2.0,
    )
    assert constraint["score"] > uncertain["score"] > full["score"]


def test_domain_distance_and_missing_target_are_auditable() -> None:
    frame = _frame()
    near = parameter_domain_distance(
        {"scan_speed_mm_s": 200.0, "pulse_width_fs": 300.0},
        frame,
        ["scan_speed_mm_s", "pulse_width_fs"],
    )
    far = parameter_domain_distance(
        {"scan_speed_mm_s": 900.0, "pulse_width_fs": 1200.0},
        frame,
        ["scan_speed_mm_s", "pulse_width_fs"],
    )
    missing = score_quality(
        {},
        frame,
        RecommendationRequest(target_depth_um=20.0),
        variant="constraint_only",
    )
    assert near == 0.0
    assert far > near
    assert missing["missing_targets"] == 1
    assert 0.0 < missing["score"] < 1.0


def test_no_target_request_preserves_default_quality_preference() -> None:
    frame = _frame()
    request = RecommendationRequest()
    preferred = score_quality(
        {"depth_um": 35.0, "roughness_um": 1.0},
        frame,
        request,
        variant="full_score",
        domain_distance_override=0.0,
    )
    weaker = score_quality(
        {"depth_um": 10.0, "roughness_um": 4.0},
        frame,
        request,
        variant="full_score",
        domain_distance_override=0.0,
    )
    assert preferred["score"] > weaker["score"]
    assert "default_preference" in preferred["constraint_components"]
