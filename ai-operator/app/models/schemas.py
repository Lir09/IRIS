import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


# --- Enums ---

class Intent(str, Enum):
    CHAT = "chat"
    CODE_HELP = "code_help"
    SYSTEM_TASK = "system_task"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    REJECTED = "rejected"


# --- API Request Models ---

class ChatRequest(BaseModel):
    message: str
    cwd: Optional[str] = None
    session_id: Optional[str] = None


# --- API Response Models ---

class ChatResponse(BaseModel):
    intent: Intent
    plan: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_id: Optional[str] = None
    proposed_command: Optional[str] = None
    response: str


class ExecutionResponse(BaseModel):
    run_id: str
    ok: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: int


class HealthResponse(BaseModel):
    status: str = "ok"


class LLMHealthResponse(HealthResponse):
    ollama: str
    model: Optional[str] = None
    model_available: bool
    fallback_used: bool


# --- Database Models (Pydantic representation) ---

class Approval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    proposed_command: str
    cwd: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True


class Run(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approval_id: str
    command: str
    cwd: str
    returncode: int
    ok: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
