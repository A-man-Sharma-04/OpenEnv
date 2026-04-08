---
title: OpenEnv Code Review Workflows
emoji: "🤖"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
- openenv
- code-review
pinned: false
---

## OpenEnv Code Review Workflows

Production-style OpenEnv environment for deterministic code-review workflows with staged actions, per-step rewards, and API-first execution.

## What This Project Provides

- 3 tasks: easy, medium, hard
- Typed OpenEnv models: Observation, Action, Reward
- Deterministic scoring in the range [0.0, 1.0]
- Runtime API endpoints for OpenEnv checks:
  - POST /reset
  - POST /step
  - GET /state
- Root inference script at inference.py that reads HF_TOKEN and outputs task scores

## Functional Coverage

- Real-world domain: code review incident handling
- Exactly 3 tasks: easy, medium, hard
- Pydantic models: Observation, Action, Reward
- OpenEnv methods: reset(), step(), state()
- Deterministic graders with score range [0.0, 1.0]
- Reward at every step with progress rewards and penalties
- Inference script reads HF_TOKEN

## Project Structure

- app/
  - env.py
  - models.py
  - rewards.py
  - utils.py
  - config.py
- tasks/
  - task_base.py
  - easy_task.py
  - medium_task.py
  - hard_task.py
- graders/
  - easy_grader.py
  - medium_grader.py
  - hard_grader.py
- data/
  - easy_cases.json
  - medium_cases.json
  - hard_cases.json
- scripts/
  - run_baseline.py
  - evaluate.py
  - test_env.py
- api/
  - app.py
- openenv.yaml
- Dockerfile
- requirements.txt
- app.py
- inference.py
- validate.py

## Reward Design

Per-step reward is deterministic and uses:

- Base stage quality score
- Progress bonus when a required stage is completed
- Confidence alignment bonus
- Invalid action penalty
- Loop/no-progress penalty
- Destructive behavior penalty

Total reward is clamped to [0.0, 1.0].

## Local Setup

```bash
pip install -r requirements.txt
```

## Run API (Required OpenEnv Command)

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

## API Contract

### POST /reset

Resets the environment and returns the initial observation.

Request body (optional):

```json
{
  "task_id": "easy"
}
```

### POST /step

Applies one action and returns the transition payload:

```json
{
  "observation": {"...": "..."},
  "reward": {"score": 0.0, "feedback": "...", "components": {}},
  "done": false,
  "info": {}
}
```

Request body supports either direct action payload or wrapped action:

```json
{
  "action": {
    "task_id": "easy",
    "action_type": "identify_bug",
    "payload": "The loop header is missing a colon.",
    "confidence": 0.85
  }
}
```

### GET /state

Returns the current internal environment state snapshot.

## Endpoint Smoke Tests

```bash
curl -X POST "http://127.0.0.1:7860/reset" \
  -H "Content-Type: application/json" \
  -d '{"task_id":"easy"}'

curl -X POST "http://127.0.0.1:7860/step" \
  -H "Content-Type: application/json" \
  -d '{"action":{"task_id":"easy","action_type":"identify_bug","payload":"The loop header is missing a colon, causing syntax failure before execution.","confidence":0.85}}'

curl "http://127.0.0.1:7860/state"
```

## Validation and Tests

```bash
python scripts/test_env.py
python validate.py
pytest -q
```

## Inference (Mandatory Root Script)

Set environment variables:

```bash
set HF_TOKEN=your_api_key
python inference.py
```

Example output:

```text
[START]
[STEP]
easy: 0.945
[STEP]
medium: 0.137
[STEP]
hard: 0.109
[END]
{"scores":{"easy":0.945,"medium":0.137,"hard":0.109},"average":0.397}
```

## Docker

```bash
docker build -t openenv-code-review-workflows .
docker run --rm -p 7860:7860 openenv-code-review-workflows
```

The service listens on port 7860 and exposes /health for liveness checks.
