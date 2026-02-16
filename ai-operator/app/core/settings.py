from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_OLLAMA_TIMEOUT_SEC = 120
DEFAULT_OLLAMA_FALLBACK_MODEL = "llama3.1:8b"


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    ollama_model: str | None
    ollama_timeout_sec: int
    ollama_fallback_model: str


def get_settings() -> Settings:
    load_dotenv()
    model_env = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    model_env = model_env.strip() if model_env else None
    return Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        ollama_model=model_env or None,
        ollama_timeout_sec=int(os.getenv("OLLAMA_TIMEOUT_SEC", str(DEFAULT_OLLAMA_TIMEOUT_SEC))),
        ollama_fallback_model=os.getenv("OLLAMA_FALLBACK_MODEL", DEFAULT_OLLAMA_FALLBACK_MODEL),
    )
