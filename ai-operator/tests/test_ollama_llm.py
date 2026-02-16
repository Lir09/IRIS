import pytest
import httpx
import respx
import json
from app.llm.client import OllamaClient, OllamaConnectionError, ollama_client
from app.models.schemas import Intent
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
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    ollama_client_fixture.refresh_detection()
    mock_response_content = {
        "model": "gpt-oss:20b",
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
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    ollama_client_fixture.refresh_detection()
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))

    messages = [{"role": "user", "content": "Hi"}]
    with pytest.raises(OllamaConnectionError, match="Could not connect to Ollama server"):
        ollama_client_fixture.chat(messages)

@respx.mock
def test_ollama_client_chat_timeout_error(ollama_client_fixture):
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    ollama_client_fixture.refresh_detection()
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.TimeoutException("Timeout"))

    messages = [{"role": "user", "content": "Hi"}]
    with pytest.raises(OllamaConnectionError, match="Ollama request timed out"):
        ollama_client_fixture.chat(messages)

@respx.mock
def test_health_endpoint_llm_ok():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ollama"] == "up"
    assert response.json()["model"] == "gpt-oss:20b"
    assert response.json()["model_available"] is True
    assert response.json()["fallback_used"] is False

@respx.mock
def test_health_endpoint_llm_unavailable():
    respx.get("http://localhost:11434/api/tags").mock(side_effect=httpx.ConnectError("Connection refused"))
    
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok" # Main app is still OK
    assert response.json()["ollama"] == "down"
    assert response.json()["model"] is None
    assert response.json()["model_available"] is False


@respx.mock
def test_chat_fallback_on_ollama_error():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    ollama_client.refresh_detection()
    respx.post("http://localhost:11434/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))

    chat_payload = {"message": "Run git status", "cwd": "."}
    response = test_client.post("/chat", json=chat_payload)
    
    assert response.status_code == 200
    chat_response = response.json()
    assert chat_response["intent"] == Intent.CHAT # Fallback intent
    assert chat_response["requires_approval"] is False
    assert "cannot connect to the local LLM" in chat_response["response"]
    assert "Failed to connect to LLM." in chat_response["plan"]

@respx.mock
def test_chat_fallback_on_model_missing():
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    ollama_client.refresh_detection()

    chat_payload = {"message": "Run git status", "cwd": "."}
    response = test_client.post("/chat", json=chat_payload)

    assert response.status_code == 200
    chat_response = response.json()
    assert chat_response["intent"] == Intent.CHAT
    assert chat_response["requires_approval"] is False
    assert "required Ollama model is not installed" in chat_response["response"]

