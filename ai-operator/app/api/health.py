from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.llm.client import ollama_client

router = APIRouter()

class LLMHealthResponse(HealthResponse):
    llm_status: str
    llm_message: str

@router.get("/health", tags=["System"], response_model=LLMHealthResponse)
def health_check():
    """
    Performs a health check of the application, including LLM connectivity.
    """
    ollama_health = ollama_client.check_ollama_status()
    return LLMHealthResponse(
        status="ok",
        llm_status=ollama_health["status"],
        llm_message=ollama_health["message"]
    )
