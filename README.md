# AnsimOn Backend AI

This project runs two services: **AI Worker** (background task processing) and **SSE** (Server-Sent Events for progress streaming). It integrates with [AnsimOn-Backend](https://github.com/Team-SEBAF/AnsimOn-Backend) (for database setup, migrations, and schema, see that repository) and uses the AI module cloned from [AnsimOn-AI](https://github.com/Team-SEBAF/AnsimOn-AI).

---

## 1. Prerequisites & Setup

### Installing Poetry

This project uses **Poetry** for dependency and virtual environment management.

**macOS / Linux**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

If `poetry` is not found after installation, add it to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Windows (PowerShell)**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Verify:

```bash
poetry --version
```

### Installing Dependencies

At the project root:

```bash
# SSE only
poetry install

# Full (AI Worker + SSE)
poetry install -E worker
```

Poetry creates and manages the virtual environment. The `worker` extra adds AI dependencies (openai, pytesseract, etc.).

---

## 2. AI Worker

### Tech Stack

| Category   | Technology    |
| ---------- | ------------- |
| Task Queue | AWS SQS       |
| Deployment | AWS ECS Fargate |
| ORM        | SQLAlchemy    |

### Clone AI Module

```bash
./scripts/clone_ai.sh
```

Clones [AnsimOn-AI](https://github.com/Team-SEBAF/AnsimOn-AI) into the expected location.

### Run Locally

```bash
poetry run python -m worker.main
```

Polls SQS, processes timeline/document tasks, and updates the database. Requires `DATABASE_URL` and `SQS_QUEUE_URL` (or AWS config).

---

## 3. SSE (Progress Streaming)

### Tech Stack

| Category   | Technology |
| ---------- | ---------- |
| Framework  | FastAPI    |
| Deployment | AWS Lambda |

### Run Locally

```bash
poetry run uvicorn sse.main:app --reload --port 8001
```

- URL: http://localhost:8001
- `--reload`: auto-restart on code changes

### Verify Streaming

```bash
curl -N http://localhost:8001/timeline/{task_id}/progress
```

Replace `{task_id}` with a valid task UUID. Events: `evidence_collecting`, `progress`, `done`.
