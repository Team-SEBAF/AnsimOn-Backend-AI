# AnsimOn Backend AI

이 프로젝트는 **AI Worker**(백그라운드 태스크 처리)와 **SSE**(진행률 스트리밍) 두 가지 서비스를 담당합니다. [AnsimOn-Backend](https://github.com/Team-SEBAF/AnsimOn-Backend)와 연동되며(DB 설정, 마이그레이션, 스키마는 해당 레포 참고), AI 모듈은 [AnsimOn-AI](https://github.com/Team-SEBAF/AnsimOn-AI)에서 클론합니다.

---

## 1. 사전 준비 및 설치

### Poetry 설치

이 프로젝트는 의존성 및 가상환경 관리를 위해 **Poetry**를 사용합니다.

**macOS / Linux**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

설치 후 `poetry`를 찾을 수 없다면 PATH에 추가:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Windows (PowerShell)**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

확인:

```bash
poetry --version
```

### 의존성 설치

프로젝트 루트에서:

```bash
# SSE만
poetry install

# 전체 (AI Worker + SSE)
poetry install -E worker
```

Poetry가 가상환경을 만듭니다. `worker` extra는 AI 의존성(openai, pytesseract 등)을 추가합니다.

---

## 2. AI Worker

### 기술 스택

| 구분       | 기술              |
| ---------- | ----------------- |
| 태스크 큐  | AWS SQS           |
| 배포       | AWS ECS Fargate   |
| ORM        | SQLAlchemy        |

### AI 모듈 클론

```bash
./scripts/clone_ai.sh
```

[AnsimOn-AI](https://github.com/Team-SEBAF/AnsimOn-AI)를 프로젝트 내 지정 위치에 클론합니다.

### 로컬 실행

```bash
poetry run python -m worker.main
```

SQS를 폴링하여 timeline/document 태스크를 처리하고 DB를 갱신합니다. `DATABASE_URL`, `SQS_QUEUE_URL`(또는 AWS 설정)이 필요합니다.

---

## 3. SSE (진행률 스트리밍)

### 기술 스택

| 구분       | 기술       |
| ---------- | ---------- |
| 프레임워크 | FastAPI    |
| 배포       | AWS Lambda |

### 로컬 실행

```bash
poetry run uvicorn sse.main:app --reload --port 8001
```

- 접속 URL: http://localhost:8001
- `--reload`: 코드 변경 시 서버 자동 재시작

### 스트리밍 확인

```bash
curl -N http://localhost:8001/timeline/{task_id}/progress
```

`{task_id}` 자리에 유효한 task UUID를 넣습니다. 이벤트: `evidence_collecting`, `progress`, `done`.
