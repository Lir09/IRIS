import os
import re
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# --- Safety Configuration ---
SANDBOX_ROOT = os.getenv("SANDBOX_ROOT", "C:\ai-sandbox")
ALLOWED_COMMAND_PREFIXES = [
    "git status",
    "git diff",
    "pytest",
    "python -m pytest",
    "docker ps",
    "dir",
    "ls",  # Adding ls for user convenience
    # Safe-by-default file creation/edit commands (restricted by sandbox checks below)
    "echo ",
    "set-content ",
    "out-file ",
    "new-item ",
]

# Block common sandbox-escape patterns in command arguments.
DISALLOWED_COMMAND_PATTERNS = [
    re.compile(r"[a-zA-Z]:\\"),
    re.compile(r"\\\\"),
    re.compile(r"\.\."),
]

class PolicyEnforcer:
    """
    Enforces security policies for command execution.
    """

    def __init__(self, sandbox_root: str = SANDBOX_ROOT, allowed_prefixes: list = None):
        try:
            self.sandbox_root = Path(sandbox_root).resolve()
            if not self.sandbox_root.exists():
                logger.warning(f"Sandbox root '{self.sandbox_root}' does not exist. Creating it.")
                self.sandbox_root.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Invalid SANDBOX_ROOT path: {sandbox_root}. Error: {e}")
            raise ValueError(f"Invalid SANDBOX_ROOT path: {sandbox_root}") from e
        
        self.allowed_prefixes = allowed_prefixes if allowed_prefixes is not None else ALLOWED_COMMAND_PREFIXES
        logger.info(f"PolicyEnforcer initialized. Sandbox: '{self.sandbox_root}', Allowed Prefixes: {self.allowed_prefixes}")


    def is_command_allowed(self, command: str) -> bool:
        """Checks if the command matches any of the allowed prefixes."""
        normalized_command = command.strip().lower()
        for prefix in self.allowed_prefixes:
            if normalized_command.startswith(prefix.lower()):
                return True
        logger.warning(f"Command denied by policy (not in whitelist): '{command}'")
        return False

    def has_disallowed_command_pattern(self, command: str) -> bool:
        """
        Checks command string for absolute/traversal path patterns that could escape sandbox.
        """
        normalized_command = command.strip()
        for pattern in DISALLOWED_COMMAND_PATTERNS:
            if pattern.search(normalized_command):
                logger.warning(
                    "Command denied by policy (disallowed path pattern): "
                    f"pattern='{pattern.pattern}' command='{command}'"
                )
                return True
        return False

    def is_path_in_sandbox(self, cwd: str | Path) -> bool:
        """Checks if the given path is within the configured sandbox directory."""
        try:
            target_path = Path(cwd).resolve()
            is_safe = target_path.is_relative_to(self.sandbox_root)
            if not is_safe:
                 logger.warning(f"Path check failed: '{target_path}' is not in sandbox '{self.sandbox_root}'")
            return is_safe
        except Exception as e:
            # This can happen for invalid path strings
            logger.error(f"Path validation error for cwd='{cwd}': {e}")
            return False

    def check_all(self, command: str, cwd: str | Path | None) -> (bool, str):
        """Runs all checks and returns a tuple (is_ok, reason)."""
        if cwd is None:
            return False, "Execution path (cwd) must be provided."
        
        if not self.is_path_in_sandbox(cwd):
            return False, f"Execution path is outside the security sandbox. Allowed root: {self.sandbox_root}"

        if not self.is_command_allowed(command):
            return False, "Command is not in the allowed list."

        if self.has_disallowed_command_pattern(command):
            return False, "Command contains a disallowed path pattern (outside-sandbox risk)."

        return True, "Command is allowed."
