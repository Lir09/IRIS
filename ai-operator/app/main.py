import logging
from fastapi import FastAPI
from app.api import health, chat, approvals, runs
from app.db.init_db import init_db
from app.llm.client import ollama_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

app = FastAPI(
    title="AI Operator",
    description="A 'Jarvis/Friday style' personal AI Operator server.",
    version="0.1.0-mvp"
)

# Include API routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(approvals.router)
app.include_router(runs.router)

@app.on_event("startup")
def on_startup():
    logging.info("Application starting up...")
    try:
        init_db()
    except Exception as e:
        logging.critical(f"Database initialization failed: {e}")
        # In a real app, you might want to exit if the DB is not available
        # For this MVP, we log a critical error and continue.
    detection = ollama_client.get_detection_status()
    logging.info(
        "Ollama selection at startup: "
        f"ollama_up={detection.ollama_up} "
        f"model_available={detection.model_available} "
        f"selected_model={detection.selected_model} "
        f"fallback_used={detection.fallback_used} "
        f"reason={detection.reason}"
    )
    logging.info("Application startup complete.")

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the AI Operator API. See /docs for details."}
