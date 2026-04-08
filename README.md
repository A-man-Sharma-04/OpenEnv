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

Production-style OpenEnv environment that simulates real code-review workflows with deterministic scoring and step-wise rewards.

## Functional Coverage

- Real-world domain: code review incident handling
- Exactly 3 tasks: easy, medium, hard
- Pydantic models: Observation, Action, Reward
- OpenEnv methods: reset(), step(), state()
- Deterministic graders with score range [0.0, 1.0]
- Reward at every step with progress rewards and penalties
- Baseline inference script using OpenAI-compatible API with HF_TOKEN

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
- openenv.yaml
- Dockerfile
- requirements.txt
- app.py

## Reward Design

Per-step reward is deterministic and uses:

- Base stage quality score
- Progress bonus when a required stage is completed
- Confidence alignment bonus
- Invalid action penalty
- Loop/no-progress penalty
- Destructive behavior penalty

Total reward is clamped to [0.0, 1.0].

## Quick Start

```bash
pip install -r requirements.txt
python scripts/test_env.py
python validate.py
```

## Baseline Inference

Set environment variables:

```bash
set HF_TOKEN=your_api_key
set OPENAI_MODEL=gpt-4o-mini
set OPENAI_BASE_URL=https://api.openai.com/v1
python scripts/run_baseline.py
```

Example output:

```text
Easy: 0.85
Medium: 0.60
Hard: 0.40
```

## Docker

```bash
docker build -t openenv-code-review-workflows .
docker run --rm -p 7860:7860 openenv-code-review-workflows
```

The API health endpoint is available at /health.
