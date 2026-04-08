from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator


class Observation(BaseModel):
    task_id: str
    difficulty: str
    objective: str
    ticket: Dict[str, Any]
    available_actions: List[str]
    required_stages: List[str]
    completed_stages: List[str] = Field(default_factory=list)
    step_count: int = 0
    remaining_steps: int = 0
    history: List[Dict[str, Any]] = Field(default_factory=list)


class Action(BaseModel):
    task_id: str
    action_type: str = Field(..., description="One of the required workflow stages")
    payload: str = Field(..., min_length=8, max_length=2000)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

    @field_validator("payload")
    @classmethod
    def normalize_payload(cls, value: str) -> str:
        return " ".join(value.split())


class Reward(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    components: Dict[str, float] = Field(default_factory=dict)
