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
