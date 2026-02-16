import logging
import json
from app.models.schemas import Intent, ChatRequest, ChatResponse
from app.llm.client import ollama_client, OllamaConnectionError
from app.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class IntentRouter:
    """
    Determines the user's intent from their message using an LLM.
    """
    def classify_intent(self, request: ChatRequest) -> tuple[Intent, list[str], str | None]:
        """
        Classifies intent, generates a plan, and extracts a proposed command using Ollama.
        Returns: (intent, plan, proposed_command)
        """
        user_message_content = f"User: {request.message}"
        if request.cwd:
            user_message_content += f"\nCurrent Working Directory: {request.cwd}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message_content}
        ]

        try:
            llm_response_content = ollama_client.chat(messages)
            logger.debug(f"LLM raw response: {llm_response_content}")

            # Attempt to parse the JSON response from the LLM
            llm_output = json.loads(llm_response_content)
            
            intent = Intent(llm_output.get("intent"))
            plan = llm_output.get("plan", [])
            proposed_command = llm_output.get("proposed_command")

            logger.info(f"LLM classified intent as {intent}, proposed command: {proposed_command}")
            return intent, plan, proposed_command
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error during intent classification: {e}")
            # Fallback to a safe default if LLM is unavailable
            return Intent.CHAT, ["LLM is unavailable. Please try again later."], None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {llm_response_content}. Error: {e}")
            return Intent.CHAT, ["Failed to parse LLM response. Please try again or rephrase your request."], None
        except Exception as e:
            logger.error(f"An unexpected error occurred during intent classification: {e}")
            return Intent.CHAT, ["An internal error occurred during intent classification."], None


