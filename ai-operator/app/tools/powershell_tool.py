import subprocess
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Tool Configuration ---
DEFAULT_TIMEOUT = 120  # seconds
MAX_OUTPUT_CHARS = 8000

class PowerShellTool:
    """A tool for safely executing PowerShell commands."""

    def _normalize_command(self, command: str) -> str:
        """
        Expands cmd-style environment variables (e.g. %USERPROFILE%) so commands
        behave consistently in PowerShell across different Windows machines.
        """
        normalized_command = os.path.expandvars(command)
        if normalized_command != command:
            logger.info(
                "Expanded environment variables in command. "
                f"original='{command}' normalized='{normalized_command}'"
            )
        return normalized_command

    def execute(
        self,
        command: str,
        cwd: str | Path,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict:
        """
        Executes a command in PowerShell and captures the output.

        Returns a dictionary with:
        - returncode: The exit code of the process.
        - stdout: The standard output, truncated if necessary.
        - stderr: The standard error, truncated if necessary.
        - ok: A boolean indicating if the command succeeded (returncode 0).
        """
        if not command:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Error: Empty command provided.",
                "ok": False,
            }

        normalized_command = self._normalize_command(command)
        logger.info(f"Executing command: '{normalized_command}' in '{cwd}'")
        try:
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", normalized_command],
                capture_output=True,
                text=True,
                cwd=str(cwd),
                timeout=timeout,
                check=False, # We handle the return code manually
            )

            stdout = process.stdout
            stderr = process.stderr

            if len(stdout) > MAX_OUTPUT_CHARS:
                stdout = f"[... TRUNCATED ...]\n{stdout[-MAX_OUTPUT_CHARS:]}"
            
            if len(stderr) > MAX_OUTPUT_CHARS:
                stderr = f"[... TRUNCATED ...]\n{stderr[-MAX_OUTPUT_CHARS:]}"

            ok = process.returncode == 0
            if not ok:
                 logger.warning(f"Command finished with non-zero exit code {process.returncode}. stderr: {stderr}")

            return {
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "ok": ok,
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command '{normalized_command}' timed out after {timeout} seconds.")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Error: Command timed out after {timeout} seconds.",
                "ok": False,
            }
        except FileNotFoundError:
            logger.error(f"Execution failed. CWD '{cwd}' does not exist.")
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Error: The specified directory does not exist: {cwd}",
                "ok": False
            }
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while executing command '{normalized_command}': {e}"
            )
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"An unexpected error occurred: {str(e)}",
                "ok": False,
            }


