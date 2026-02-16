import logging
import json
import re
from app.core.memory import MemoryEntry
from app.models.schemas import Intent, ChatRequest, ChatResponse
from app.llm.client import ollama_client, OllamaConnectionError, OllamaModelUnavailableError
from app.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _parse_llm_json_payload(raw_text: str) -> dict:
    """
    Parse LLM output into JSON, tolerating Markdown code fences.
    """
    text = raw_text.strip()

    # Fast path: already valid JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove fenced block markers and parse inner content.
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        fenced_body = fence_match.group(1).strip()
        try:
            return json.loads(fenced_body)
        except json.JSONDecodeError:
            pass

    # Last chance: extract the first JSON object-like region.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        return json.loads(candidate)

    raise json.JSONDecodeError("No valid JSON object found in LLM response.", text, 0)

class IntentRouter:
    """
    Determines the user's intent from their message using an LLM.
    """
    def classify_intent(
        self,
        request: ChatRequest,
        history: list[MemoryEntry] | None = None,
    ) -> tuple[Intent, list[str], str | None, str | None]:
        """
        Classifies intent, generates a plan, and extracts structured response fields using Ollama.
        Returns: (intent, plan, proposed_command, response_text)
        """
        user_message_content = ""
        if history:
            history_lines = []
            for entry in history[-10:]:
                role = "User" if entry.role.lower() == "user" else "Assistant"
                history_lines.append(f"{role}: {entry.content}")
            user_message_content += "Conversation history:\n" + "\n".join(history_lines) + "\n\n"

        user_message_content += f"User: {request.message}"
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
            llm_output = _parse_llm_json_payload(llm_response_content)
            
            intent = Intent(llm_output.get("intent"))
            plan = llm_output.get("plan", [])
            proposed_command = llm_output.get("proposed_command")
            response_text = llm_output.get("response")

            logger.info(f"LLM classified intent as {intent}, proposed command: {proposed_command}")
            return intent, plan, proposed_command, response_text
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error during intent classification: {e}")
            raise
        except OllamaModelUnavailableError as e:
            logger.error(f"Ollama model unavailable during intent classification: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {llm_response_content}. Error: {e}")
            return Intent.CHAT, ["Failed to parse LLM response. Please try again or rephrase your request."], None, None
        except Exception as e:
            logger.error(f"An unexpected error occurred during intent classification: {e}")
            return Intent.CHAT, ["An internal error occurred during intent classification."], None, None


