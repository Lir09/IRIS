import httpx
import json
import os
import sys

# 기본 API 설정
BASE_URL = "http://127.0.0.1:8000"
CHAT_ENDPOINT = f"{BASE_URL}/chat"
APPROVAL_EXECUTE_ENDPOINT = f"{BASE_URL}/approvals/{{approval_id}}/execute"
HEALTH_ENDPOINT = f"{BASE_URL}/health"

def print_response(response_json: dict):
    """API 응답을 보기 좋게 출력합니다."""
    print(f"--- 응답 ---")
    if "intent" in response_json:
        print(f"  의도: {response_json.get('intent')}")
    if "plan" in response_json and response_json["plan"]:
        print(f"  계획:")
        for step in response_json["plan"]:
            print(f"    - {step}")
    if "requires_approval" in response_json:
        print(f"  승인 필요: {response_json.get('requires_approval')}")
    if "proposed_command" in response_json and response_json["proposed_command"]:
        print(f"  제안된 명령: {response_json.get('proposed_command')}")
    if "response" in response_json:
        print(f"  응답 메시지: {response_json.get('response')}")
    if "run_id" in response_json:
        print(f"  실행 ID: {response_json.get('run_id')}")
    if "ok" in response_json:
        print(f"  성공 여부: {response_json.get('ok')}")
    if "returncode" in response_json:
        print(f"  리턴 코드: {response_json.get('returncode')}")
    if "stdout" in response_json and response_json["stdout"]:
        print(f"  STDOUT:
{response_json['stdout']}")
    if "stderr" in response_json and response_json["stderr"]:
        print(f"  STDERR:
{response_json['stderr']}")
    print(f"------------")

async def chat_loop():
    """AI Operator와 상호작용하는 CLI 루프입니다."""
    print("AI Operator CLI 클라이언트에 오신 것을 환영합니다!")
    print(f"서버 URL: {BASE_URL}")
    print("종료하려면 'exit' 또는 'quit'을 입력하세요.")

    client = httpx.AsyncClient()
    current_cwd = os.getcwd() # 클라이언트의 현재 작업 디렉토리

    # 헬스체크
    try:
        health_response = await client.get(HEALTH_ENDPOINT)
        health_response.raise_for_status()
        health_data = health_response.json()
        print(f"서버 헬스체크: {health_data.get('status')}")
        if health_data.get('llm_status'):
            print(f"LLM 상태: {health_data.get('llm_status')} ({health_data.get('llm_message')})")
    except httpx.RequestError as e:
        print(f"서버에 연결할 수 없습니다: {e}. 서버가 {BASE_URL}에서 실행 중인지 확인하세요.")
        return

    while True:
        try:
            message = input(f"
({current_cwd}) 당신: ")
            if message.lower() in ["exit", "quit"]:
                print("CLI 클라이언트를 종료합니다.")
                break

            # chat 요청
            chat_payload = {
                "message": message,
                "cwd": current_cwd
            }
            response = await client.post(CHAT_ENDPOINT, json=chat_payload)
            response.raise_for_status()
            chat_response = response.json()
            
            print_response(chat_response)

            # 승인 필요 여부 확인
            if chat_response.get("requires_approval") and chat_response.get("approval_id"):
                approval_id = chat_response["approval_id"]
                proposed_command = chat_response.get("proposed_command", "알 수 없는 명령")
                
                confirm = input(f"제안된 명령 '{proposed_command}'을(를) 실행하시겠습니까? (y/N): ").lower()
                if confirm == 'y':
                    print(f"'{approval_id}' 승인 요청 실행 중...")
                    execute_url = APPROVAL_EXECUTE_ENDPOINT.format(approval_id=approval_id)
                    execute_response = await client.post(execute_url)
                    execute_response.raise_for_status()
                    execute_result = execute_response.json()
                    print_response(execute_result)
                else:
                    print("명령 실행을 취소했습니다.")
            
            # cwd 변경 요청 처리 (LLM이 제안할 경우)
            if chat_response.get("intent") == "system_task" and chat_response.get("proposed_command", "").lower().strip().startswith("cd "):
                new_path = chat_response["proposed_command"].split(" ", 1)[1].strip()
                try:
                    if os.path.isabs(new_path):
                        os.chdir(new_path)
                    else:
                        os.chdir(os.path.join(current_cwd, new_path))
                    current_cwd = os.getcwd()
                    print(f"작업 디렉토리를 '{current_cwd}'(으)로 변경했습니다.")
                except OSError as e:
                    print(f"오류: 디렉토리를 변경할 수 없습니다. {e}")


        except httpx.RequestError as e:
            print(f"API 요청 중 오류 발생: {e}. 서버가 실행 중인지 확인하세요.")
        except json.JSONDecodeError:
            print(f"API 응답 파싱 중 오류 발생: {response.text}")
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")

    await client.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(chat_loop())
