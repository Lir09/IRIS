# AI Operator (MVP)

AI Operator is a local FastAPI service that uses Ollama to classify user requests into:
- `chat`
- `code_help`
- `system_task`

For `system_task`, it enforces policy checks and requires explicit approval before command execution.

## What This Project Does
- Accepts natural language input through `/chat`
- Uses an LLM to produce structured intent + plan + optional command
- Blocks unsafe commands with a whitelist policy
- Restricts execution to a sandbox path
- Executes approved commands via PowerShell
- Stores execution logs in SQLite
- Provides a terminal chat client with session logging

## High-Level Flow
1. User sends a message to `POST /chat`
2. Ollama returns JSON: `intent`, `plan`, `proposed_command`
3. If `intent == system_task`, the policy layer validates command + `cwd`
4. If allowed, server creates an approval record and returns `approval_id`
5. User calls `POST /approvals/{approval_id}/execute`
6. Server executes command and stores a run record
7. User fetches run details with `GET /runs/{run_id}`

## Project Layout
```text
ai-operator/
  app/
    api/            # chat, health, approvals, runs endpoints
    core/           # intent routing, policy, app settings
    db/             # SQLAlchemy models, session, repositories
    llm/            # Ollama client + prompts
    tools/          # PowerShell execution helper
    main.py         # FastAPI entrypoint
  tests/
  cli_client.py     # interactive terminal chat client
  chat.bat          # Windows launcher for cli_client.py
  .env.example
  requirements.txt
```

## Requirements
- Windows (PowerShell or CMD examples below)
- Python 3.11+
- Ollama installed and running

## Quick Start

### 1) Move into the project
```powershell
cd C:\Users\gbin8\Documents\GitHub\IRIS\ai-operator
```

### 2) Create and activate venv
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3) Install dependencies
```powershell
pip install -r requirements.txt
```

### 4) Create env file
```powershell
copy .env.example .env
```

Default values:
```env
SANDBOX_ROOT=C:\ai-sandbox
DATABASE_URL=sqlite:///./ai_operator.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_TIMEOUT_SEC=120
OLLAMA_FALLBACK_MODEL=llama3.1:8b
```

Create sandbox folder if needed:
```powershell
mkdir C:\ai-sandbox
```

### 5) Start server
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Endpoints:
- API root: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Ollama Checks

### Check daemon and models
```powershell
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
```

### Pull model if missing
```powershell
ollama pull gpt-oss:20b
```

## Terminal Chat Mode

The repository includes a local terminal chat client with approval prompts and JSONL logging.

### Run from PowerShell
```powershell
cd C:\Users\gbin8\Documents\GitHub\IRIS\ai-operator
.\chat.bat
```

### Run from CMD
```cmd
cd C:\Users\gbin8\Documents\GitHub\IRIS\ai-operator
chat.bat
```

Important:
- In PowerShell, use `.\chat.bat` (without `.\`, command lookup fails for current directory scripts).

### Chat commands
- Type text at `You>` to chat
- `/help` prints client commands
- `/cwd` shows current `cwd` sent in chat payload
- `/log` prints active log file path
- `/exit` or `/quit` ends session

### Approval behavior
When the server returns:
- `requires_approval: true`
- `approval_id: <id>`

The client asks:
- `Run this command? [y/N]`

If `y`, it calls `POST /approvals/{approval_id}/execute` and prints execution output.

## Session Log Files

The terminal client writes structured events to:
- `logs/chat-YYYYMMDD-HHMMSS.jsonl`

Events include:
- `session_start`
- `health_ok` or `health_error`
- `user_message`
- `assistant_response`
- `approval_prompt`
- `execution_result`
- `chat_error` / `execute_error`
- `session_end`

Example JSONL row:
```json
{"ts":"2026-02-16T19:40:01","event":"user_message","message":"run dir","cwd":"C:\\ai-sandbox"}
```

## API Reference

### `GET /health`
Returns app and Ollama status.

Example:
```json
{
  "status": "ok",
  "ollama": "up",
  "model": "gpt-oss:20b",
  "model_available": true,
  "fallback_used": false
}
```

### `POST /chat`
Request:
```json
{
  "message": "run dir",
  "cwd": "C:\\ai-sandbox"
}
```

Response example (`system_task`):
```json
{
  "intent": "system_task",
  "plan": [
    "Acknowledge request for system task.",
    "Propose executing the command: 'dir'.",
    "Await user approval.",
    "Execute command upon approval."
  ],
  "requires_approval": true,
  "approval_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "proposed_command": "dir",
  "response": "I can do that. To proceed with the command 'dir', please confirm by executing the approval request."
}
```

### `POST /approvals/{approval_id}/execute`
Executes a pending approval and returns:
- `run_id`
- `ok`
- `stdout`
- `stderr`
- `returncode`

### `GET /runs/{run_id}`
Returns stored execution metadata and output for one run.

## Security Model

The policy layer enforces:
- Command prefix whitelist
- Sandboxed working directory checks
- Explicit approval before execution
- Execution timeout (default 120s)
- Output truncation (default max 8000 chars per stream)

Current allowed command prefixes (from `app/core/policy.py`):
- `git status`
- `git diff`
- `pytest`
- `python -m pytest`
- `docker ps`
- `dir`
- `ls`

## Troubleshooting

### `chat.bat` not recognized in PowerShell
Use:
```powershell
.\chat.bat
```

### Cannot connect to Ollama
- Ensure Ollama is running
- Check `OLLAMA_BASE_URL`
- Verify model exists with `ollama list`

### Model unavailable
Install model:
```powershell
ollama pull gpt-oss:20b
```

### Sandbox path denied
- Verify `SANDBOX_ROOT` in `.env`
- Ensure directory exists
- Send a `cwd` that is inside sandbox (use absolute path like `C:\ai-sandbox`)

## Run Tests
```powershell
.\venv\Scripts\python.exe -m pytest -q
```

## Key Files
- `app/main.py`
- `app/api/chat.py`
- `app/api/approvals.py`
- `app/api/health.py`
- `app/api/runs.py`
- `app/core/policy.py`
- `app/llm/client.py`
- `cli_client.py`
