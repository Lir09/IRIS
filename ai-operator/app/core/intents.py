from app.models.schemas import Intent

# This file is kept for consistency with the project structure.
# The Intent enum is defined in schemas.py to avoid circular dependencies.
# You can add intent-related helper functions here if needed.

def is_task_intent(intent: Intent) -> bool:
    """Checks if the intent requires performing a system task."""
    return intent == Intent.SYSTEM_TASK
