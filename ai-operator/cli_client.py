import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


BASE_URL = os.getenv("AI_OPERATOR_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CHAT_URL = f"{BASE_URL}/chat"
APPROVAL_EXEC_URL = f"{BASE_URL}/approvals/{{approval_id}}/execute"
HEALTH_URL = f"{BASE_URL}/health"
DEFAULT_SANDBOX_CWD = os.getenv("SANDBOX_ROOT", r"C:\ai-sandbox")


def append_log(log_path: Path, event: str, payload: dict[str, Any]) -> None:
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **payload,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def print_chat_response(data: dict[str, Any]) -> None:
    text = data.get("response", "")
    if text:
        print(f"IRIS> {text}")

    if data.get("proposed_command"):
        print(f"[command] {data['proposed_command']}")


def print_execution_response(data: dict[str, Any]) -> None:
    ok = data.get("ok")
    returncode = data.get("returncode")
    run_id = data.get("run_id")
    print(f"[execution] ok={ok} returncode={returncode} run_id={run_id}")

    stdout = data.get("stdout")
    stderr = data.get("stderr")
    if stdout:
        print("[stdout]")
        print(stdout)
    if stderr:
        print("[stderr]")
        print(stderr)


def main() -> None:
    # Use sandbox as default execution cwd so policy checks pass by default.
    current_cwd = DEFAULT_SANDBOX_CWD
    if not Path(current_cwd).exists():
        current_cwd = os.getcwd()
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = logs_dir / f"chat-{session_id}.jsonl"

    print("IRIS CLI chat")
    print(f"Server: {BASE_URL}")
    print(f"Log: {log_path}")
    print("Type /exit to quit. Type /help for commands.")
    append_log(
        log_path,
        "session_start",
        {
            "base_url": BASE_URL,
            "cwd": current_cwd,
            "session_id": session_id,
        },
    )

    with httpx.Client(timeout=120.0) as client:
        try:
            health = client.get(HEALTH_URL)
            health.raise_for_status()
            print("[connected] /health OK")
            append_log(log_path, "health_ok", {"status_code": health.status_code})
        except Exception as exc:
            print(f"[error] Server is not reachable: {exc}")
            append_log(log_path, "health_error", {"error": str(exc)})
            return

        while True:
            try:
                message = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not message:
                continue

            if message in {"/exit", "/quit"}:
                print("Bye.")
                append_log(log_path, "session_end", {"reason": "user_exit"})
                break

            if message == "/help":
                print("Commands:")
                print("/help - show this help")
                print("/exit - quit")
                print("/cwd  - show current cwd sent to server")
                print("/sandbox - set cwd to SANDBOX_ROOT")
                print("/log  - show current log file")
                continue

            if message == "/cwd":
                print(f"cwd: {current_cwd}")
                continue

            if message == "/log":
                print(f"log: {log_path}")
                continue

            if message == "/sandbox":
                current_cwd = DEFAULT_SANDBOX_CWD
                print(f"cwd set to sandbox: {current_cwd}")
                append_log(log_path, "cwd_changed", {"cwd": current_cwd, "mode": "sandbox"})
                continue

            payload = {"message": message, "cwd": current_cwd}
            append_log(log_path, "user_message", payload)

            try:
                chat_resp = client.post(CHAT_URL, json=payload)
                chat_resp.raise_for_status()
                chat_data = chat_resp.json()
            except json.JSONDecodeError:
                print("[error] Chat response was not valid JSON.")
                append_log(
                    log_path,
                    "chat_error",
                    {"error": "invalid_json", "status_code": chat_resp.status_code},
                )
                continue
            except Exception as exc:
                print(f"[error] Chat request failed: {exc}")
                append_log(log_path, "chat_error", {"error": str(exc)})
                continue

            print_chat_response(chat_data)
            append_log(log_path, "assistant_response", chat_data)

            if chat_data.get("requires_approval") and chat_data.get("approval_id"):
                approval_id = chat_data["approval_id"]
                confirm = input("Run this command? [y/N] ").strip().lower()
                append_log(
                    log_path,
                    "approval_prompt",
                    {
                        "approval_id": approval_id,
                        "proposed_command": chat_data.get("proposed_command"),
                        "user_confirm": confirm == "y",
                    },
                )
                if confirm != "y":
                    print("[skipped] command not executed")
                    continue

                exec_url = APPROVAL_EXEC_URL.format(approval_id=approval_id)
                try:
                    exec_resp = client.post(exec_url)
                    exec_resp.raise_for_status()
                    exec_data = exec_resp.json()
                except json.JSONDecodeError:
                    print("[error] Execute response was not valid JSON.")
                    append_log(
                        log_path,
                        "execute_error",
                        {"error": "invalid_json", "approval_id": approval_id},
                    )
                    continue
                except Exception as exc:
                    print(f"[error] Execute request failed: {exc}")
                    append_log(
                        log_path,
                        "execute_error",
                        {"error": str(exc), "approval_id": approval_id},
                    )
                    continue

                print_execution_response(exec_data)
                append_log(
                    log_path,
                    "execution_result",
                    {"approval_id": approval_id, **exec_data},
                )


if __name__ == "__main__":
    main()
