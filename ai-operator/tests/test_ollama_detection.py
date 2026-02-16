import httpx
import respx

from app.llm.client import OllamaClient


@respx.mock
def test_detect_ollama_up_and_model_available(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
    )
    client = OllamaClient()
    detection = client.detect_ollama_model()

    assert detection.ollama_up is True
    assert detection.model_available is True
    assert detection.selected_model == "gpt-oss:20b"
    assert ("environment model" in detection.reason) or ("default model" in detection.reason)


@respx.mock
def test_detect_ollama_up_but_model_missing(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": []})
    )
    client = OllamaClient()
    detection = client.detect_ollama_model()

    assert detection.ollama_up is True
    assert detection.model_available is False
    assert detection.selected_model is None
    assert "no preferred models are installed" in detection.reason


@respx.mock
def test_detect_ollama_down(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    respx.get("http://localhost:11434/api/tags").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    client = OllamaClient()
    detection = client.detect_ollama_model()

    assert detection.ollama_up is False
    assert detection.model_available is False
    assert detection.selected_model is None
    assert "Could not connect to Ollama server" in detection.reason


@respx.mock
def test_model_selection_priority_env_over_default(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model:latest")
    respx.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "custom-model:latest"}, {"name": "gpt-oss:20b"}]})
    )
    client = OllamaClient()
    detection = client.detect_ollama_model()

    assert detection.ollama_up is True
    assert detection.model_available is True
    assert detection.selected_model == "custom-model:latest"
    assert "environment model" in detection.reason
