from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque


@dataclass(frozen=True)
class MemoryEntry:
    role: str
    content: str


class ConversationMemory:
    """
    In-memory session conversation store.
    Keeps a bounded number of recent messages per session.
    """

    def __init__(self, max_messages_per_session: int = 20):
        self.max_messages_per_session = max_messages_per_session
        self._store: dict[str, Deque[MemoryEntry]] = defaultdict(
            lambda: deque(maxlen=self.max_messages_per_session)
        )
        self._lock = Lock()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if not session_id or not content:
            return
        with self._lock:
            self._store[session_id].append(MemoryEntry(role=role, content=content))

    def get_history(self, session_id: str) -> list[MemoryEntry]:
        if not session_id:
            return []
        with self._lock:
            return list(self._store.get(session_id, []))

