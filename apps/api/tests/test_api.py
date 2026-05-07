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


def test_model_info() -> None:
    response = client.get("/api/recommendations/model-info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "range_guarded_similarity_retriever"
    assert "不训练回归模型" in payload["training_scope"]


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
    assert payload["model_info"]["model_name"] == "range_guarded_similarity_retriever"


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
