from fastapi import APIRouter
from app.models.schemas import LLMHealthResponse
from app.llm.client import ollama_client

router = APIRouter()

@router.get("/health", tags=["System"], response_model=LLMHealthResponse)
def health_check():
    """
    Performs a health check of the application, including LLM connectivity.
    """
    detection = ollama_client.get_detection_status(refresh=True)
    ollama_state = "up" if detection.ollama_up else "down"
    return LLMHealthResponse(
        status="ok",
        ollama=ollama_state,
        model=detection.selected_model,
        model_available=detection.model_available,
        fallback_used=detection.fallback_used,
    )
