import httpx
import respx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@respx.mock
def test_health_check_base_status():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "ollama" in response.json()
    assert "model" in response.json()
    assert "model_available" in response.json()
    assert "fallback_used" in response.json()

