from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_base_status():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "llm_status" in response.json()
    assert "llm_message" in response.json()

