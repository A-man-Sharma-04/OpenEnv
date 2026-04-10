from __future__ import annotations

from threading import Lock
from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel

from env.environment import CodeReviewEnv


app = FastAPI(
    title="OpenEnv Code Review API",
    description="Minimal OpenEnv runtime with deterministic staged code-review tasks.",
    version="1.0.0",
)

env = CodeReviewEnv(default_task_id="easy")
env_lock = Lock()


class ResetRequest(BaseModel):
    task_id: str | None = None


@app.post("/reset", response_model=Dict[str, Any])
async def reset_openenv(payload: ResetRequest | None = None):
    task_id = payload.task_id if payload else None
    try:
        with env_lock:
            obs = env.reset(task_id)
        return obs.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/step", response_model=Dict[str, Any])
async def step_openenv(payload: Dict[str, Any] = Body(...)):
    action_payload = payload.get("action", payload)
    try:
        with env_lock:
            obs, reward, done, info = env.step(action_payload)
        return {
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/state", response_model=Dict[str, Any])
async def state_openenv():
    with env_lock:
        return env.state()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}
