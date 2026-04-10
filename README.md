---
title: OpenEnv Code Review
emoji: 🧪
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# OpenEnv Code Review Environment

Production-style OpenEnv benchmark for deterministic code review workflows.

## At a Glance

| Area | Details |
|---|---|
| Focus | Code review and incident triage simulation |
| Difficulties | `easy`, `medium`, `hard` |
| API Port | `7860` |
| Primary API | FastAPI (`api/app.py`) |
| Frontend | Static dashboard (`index.html`, `style.css`, `script.js`) |

## Why This Project

This environment models realistic review tasks in three stages:

- `easy`: find a syntax bug and apply a safe direct fix
- `medium`: identify maintainability risks and propose a non-breaking refactor
- `hard`: triage production risks, define a fix plan, and define a test plan

Core OpenEnv methods:

- `reset(task_id)`
- `step(action)`
- `state()`

## Quick Start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Start the API

```bash
uvicorn api.app:app --host 127.0.0.1 --port 7860
```

Open: `http://127.0.0.1:7860` (or `http://localhost:7860`)

Note: do not use `http://0.0.0.0:7860` in a browser.

### 3) Run validation and tests

```bash
python validate.py
pytest -q tests
```

### 4) (Optional) Open frontend dashboard

```bash
start index.html
```

Default API base URL in the dashboard is `http://localhost:7860`.

## API Overview

### Endpoints

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /health`

### Example request

```bash
curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{"task_id":"easy"}'
```

## Environment Models

### Action Space

Pydantic model: `env.models.Action`

- `task_id: str` (`easy|medium|hard`)
- `action_type: str` (must match required stage)
- `payload: str` (analysis/fix text)
- `confidence: float` (`0.0..1.0`)

### Observation Space

Pydantic model: `env.models.Observation`

- `task_id`
- `difficulty`
- `objective`
- `ticket`
- `available_actions`
- `required_stages`
- `completed_stages`
- `step_count`
- `remaining_steps`
- `history`

### Reward Model

Pydantic model: `env.models.Reward`

Reward is deterministic, emitted on every step, and clamped to `0.0..1.0`.

Includes:

- intermediate progress rewards
- penalties for loops and no-progress behavior
- penalties for redundant/invalid actions
- penalties for destructive behavior signals

## Tasks and Graders

Deterministic datasets + graders:

- `data/easy_cases.json` + `tasks/graders/easy_grader.py`
- `data/medium_cases.json` + `tasks/graders/medium_grader.py`
- `data/hard_cases.json` + `tasks/graders/hard_grader.py`

All graders return scores in `0.0..1.0`.

## Inference

Entrypoint: `inference.py`

Required environment variables:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`

Strict log format:

- `[START]`
- `task: <task_name>`
- `[STEP]`
- `action: <action>`
- `reward: <reward>`
- `[END]`
- `score: <final_score>`

```bash
python inference.py
```

## Windows Runner

Use `run_all.bat` to run common workflows from project root.

```bat
.\run_all.bat all
```

Modes:

- `all`: validate + tests + start API + inference
- `validate`: run `validate.py`
- `tests`: run `pytest -q tests`
- `api`: start API server only
- `inference`: run inference only
- `help`: show usage

Examples:

```bat
.\run_all.bat validate
.\run_all.bat tests
.\run_all.bat api
.\run_all.bat inference
.\run_all.bat help
```

## Docker / Hugging Face Spaces

```bash
docker build -t openenv-code-review .
docker run --rm -p 7860:7860 openenv-code-review
```

Container serves on port `7860` and is compatible with Hugging Face Docker Spaces.

## Space Metadata (Important)

This README uses static YAML frontmatter for Hugging Face Spaces.
Use concrete values only. Do not use template placeholders like `{{title}}` or conditional blocks.

Current Space config:

```yaml
title: OpenEnv Code Review
emoji: "\U0001F9EA"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
```

If you switch to Gradio Space metadata:

- `sdk: gradio`
- `app_file: app.py`
- optional `python_version: "3.10"` (or your target runtime)

## Project Structure

```text
OpenEnv/
  env/
  tasks/
    graders/
  data/
  api/
  index.html
  style.css
  script.js
  run_all.bat
  inference.py
  openenv.yaml
  Dockerfile
  requirements.txt
  README.md
```
