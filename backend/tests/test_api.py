from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_simulation_contract():
    response = client.post("/api/v1/simulations", json={"presetId": "balanced-portfolio", "runs": 100, "seed": 12})
    assert response.status_code == 200
    assert response.json()["seed"] == 12

def test_rejects_unsafe_run_count():
    response = client.post("/api/v1/simulations", json={"presetId": "balanced-portfolio", "runs": 10})
    assert response.status_code == 422
