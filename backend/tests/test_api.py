from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_reports_data_availability():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert isinstance(response.json()["dataReady"], bool)


def test_variable_catalogue_and_api_branding():
    response = client.get("/api/v1/aurora/variables")
    assert response.status_code == 200
    assert len(response.json()["features"]) == 10
    assert "light_pollution" not in response.json()["features"]
    assert "latitude" not in response.json()["features"]
    assert response.json()["locations"] == ["Tromsø", "Reykjavík"]
    assert app.title == "AuroraTime"
