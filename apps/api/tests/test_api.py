from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dataset_summary() -> None:
    response = client.get("/api/datasets/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_samples"] > 0
    assert payload["raw_files"]
    materials = {item["material"]: item for item in payload["materials"]}
    assert {"AlSiC", "CFRP", "SiC", "ZrO2"}.issubset(materials)
    assert materials["CFRP"]["sample_count"] == 128
    assert {"sq_um", "sz_um", "min_depth_um", "max_depth_um"}.issubset(materials["AlSiC"]["quality_metrics"])


def test_csv_material_extended_quality_request() -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "material": "ZrO2",
            "target_depth_um": 14,
            "target_min_depth_um": 10,
            "target_max_depth_um": 18,
            "max_roughness_um": 2,
            "max_sq_um": 3,
            "max_sz_um": 15,
            "top_k": 1,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert payload["recommendations"][0]["similar_cases"][0]["material"] == "ZrO2"


def test_csv_data_management_retains_negative_depth_as_audit_only() -> None:
    response = client.get("/api/data-management/experiments/AlSiC")
    assert response.status_code == 200
    records = response.json()["records"]
    flagged = [record for record in records if record["quality_flags"]]
    assert flagged
    assert any(record["depth_um"] < 0 for record in flagged)
    assert all(record["data_source"] == "system" for record in records)


def test_model_info() -> None:
    response = client.get("/api/recommendations/model-info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "range_guarded_random_forest_regressor"
    assert "RandomForestRegressor" in payload["model_type"]
    assert "材料定制中间量" in payload["model_type"]


def test_recommendations() -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "material": "高温合金",
            "target_depth_um": 40,
            "target_diameter_um": 500,
            "max_roughness_um": 8.5,
            "top_k": 2,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert payload["candidate_size"] > 0
    assert payload["model_info"]["model_name"] == "range_guarded_random_forest_regressor"
    assert payload["recommendations"][0]["generation_method"] == "ml_regression_fit"
    assert payload["recommendations"][0]["candidate_source"] in {"historical", "perturbed"}
    expected_eligibility = (
        "reviewable" if payload["recommendations"][0]["candidate_source"] == "historical" else "diagnostic_only"
    )
    assert payload["recommendations"][0]["execution_eligibility"] == expected_eligibility
    assert payload["recommendations"][0]["model_name"] == "range_guarded_random_forest_regressor"
    assert payload["recommendations"][0]["rank"] == 0
    assert payload["recommendations"][0]["intermediate_metrics"]
    assert payload["recommendations"][0]["material_explanation"]
    assert payload["recommendations"][0]["similar_cases"]
    assert payload["recommendations"][0]["similar_cases"][0]["intermediate_metrics"]
    assert payload["recommendations"][1]["generation_method"] == "historical_similarity"
    assert payload["recommendations"][1]["candidate_source"] == "historical"
    assert payload["recommendations"][1]["execution_eligibility"] == "reviewable"
    assert payload["recommendations"][1]["rank"] == 1
    assert len(payload["recommendations"]) == 3


def test_feedback_rejects_generated_candidate_direct_api_bypass() -> None:
    response = client.post(
        "/api/feedback",
        json={
            "task": {"material": "BF33", "top_k": 1, "constraints": {}},
            "candidate_source": "perturbed",
            "execution_eligibility": "diagnostic_only",
            "selected_parameters": {"repetition_frequency_khz": 20.0},
            "measured_quality": {"depth_um": 10.0},
        },
    )
    assert response.status_code == 409
    assert "仅用于诊断" in response.json()["detail"]


def _assert_material_metrics(material: str, expected_metrics: set[str]) -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "material": material,
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    first = payload["recommendations"][0]
    assert expected_metrics.issubset(set(first["intermediate_metrics"]))
    assert first["material_explanation"]
    assert first["similar_cases"]
    assert expected_metrics.intersection(set(first["similar_cases"][0]["intermediate_metrics"]))


def test_material_intermediate_metrics_bf33() -> None:
    _assert_material_metrics("BF33", {"line_pulse_density_pulses_mm", "pulse_spacing_um"})


def test_material_intermediate_metrics_sic() -> None:
    _assert_material_metrics(
        "4H碳化硅",
        {"line_pulse_density_pulses_mm", "pulse_spacing_um", "threshold_relative_density"},
    )


def test_material_intermediate_metrics_diamond() -> None:
    _assert_material_metrics("金刚石", {"cumulative_pulse_density", "dose_index"})


def test_material_intermediate_metrics_microcrystalline_glass() -> None:
    _assert_material_metrics("微晶玻璃", {"pulse_time_interaction"})


def test_material_intermediate_metrics_superalloy() -> None:
    _assert_material_metrics("高温合金", {"duty_cycle", "power_chain_proxy_w", "marking_energy_proxy"})


def test_recommendations_reject_obvious_out_of_range_target() -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "material": "4H碳化硅",
            "target_depth_um": 40,
            "max_roughness_um": 0.5,
            "top_k": 3,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert "拒绝外推拟合" in payload["detail"]["message"]
    assert payload["detail"]["violations"][0]["field"] == "target_depth_um"


def test_recommendations_reject_missing_target_observations() -> None:
    response = client.post(
        "/api/recommendations",
        json={
            "material": "4H碳化硅",
            "target_diameter_um": 10,
            "top_k": 3,
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"]["violations"][0]["reason"] == "insufficient_observations"
