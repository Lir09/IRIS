````markdown
# AI Operator - MVP

## 1. 프로젝트 개요

"AI Operator"는 "Jarvis/Friday 스타일"의 개인용 AI 비서 서버를 구현하기 위한 MVP(Minimum Viable Product) 프로젝트입니다. 이 시스템은 자연어 요청을 받아 의도를 파악하고, 안전한 환경에서 시스템 명령을 실행하며, 모든 과정을 기록합니다.

핵심 목표는 LLM(거대 언어 모델)을 백엔드 시스템과 안전하게 통합하여, 단순 채팅을 넘어 실제 작업을 수행하는 에이전트를 만드는 것입니다.

**주요 기능:**
- **의도 분류**: 사용자의 요청을 `chat`, `code_help`, `system_task`로 분류합니다.
- **실행 계획**: 작업을 수행하기 위한 계획을 생성합니다.
- **안전한 실행**: 모든 시스템 작업은 사용자의 승인을 거치며, 허용된 명령어만, 지정된 샌드박스 폴더 내에서 실행됩니다.
- **실행 기록**: 모든 실행 결과는 데이터베이스에 기록되어 추적이 가능합니다.
- **API 기반**: 모든 기능은 FastAPI를 통해 REST API로 제공됩니다.

## 2. 설치 방법 (Windows PowerShell 기준)

**요구사항:**
- Python 3.11+
- Git

**설치 과정:**

1.  **프로젝트 클론**
    ```powershell
    git clone <your-repo-url>
    cd ai-operator
    ```

2.  **가상 환경 생성 및 활성화**
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
    (터미널 프롬프트 앞에 `(venv)`가 표시되어야 합니다.)

3.  **환경변수 파일 설정**
    `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```powershell
    copy .env.example .env
    ```
    `C:\ai-sandbox` 폴더가 없다면 생성해주세요. 이 폴더는 모든 시스템 명령이 실행될 안전한 공간입니다.
    ```powershell
    mkdir C:\ai-sandbox
    ```

4.  **필요 패키지 설치**
    ```powershell
    pip install -r requirements.txt
    ```

5.  **데이터베이스 초기화**
    `app` 모듈 경로를 기준으로 `init_db` 스크립트를 실행하여 SQLite 데이터베이스와 테이블을 생성합니다.
    ```powershell
    python -m app.db.init_db
    ```
    프로젝트 루트에 `ai_operator.db` 파일이 생성됩니다.

## 3. 실행 방법

아래 명령어를 프로젝트 루트 디렉터리에서 실행하여 Uvicorn 개발 서버를 시작합니다.
`--reload` 플래그는 코드 변경 시 서버를 자동으로 재시작해줍니다.

```powershell
uvicorn app.main:app --reload
```

서버가 정상적으로 실행되면 `http://127.0.0.1:8000` 주소에서 API 요청을 받을 수 있습니다.
API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

## 4. API 사용 예시

### 예시 1: 시스템 작업 요청 및 실행

#### 1) `/chat`으로 작업 요청 (PowerShell)
`dir` 명령어를 `C:\ai-sandbox`에서 실행하도록 요청합니다.

```powershell
$body = @{
    message = "run dir"
    cwd = "." # 샌드박스 루트 기준 상대 경로
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method Post -Body $body -ContentType "application/json"
```

**응답 (예시):**
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
  "approval_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "proposed_command": "dir",
  "response": "I can do that. To proceed with the command 'dir', please confirm by executing the approval request."
}
```

#### 2) `/approvals/{approval_id}/execute`로 작업 승인 및 실행 (PowerShell)
위에서 받은 `approval_id`를 사용하여 작업을 실행합니다.

```powershell
# 위 응답에서 받은 approval_id를 여기에 입력
$approvalId = "a1b2c3d4-e5f6-7890-1234-567890abcdef"

Invoke-RestMethod -Uri "http://127.0.0.1:8000/approvals/$approvalId/execute" -Method Post
```

**응답 (예시):**
```json
{
  "run_id": "z9y8x7w6-v5u4-3210-fedc-ba0987654321",
  "ok": true,
  "stdout": " C 드라이브의 볼륨: Windows
 볼륨 일련 번호: 1234-ABCD

 C:\ai-sandbox 디렉터리

2024-01-01  오후 12:00    <DIR>          .
2024-01-01  오후 12:00    <DIR>          ..
               0개 파일                   0 바이트
               2개 디렉터리  123,456,789,012 바이트 남음
",
  "stderr": "",
  "returncode": 0
}
```

#### curl 사용 예시
```bash
# 1. Chat
curl -X POST "http://127.0.0.1:8000/chat" 
-H "Content-Type: application/json" 
-d '{"message": "run dir", "cwd": "."}'

# 2. Execute
curl -X POST "http://127.0.0.1:8000/approvals/YOUR_APPROVAL_ID/execute"
```

## 5. 보안 제한사항

이 시스템은 잠재적으로 위험한 시스템 명령을 실행할 수 있으므로, 다음과 같은 강력한 보안 정책을 적용합니다.

- **기본 거부 원칙**: 명시적으로 허용되지 않은 모든 작업은 기본적으로 거부됩니다.
- **승인 필수**: 모든 `system_task`는 사용자의 명시적인 승인(`POST /approvals/.../execute`) 없이는 절대 실행되지 않습니다.
- **명령어 화이트리스트**: `app/core/policy.py`에 정의된 접두사로 시작하는 명령어만 허용됩니다. (초기: `git status`, `git diff`, `pytest`, `docker ps`, `dir`)
- **실행 샌드박스**: 모든 명령어는 `.env` 파일에 정의된 `SANDBOX_ROOT`(`C:\ai-sandbox`) 경로 내부에서만 실행될 수 있습니다. 이 경로를 벗어나는 어떠한 작업도 허용되지 않습니다.
- **타임아웃**: 모든 명령어는 120초의 타임아웃이 적용됩니다.
- **출력 길이 제한**: `stdout`과 `stderr`의 최대 길이를 제한하여 과도한 출력으로 인한 문제를 방지합니다.

## 6. 다음 확장 포인트

이 MVP는 다음과 같은 방향으로 확장될 수 있습니다.

- **LLM 연결**: `core/router.py`와 `core/planner.py`의 규칙 기반 로직을 실제 LLM API(예: OpenAI, Anthropic) 호출로 교체하여 더 유연하고 지능적인 의도 분석 및 계획 생성을 구현합니다.
- **RAG (Retrieval-Augmented Generation)**: 벡터 데이터베이스(Chroma, Pinecone 등)를 연동하여 로컬 파일이나 이전 대화 내용을 기반으로 더 정확한 답변을 생성합니다.
- **비동기 작업 큐**: `Celery`나 `FastAPI`의 `BackgroundTasks`를 사용하여 오래 걸리는 작업을 비동기적으로 처리하고, `websockets`으로 클라이언트에 진행 상황을 실시간으로 알립니다.
- **웹 UI**: `React`나 `Vue.js`를 사용하여 사용자가 더 편리하게 상호작용할 수 있는 웹 인터페이스를 구축합니다.
````
