import os
import shutil
from fastapi.testclient import TestClient
from app.main import app
from app.core.policy import SANDBOX_ROOT
from app.models.schemas import Intent
from app.llm.client import ollama_client
import pytest
import respx
import httpx
import json

client = TestClient(app)

# Mock the Ollama client calls for tests
@pytest.fixture(autouse=True)
def mock_ollama_client_responses():
    with respx.mock:
        # Default mock for health check (Ollama OK)
        respx.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json={"models": [{"name": "gpt-oss:20b"}]})
        )
        ollama_client.refresh_detection()

        # Default mock for chat (general chat)
        respx.post("http://localhost:11434/api/chat").mock(return_value=httpx.Response(200, json={
            "message": {"content": json.dumps({
                "intent": Intent.CHAT.value,
                "plan": ["Acknowledge user message.", "Provide a conversational response."],
                "proposed_command": None
            })}
        }))
        yield

# Setup and Teardown for sandbox
def setup_module(module):
    if os.path.exists(SANDBOX_ROOT):
        shutil.rmtree(SANDBOX_ROOT)
    os.makedirs(SANDBOX_ROOT, exist_ok=True)
    # Create a dummy file in the sandbox for 'dir' command to find
    with open(os.path.join(SANDBOX_ROOT, "dummy_file.txt"), "w") as f:
        f.write("test content")


def teardown_module(module):
    if os.path.exists(SANDBOX_ROOT):
        shutil.rmtree(SANDBOX_ROOT)


@respx.mock
def test_full_chat_to_execution_flow():
    # Mock LLM response for a system task 'git status'
    respx.post("http://localhost:11434/api/chat").mock(
        httpx.Response(200, json={"message": {"content": json.dumps({
            "intent": Intent.SYSTEM_TASK.value,
            "plan": ["Acknowledge request for system task.", "Propose executing the command: 'git status'.", "Await user approval.", "Execute command upon approval."],
            "proposed_command": "git status"
        })}}),
        content_type="application/json"
    )

    # --- Step 1: Post a chat message requesting a system task ---
    chat_payload = {
        "message": "Can you run git status for me?",
        "cwd": "." # Relative to sandbox root
    }
    response = client.post("/chat", json=chat_payload)
    
    assert response.status_code == 200
    chat_response = response.json()
    
    assert chat_response["intent"] == Intent.SYSTEM_TASK
    assert chat_response["requires_approval"] is True
    assert chat_response["proposed_command"] == "git status"
    assert chat_response["approval_id"] is not None
    
    approval_id = chat_response["approval_id"]

    # --- Step 2: Deny a bad command that the LLM might propose (but policy should catch) ---
    respx.post("http://localhost:11434/api/chat").mock(
        httpx.Response(200, json={"message": {"content": json.dumps({
            "intent": Intent.SYSTEM_TASK.value,
            "plan": ["Propose executing rm -rf /", "Await approval."],
            "proposed_command": "rm -rf /"
        })}}),
        content_type="application/json"
    )

    chat_payload_disallowed = {
        "message": "run rm -rf /",
        "cwd": "."
    }
    response = client.post("/chat", json=chat_payload_disallowed)
    assert response.status_code == 200
    chat_response_disallowed = response.json()
    assert chat_response_disallowed["requires_approval"] is False
    assert "not in the allowed list" in chat_response_disallowed["response"]


    # Mock LLM response for an allowed command 'dir'
    respx.post("http://localhost:11434/api/chat").mock(
        httpx.Response(200, json={"message": {"content": json.dumps({
            "intent": Intent.SYSTEM_TASK.value,
            "plan": ["Propose executing dir", "Await approval."],
            "proposed_command": "dir"
        })}}),
        content_type="application/json"
    )

    # --- Step 3: Post an allowed command directly ---
    chat_payload_allowed = {
        "message": "list files in current directory",
        "cwd": "."
    }
    response_allowed = client.post("/chat", json=chat_payload_allowed)
    assert response_allowed.status_code == 200
    chat_response_allowed = response_allowed.json()
    assert chat_response_allowed["intent"] == Intent.SYSTEM_TASK
    assert chat_response_allowed["requires_approval"] is True
    assert chat_response_allowed["proposed_command"] == "dir"
    
    approval_id_allowed = chat_response_allowed["approval_id"]

    # --- Step 4: Execute the approved task ---
    exec_response = client.post(f"/approvals/{approval_id_allowed}/execute")
    
    assert exec_response.status_code == 200
    exec_data = exec_response.json()

    assert exec_data["ok"] is True
    assert exec_data["returncode"] == 0
    assert "dummy_file.txt" in exec_data["stdout"] # Verify the command actually ran in the sandbox
    assert exec_data["run_id"] is not None
    
    run_id = exec_data["run_id"]

    # --- Step 5: Try to execute the same approval again (should fail) ---
    double_exec_response = client.post(f"/approvals/{approval_id_allowed}/execute")
    assert double_exec_response.status_code == 400
    assert "already been processed" in double_exec_response.json()["detail"]


    # --- Step 6: Retrieve the run log ---
    run_log_response = client.get(f"/runs/{run_id}")
    
    assert run_log_response.status_code == 200
    run_log_data = run_log_response.json()
    
    assert run_log_data["id"] == run_id
    assert run_log_data["approval_id"] == approval_id_allowed
    assert run_log_data["command"] == "dir"
    assert run_log_data["ok"] is True

@respx.mock
def test_chat_general_message():
    # Mock LLM response for a general chat message
    respx.post("http://localhost:11434/api/chat").mock(
        httpx.Response(200, json={"message": {"content": json.dumps({
            "intent": Intent.CHAT.value,
            "plan": ["Acknowledge user message.", "Provide a conversational response."],
            "proposed_command": None
        })}}),
        content_type="application/json"
    )

    chat_payload = {
        "message": "Hello there, how are you?",
        "cwd": "."
    }
    response = client.post("/chat", json=chat_payload)
    
    assert response.status_code == 200
    chat_response = response.json()
    assert chat_response["intent"] == Intent.CHAT
    assert chat_response["requires_approval"] is False
    assert "general chat response from the LLM" in chat_response["response"]
    assert "Acknowledge user message." in chat_response["plan"]

@respx.mock
def test_chat_code_help_message():
    # Mock LLM response for a code help message
    respx.post("http://localhost:11434/api/chat").mock(
        httpx.Response(200, json={"message": {"content": json.dumps({
            "intent": Intent.CODE_HELP.value,
            "plan": ["Analyze code.", "Provide explanation."],
            "proposed_command": None
        })}}),
        content_type="application/json"
    )

    chat_payload = {
        "message": "Explain this Python code: print('hello')",
        "cwd": "."
    }
    response = client.post("/chat", json=chat_payload)
    
    assert response.status_code == 200
    chat_response = response.json()
    assert chat_response["intent"] == Intent.CODE_HELP
    assert chat_response["requires_approval"] is False
    assert "response for code help" in chat_response["response"]
    assert "Analyze code." in chat_response["plan"]

