import pytest
from app.services.agent_decision import candidate_loss

TARGETS = {"depth_um": {"value": 10, "tolerance": 1, "operator": "eq"}}

def test_distance_cannot_displace_better_target_match():
    far = candidate_loss({"depth_um": 10.01}, TARGETS, 1)
    near = candidate_loss({"depth_um": 10.1}, TARGETS, 0)
    assert far < near
    assert far + .2 > near  # This fixture distinguishes the former soft weight.

@pytest.mark.parametrize("distance", [1.000001, float("nan"), float("inf"), -1])
def test_support_gate(distance):
    assert candidate_loss({"depth_um": 10}, TARGETS, distance) is None

def test_all_targets_must_fit_and_boundary_is_inclusive():
    assert candidate_loss({"depth_um": 11}, TARGETS, 1) == 1
    assert candidate_loss({"depth_um": 11.1}, TARGETS, 0) is None
    targets = {**TARGETS, "roughness_um": {"value": 1, "tolerance": .1, "operator": "le"}}
    assert candidate_loss({"depth_um": 10}, targets, 0) is None
    assert candidate_loss({"depth_um": 10, "roughness_um": 1.2}, targets, 0) is None
    assert candidate_loss({"depth_um": 10, "roughness_um": .5}, targets, 0) == 0
