import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.router import IntentRouter
from app.core.policy import PolicyEnforcer
from app.db.database import get_db
from app.db.repositories import ApprovalRepository
from app.models.schemas import ChatRequest, ChatResponse, Approval, Intent
from app.llm.client import OllamaConnectionError

router = APIRouter()
logger = logging.getLogger(__name__)

intent_router = IntentRouter()
policy_enforcer = PolicyEnforcer()


@router.post("/chat", tags=["Chat"], response_model=ChatResponse)
async def post_chat_message(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Receives a natural language message, determines intent, and responds using Ollama.
    If the intent is a system task, it creates an approval request.
    """
    try:
        intent, plan, proposed_command = intent_router.classify_intent(request)
    except OllamaConnectionError as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        return ChatResponse(
            intent=Intent.CHAT, # Default to chat for safety
            plan=["Failed to connect to LLM."],
            response="I'm sorry, I cannot connect to the local LLM at the moment. Please ensure Ollama is running and the model is pulled."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during intent classification: {e}")
        return ChatResponse(
            intent=Intent.CHAT,
            plan=["An unexpected error occurred."],
            response="I'm sorry, an unexpected error occurred while processing your request."
        )

    # --- Handle System Task Intent ---
    if intent == Intent.SYSTEM_TASK:
        if not proposed_command:
            return ChatResponse(
                intent=intent,
                plan=plan,
                response="I identified a system task, but the LLM couldn't determine the specific command. Please be more explicit, for example: 'run git status'."
            )

        # Policy enforcement is crucial
        is_allowed, reason = policy_enforcer.check_all(proposed_command, request.cwd)
        if not is_allowed:
            return ChatResponse(
                intent=intent,
                plan=plan,
                response=f"I cannot execute this command. Reason: {reason}"
            )

        # Create and save an approval request
        approval_repo = ApprovalRepository(db)
        # Ensure cwd is within sandbox root if provided, otherwise default to sandbox root
        execution_cwd = str(policy_enforcer.sandbox_root.joinpath(request.cwd)) if request.cwd else str(policy_enforcer.sandbox_root)

        approval_request = Approval(
            message=request.message,
            proposed_command=proposed_command,
            cwd=execution_cwd,
        )
        db_approval = approval_repo.create_approval(approval_request)
        
        logger.info(f"Created approval request '{db_approval.id}' for command: '{proposed_command}'")

        return ChatResponse(
            intent=intent,
            plan=plan,
            requires_approval=True,
            approval_id=db_approval.id,
            proposed_command=proposed_command,
            response=f"I can do that. To proceed with the command '{proposed_command}', please confirm by executing the approval request."
        )

    # --- Handle Code Help Intent ---
    if intent == Intent.CODE_HELP:
        # In a full implementation, you'd use LLM again for the actual code help response
        return ChatResponse(
            intent=intent,
            plan=plan,
            response=f"This is the response for code help, based on your request: '{request.message}'. Plan: {', '.join(plan)}"
        )

    # --- Handle General Chat Intent ---
    return ChatResponse(
        intent=intent,
        plan=plan,
        response=f"This is a general chat response from the LLM, based on your request: '{request.message}'. Plan: {', '.join(plan)}"
    )
