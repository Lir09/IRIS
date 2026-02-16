import pytest
import httpx
import respx
import json
from app.llm.client import OllamaClient, OllamaConnectionError
from app.models.schemas import Intent
from app.api.health import LLMHealthResponse
from app.main import app
from fastapi.testclient import TestClient

test_client = TestClient(app)

@pytest.fixture
def ollama_client_fixture():
    # Ensure client uses mocked httpx.Client
    client = OllamaClient()
    client.client = httpx.Client(base_url=client.base_url, timeout=client.timeout)
    return client

@respx.mock
def test_ollama_client_chat_success(ollama_client_fixture):
    mock_response_content = {
        "model": "llama3.1:8b-instruct",
        "created_at": "2024-07-20T10:00:00Z",
        "message": {"role": "assistant", "content": "Hello, how can I help you?"},
        "done": True
    }
    respx.post("http://localhost:11434/api/chat").mock(return_value=httpx.Response(200, json=mock_response_content))

    messages = [{"role": "user", "content": "Hi"}]
    response = ollama_client_fixture.chat(messages)
    assert response == "Hello, how can I help you?"

@respx.mock
def test_ollama_client_chat_connection_error(ollama_client_fixture):
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))

    messages = [{"role": "user", "content": "Hi"}]
    with pytest.raises(OllamaConnectionError, match="Could not connect to Ollama server"):
        ollama_client_fixture.chat(messages)

@respx.mock
def test_ollama_client_chat_timeout_error(ollama_client_fixture):
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.TimeoutException("Timeout"))

    messages = [{"role": "user", "content": "Hi"}]
    with pytest.raises(OllamaConnectionError, match="Ollama request timed out"):
        ollama_client_fixture.chat(messages)

@respx.mock
def test_ollama_client_check_status_ok(ollama_client_fixture):
    respx.get("http://localhost:11434/api/tags").mock(return_value=httpx.Response(200, json={"models": [{"name": "llama3.1:8b-instruct"}]}))
    
    status_info = ollama_client_fixture.check_ollama_status()
    assert status_info["status"] == "ok"
    assert "running and model 'llama3.1:8b-instruct' is available" in status_info["message"]

@respx.mock
def test_ollama_client_check_status_model_not_found(ollama_client_fixture):
    respx.get("http://localhost:11434/api/tags").mock(return_value=httpx.Response(200, json={"models": [{"name": "other-model:latest"}]}))

    status_info = ollama_client_fixture.check_ollama_status()
    assert status_info["status"] == "warning"
    assert "model 'llama3.1:8b-instruct' is not available" in status_info["message"]

@respx.mock
def test_ollama_client_check_status_connection_error(ollama_client_fixture):
    respx.get("http://localhost:11434/api/tags").mock(side_effect=httpx.ConnectError("Connection refused"))

    status_info = ollama_client_fixture.check_ollama_status()
    assert status_info["status"] == "error"
    assert "Could not connect to Ollama server" in status_info["message"]


@respx.mock
def test_health_endpoint_llm_ok():
    respx.get("http://localhost:11434/api/tags").mock(return_value=httpx.Response(200, json={"models": [{"name": "llama3.1:8b-instruct"}]}))
    
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["llm_status"] == "ok"
    assert "running and model 'llama3.1:8b-instruct' is available" in response.json()["llm_message"]

@respx.mock
def test_health_endpoint_llm_unavailable():
    respx.get("http://localhost:11434/api/tags").mock(side_effect=httpx.ConnectError("Connection refused"))
    
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok" # Main app is still OK
    assert response.json()["llm_status"] == "error"
    assert "Could not connect to Ollama server" in response.json()["llm_message"]


@respx.mock
def test_chat_fallback_on_ollama_error():
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))

    chat_payload = {"message": "Run git status", "cwd": "."}
    response = test_client.post("/chat", json=chat_payload)
    
    assert response.status_code == 200
    chat_response = response.json()
    assert chat_response["intent"] == Intent.CHAT # Fallback intent
    assert chat_response["requires_approval"] is False
    assert "cannot connect to the local LLM" in chat_response["response"]
    assert "Failed to connect to LLM." in chat_response["plan"]

