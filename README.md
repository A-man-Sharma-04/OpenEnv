# OpenEnv Code Review Environment

Minimal, production-ready OpenEnv project for real-world code review workflows.

## Description

This environment simulates production incident code review work in three deterministic stages:

- easy: identify a syntax bug and provide a safe direct fix
- medium: identify style and maintainability risks, then propose a non-breaking refactor
- hard: triage production risks, define a fix plan, and define a test plan

The environment exposes required OpenEnv methods:

- `reset(task_id)`
- `step(action)`
- `state()`

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

## Action Space

Pydantic model: `env.models.Action`

- `task_id: str` (`easy|medium|hard`)
- `action_type: str` (must match required stage)
- `payload: str` (analysis/fix text)
- `confidence: float` (`0.0..1.0`)

## Observation Space

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

## Reward Model

Pydantic model: `env.models.Reward`

Reward is deterministic, emitted on every step, and clamped to `0.0..1.0`.

Includes:

- intermediate progress rewards
- penalties for loops and no-progress behavior
- penalties for redundant/invalid actions
- penalties for destructive behavior signals

## Tasks

Datasets and deterministic graders:

- `data/easy_cases.json` + `tasks/graders/easy_grader.py`
- `data/medium_cases.json` + `tasks/graders/medium_grader.py`
- `data/hard_cases.json` + `tasks/graders/hard_grader.py`

All graders return scores in `0.0..1.0`.

## Setup

```bash
pip install -r requirements.txt
```

## Frontend Dashboard

Minimal static frontend files:

- `index.html`
- `style.css`
- `script.js`

Open directly in a browser:

```bash
start index.html
```

Default API base URL in the UI is `http://localhost:7860` and can be changed from the dashboard.

## Run API

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

Endpoints:

- `POST /reset`
- `POST /step`
- `GET /state`
- `GET /health`

Example:

```bash
curl -X POST http://127.0.0.1:7860/reset -H "Content-Type: application/json" -d '{"task_id":"easy"}'
```

## Inference Script

Root inference entrypoint: `inference.py`

Reads required environment variables:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`

Emits strict logs using only:

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

## Validation

```bash
python validate.py
pytest -q tests
```

## Windows Batch Runner

Use `run_all.bat` from the project root to run common workflows.

Important: run the batch file itself, not just `all`.

```bat
.\run_all.bat all
```

Available modes:

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
