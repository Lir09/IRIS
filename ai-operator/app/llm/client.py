import os
import httpx
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()
logger = logging.getLogger(__name__)

class OllamaConnectionError(Exception):
    """Custom exception for Ollama connection issues."""
    pass

class OllamaClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT_SEC", 120))
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        logger.info(f"OllamaClient initialized with base_url: {self.base_url}, model: {self.model}, timeout: {self.timeout}s")

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        try:
            response = self.client.request(method, path, **kwargs)
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

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
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

    def check_ollama_status(self) -> Dict[str, Any]:
        try:
            # A simple GET request to check server status
            # /api/tags lists available models, implies server is up
            response_data = self._request("GET", "/api/tags")
            
            # Check if the configured model is available
            available_models = [m['name'] for m in response_data.get('models', [])]
            if self.model in available_models:
                return {"status": "ok", "message": f"Ollama server is running and model '{self.model}' is available."}
            else:
                return {"status": "warning", "message": f"Ollama server is running but model '{self.model}' is not available. Available models: {', '.join(available_models)}"}
        except OllamaConnectionError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            return {"status": "error", "message": f"An unexpected error occurred during Ollama status check: {e}"}

# Global client instance to avoid recreating it on each request
ollama_client = OllamaClient()

if __name__ == '__main__':
    # Example usage (for testing)
    print("--- Ollama Status Check ---")
    status_info = ollama_client.check_ollama_status()
    print(status_info)

    if status_info["status"] == "ok":
        print("
--- Sending a test chat message ---")
        test_messages = [
            {"role": "user", "content": "Hello, how are you today?"}
        ]
        try:
            response_content = ollama_client.chat(test_messages)
            print(f"Ollama Response: {response_content}")
        except OllamaConnectionError as e:
            print(f"Chat failed: {e}")
    else:
        print("Ollama server or model not ready. Skipping chat test.")
