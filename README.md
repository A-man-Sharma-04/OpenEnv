---
title: OpenEnv Code Review
emoji: robot
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

## OpenEnv Code Review Environment

Deterministic OpenEnv-compatible environment for evaluating AI code reviewers on realistic software engineering tasks.

## Overview

This repository implements a strict, production-oriented environment where an agent reviews Python code snippets and proposes fixes or refactors. The core environment is deterministic, reward shaping is step-aware, and the inference path uses Groq for live model calls.

## System Architecture

- Core environment: `code_review_env.py`
- Task fixtures: `data/mock_diffs.py`
- Deterministic reward shaping: `code_review_env.py`
- Shared LLM provider layer: `llm/provider.py`
- Groq-powered inference script: `inference.py`
- FastAPI app and frontend: `api/app.py`, `api/templates/index.html`, `api/static/`
- Evaluation pipeline: `evaluation/runner.py`
- Validation: `validate.py`, `tests/test_platform.py`

## OpenEnv Contract

`CodeReviewEnv` exposes the expected interface:

- `reset() -> Observation`
- `step(action) -> (Observation, Reward, done, info)`
- `state() -> Dict[str, Any]`

The environment is deterministic and uses incremental rewards with explicit penalties for repetition, looping, and destructive suggestions.

### Action Schema

- `task_id`: `simple_bug`, `style_issue`, or `complex_refactor`
- `review_type`: `bug`, `style`, or `refactor`
- `suggestion`: natural-language recommendation
- `confidence`: float in `[0.0, 1.0]`

### Reward Design

Reward values are normalized to `[0.0, 1.0]` and combine:

- Base task alignment score
- Progress bonus for meaningful improvement
- Repeat penalty for duplicate actions
- Loop penalty for repeated no-progress behavior
- Destructive penalty for unsafe suggestions

## Groq Integration

The project uses Groq for any live LLM-backed operation.

- Provider: `Groq` from the official Python SDK
- Default model: `llama-3.1-8b-instant`
- Environment variable: `GROQ_API_KEY`

If `GROQ_API_KEY` is missing, the API and demo fall back to the deterministic mock provider. The inference script requires the key and exits with a clear error if it is missing.

## Setup

### Local Development

```bash
pip install -r requirements.txt
python validate.py
python -m pytest tests/test_platform.py
```

### Run the API

```bash
e:/Projects/OpenEnv/.venv/Scripts/python.exe api/app.py
```

Then open `http://127.0.0.1:8000`.

### Run Groq Inference

```bash
set GROQ_API_KEY=gsk_xxx
set GROQ_MODEL=llama-3.1-8b-instant
python inference.py
```

The script emits the required markers in stdout:

- `[START]`
- `[STEP]`
- `[END]`

## Frontend

The web UI supports:

- Task creation
- Evaluation starts
- Status polling
- Leaderboard retrieval
- Health checks

It includes loading states, error feedback, and responsive layout behavior for smaller screens.

## Docker

```bash
docker build -t openenv-code-review .
docker run --rm -p 8000:8000 openenv-code-review
```

## Validation

Recommended checks before submission:

```bash
python validate.py
python -m pytest tests/test_platform.py
python inference.py
```

## Notes

- The environment is intentionally deterministic to support reproducible hackathon scoring.
- `data/mock_diffs.py` contains the curated task snippets used by the code review environment.
- `openenv.yaml` describes the environment entrypoint, schema types, and inference output markers.
