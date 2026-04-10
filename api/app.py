from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from env.environment import CodeReviewEnv


app = FastAPI(
    title="OpenEnv Code Review API",
    description="Minimal OpenEnv runtime with deterministic staged code-review tasks.",
    version="1.0.0",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = PROJECT_ROOT / "index.html"
SCRIPT_FILE = PROJECT_ROOT / "script.js"
STYLE_FILE = PROJECT_ROOT / "style.css"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = CodeReviewEnv(default_task_id="easy")
env_lock = Lock()


class ResetRequest(BaseModel):
    task_id: str | None = None


class StepRequest(BaseModel):
    action: Dict[str, Any] | None = None
    task_id: str | None = None
    action_type: str | None = None
    payload: str | None = None
    confidence: float | None = None


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
async def step_openenv(payload: StepRequest = Body(...)):
    data = payload.model_dump(exclude_none=True)
    action_payload = data.get("action") or data
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


@app.get("/")
async def root():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return {
        "service": "OpenEnv Code Review API",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "state": "/state",
        "reset": "/reset",
        "step": "/step",
    }


@app.get("/index.html")
async def index_html():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_FILE)


@app.get("/script.js")
async def script_js():
    if not SCRIPT_FILE.exists():
        raise HTTPException(status_code=404, detail="script.js not found")
    return FileResponse(SCRIPT_FILE, media_type="application/javascript")


@app.get("/style.css")
async def style_css():
    if not STYLE_FILE.exists():
        raise HTTPException(status_code=404, detail="style.css not found")
    return FileResponse(STYLE_FILE, media_type="text/css")
