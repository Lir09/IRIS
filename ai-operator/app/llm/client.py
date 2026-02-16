import httpx
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.settings import DEFAULT_OLLAMA_MODEL, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaModelDetection:
    ollama_up: bool
    model_available: bool
    selected_model: Optional[str]
    reason: str
    fallback_used: bool


class OllamaConnectionError(Exception):
    """Custom exception for Ollama connection issues."""
    pass


class OllamaModelUnavailableError(Exception):
    """Raised when no suitable Ollama model is available."""
    pass


class OllamaClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.timeout = settings.ollama_timeout_sec
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        self._env_model = settings.ollama_model
        self._fallback_model = settings.ollama_fallback_model
        self._detection = self.detect_ollama_model()
        self.model = self._detection.selected_model
        logger.info(
            "OllamaClient initialized with selection result: "
            f"ollama_up={self._detection.ollama_up} "
            f"model_available={self._detection.model_available} "
            f"selected_model={self._detection.selected_model} "
            f"fallback_used={self._detection.fallback_used} "
            f"reason={self._detection.reason}"
        )

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self.client.request(method, path, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            logger.error(f"Ollama connection failed: {e}")
            raise OllamaConnectionError(f"Could not connect to Ollama server at {self.base_url}. Is it running?") from e
        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out: {e}")
            raise OllamaConnectionError(f"Ollama request timed out after {self.timeout}s.") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
            raise OllamaConnectionError(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Ollama request: {e}")
            raise OllamaConnectionError(f"Unexpected Ollama error: {e}") from e

    def _parse_model_names(self, response_data: Dict[str, Any]) -> List[str]:
        models = response_data.get("models", [])
        if not isinstance(models, list):
            return []
        model_names: List[str] = []
        for model in models:
            if isinstance(model, dict) and "name" in model:
                model_names.append(str(model["name"]))
        return model_names

    def _select_model(self, available_models: List[str]) -> tuple[Optional[str], bool, bool, str]:
        if self._env_model and self._env_model in available_models:
            return self._env_model, True, False, f"Using environment model '{self._env_model}'."

        if DEFAULT_OLLAMA_MODEL in available_models:
            return DEFAULT_OLLAMA_MODEL, True, False, f"Using default model '{DEFAULT_OLLAMA_MODEL}'."

        if self._fallback_model in available_models:
            return self._fallback_model, True, True, f"Using fallback model '{self._fallback_model}'."

        return None, False, False, (
            "Ollama is running but no preferred models are installed. "
            "Install 'gpt-oss:20b' or a fallback model."
        )

    def detect_ollama_model(self) -> OllamaModelDetection:
        try:
            response_data = self._request("GET", "/api/tags")
        except OllamaConnectionError as e:
            return OllamaModelDetection(
                ollama_up=False,
                model_available=False,
                selected_model=None,
                reason=str(e),
                fallback_used=False,
            )

        available_models = self._parse_model_names(response_data)
        selected_model, model_available, fallback_used, reason = self._select_model(available_models)
        return OllamaModelDetection(
            ollama_up=True,
            model_available=model_available,
            selected_model=selected_model,
            reason=reason,
            fallback_used=fallback_used,
        )

    def refresh_detection(self) -> OllamaModelDetection:
        self._detection = self.detect_ollama_model()
        self.model = self._detection.selected_model
        return self._detection

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        if not self.model:
            logger.info("No selected Ollama model cached. Refreshing model detection before chat.")
            detection = self.refresh_detection()
            if not detection.model_available or not detection.selected_model:
                raise OllamaModelUnavailableError(
                    "No suitable Ollama model is available. "
                    "Please pull 'gpt-oss:20b' or configure OLLAMA_MODEL."
                )

        if not self.model:
            raise OllamaModelUnavailableError(
                "No suitable Ollama model is available. "
                "Please pull 'gpt-oss:20b' or configure OLLAMA_MODEL."
            )
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        logger.debug(f"Sending chat request to Ollama: {payload}")
        response_data = self._request("POST", "/api/chat", json=payload)
        
        # Ollama's chat endpoint response structure
        if "message" in response_data and "content" in response_data["message"]:
            return response_data["message"]["content"]
        
        logger.error(f"Unexpected Ollama chat response format: {response_data}")
        raise OllamaConnectionError("Unexpected response format from Ollama chat endpoint.")

    def get_detection_status(self, refresh: bool = False) -> OllamaModelDetection:
        if refresh:
            return self.refresh_detection()
        return self._detection

# Global client instance to avoid recreating it on each request
ollama_client = OllamaClient()

if __name__ == '__main__':
    # Example usage (for testing)
    print("--- Ollama Status Check ---")
    detection = ollama_client.get_detection_status()
    print(detection)

    if detection.ollama_up and detection.model_available:
        print("\n--- Sending a test chat message ---")
        test_messages = [
            {"role": "user", "content": "Hello, how are you today?"}
        ]
        try:
            response_content = ollama_client.chat(test_messages)
            print(f"Ollama Response: {response_content}")
        except (OllamaConnectionError, OllamaModelUnavailableError) as e:
            print(f"Chat failed: {e}")
    else:
        print("Ollama server or model not ready. Skipping chat test.")
