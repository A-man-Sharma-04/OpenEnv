from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import defaultdict, deque
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field, ValidationError, field_validator

from data.mock_diffs import CODE_SNIPPETS, TASK_DEFINITIONS


class TaskType(str, Enum):
    simple_bug = "simple_bug"
    style_issue = "style_issue"
    complex_refactor = "complex_refactor"


class ReviewType(str, Enum):
    bug = "bug"
    style = "style"
    refactor = "refactor"


class Action(BaseModel):
    task_id: TaskType
    review_type: ReviewType = Field(..., description="bug|style|refactor")
    suggestion: str = Field(..., min_length=8, max_length=800)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @field_validator("suggestion")
    @classmethod
    def normalize_suggestion(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            raise ValueError("suggestion cannot be empty")
        return normalized


class Observation(BaseModel):
    code_snippets: List[Dict[str, Any]]
    current_task: Dict[str, Any]
    history: List[Dict[str, Any]] = Field(default_factory=list)
    step_count: int = 0
    remaining_snippets: int = 0


class Reward(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: str
    components: Dict[str, float] = Field(default_factory=dict)


class CodeReviewEnv:
    """Deterministic OpenEnv-compatible environment for code review tasks."""

    _TASK_REVIEW_MAP: Dict[TaskType, ReviewType] = {
        TaskType.simple_bug: ReviewType.bug,
        TaskType.style_issue: ReviewType.style,
        TaskType.complex_refactor: ReviewType.refactor,
    }

    _DESTRUCTIVE_PATTERN = re.compile(
        r"\b(delete\s+table|drop\s+table|truncate|rm\s+-rf|wipe|destroy\s+data|disable\s+tests?)\b",
        flags=re.IGNORECASE,
    )

    def __init__(self, max_steps: int = 12, recent_window: int = 4):
        self.max_steps = max_steps
        self.recent_window = recent_window
        self.code_snippets = list(CODE_SNIPPETS)
        self._state: Dict[str, Any] = {}
        self.reset()

    def reset(self) -> Observation:
        self._state = {
            "current_snippet_idx": 0,
            "history": [],
            "action_hashes": deque(maxlen=16),
            "recent_actions": deque(maxlen=self.recent_window),
            "no_progress_steps": 0,
            "last_total_score": 0.0,
            "per_task_scores": defaultdict(list),
            "penalties": {"repeat": 0.0, "loop": 0.0, "destructive": 0.0},
            "done": False,
        }
        return self._get_observation()

    def state(self) -> Dict[str, Any]:
        snapshot = copy.deepcopy(self._state)
        snapshot["action_hashes"] = list(self._state["action_hashes"])
        snapshot["recent_actions"] = list(self._state["recent_actions"])
        snapshot["per_task_scores"] = {
            str(task): list(scores) for task, scores in self._state["per_task_scores"].items()
        }
        return snapshot

    def step(self, action: Union[Action, Dict[str, Any], str]) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self._state["done"]:
            terminal_reward = Reward(
                score=0.0,
                feedback="Episode already completed. Call reset() before step().",
                components={"base": 0.0, "progress": 0.0, "repeat_penalty": 0.0, "loop_penalty": 0.0, "destructive_penalty": 0.0},
            )
            return self._terminal_observation(), terminal_reward, True, self._build_info("episode_already_done")

        try:
            parsed_action = self._coerce_action(action)
        except (ValidationError, TypeError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                err_msg = exc.errors()[0]["msg"]
            else:
                err_msg = str(exc)
            reward = Reward(
                score=0.0,
                feedback=f"Invalid action payload: {err_msg}",
                components={"base": 0.0, "progress": 0.0, "repeat_penalty": 0.0, "loop_penalty": 0.0, "destructive_penalty": 0.0},
            )
            self._state["no_progress_steps"] += 1
            info = self._build_info("invalid_action")
            return self._get_observation(), reward, False, info

        snippet = self.code_snippets[self._state["current_snippet_idx"]]
        expected_task = TaskType(snippet["task_type"])

        base_score, base_feedback = self._score_action(parsed_action, snippet, expected_task)
        progress_bonus = self._progress_bonus(base_score)
        repeat_penalty = self._repeat_penalty(parsed_action)
        loop_penalty = self._loop_penalty(parsed_action)
        destructive_penalty = self._destructive_penalty(parsed_action)

        total_score = max(0.0, min(1.0, base_score + progress_bonus - repeat_penalty - loop_penalty - destructive_penalty))

        self._state["history"].append(
            {
                "step": len(self._state["history"]),
                "snippet_id": snippet["id"],
                "task_id": parsed_action.task_id.value,
                "action": parsed_action.model_dump(),
                "score": total_score,
                "components": {
                    "base": base_score,
                    "progress": progress_bonus,
                    "repeat_penalty": repeat_penalty,
                    "loop_penalty": loop_penalty,
                    "destructive_penalty": destructive_penalty,
                },
            }
        )

        self._state["per_task_scores"][parsed_action.task_id.value].append(total_score)
        self._state["last_total_score"] = total_score
        self._state["penalties"]["repeat"] += repeat_penalty
        self._state["penalties"]["loop"] += loop_penalty
        self._state["penalties"]["destructive"] += destructive_penalty

        self._state["current_snippet_idx"] += 1
        done = self._state["current_snippet_idx"] >= len(self.code_snippets) or len(self._state["history"]) >= self.max_steps
        self._state["done"] = done

        reward = Reward(
            score=total_score,
            feedback=base_feedback,
            components={
                "base": round(base_score, 4),
                "progress": round(progress_bonus, 4),
                "repeat_penalty": round(repeat_penalty, 4),
                "loop_penalty": round(loop_penalty, 4),
                "destructive_penalty": round(destructive_penalty, 4),
            },
        )
        info = self._build_info("completed" if done else "in_progress")

        if done:
            return self._terminal_observation(), reward, True, info

        return self._get_observation(), reward, False, info

    def _coerce_action(self, action: Union[Action, Dict[str, Any], str]) -> Action:
        if isinstance(action, Action):
            return action
        if isinstance(action, str):
            return Action.model_validate_json(action)
        if isinstance(action, dict):
            return Action.model_validate(action)
        raise TypeError("Action must be Action, dict, or JSON string")

    def _score_action(self, action: Action, snippet: Dict[str, Any], expected_task: TaskType) -> Tuple[float, str]:
        if action.task_id != expected_task:
            return 0.05, f"Task mismatch: expected {expected_task.value}, received {action.task_id.value}"

        expected_review = self._TASK_REVIEW_MAP[expected_task]
        review_match_bonus = 0.1 if action.review_type == expected_review else 0.0

        suggestion_lower = action.suggestion.lower()
        keyword_hits = sum(1 for kw in snippet.get("expected_keywords", []) if kw.lower() in suggestion_lower)
        anti_pattern_hits = sum(1 for kw in snippet.get("anti_patterns", []) if kw.lower() in suggestion_lower)

        keyword_score = min(0.75, keyword_hits * 0.2)
        confidence_alignment = (1.0 - abs(0.75 - action.confidence)) * 0.15
        anti_pattern_penalty = min(0.2, anti_pattern_hits * 0.1)

        base = max(0.0, keyword_score + review_match_bonus + confidence_alignment - anti_pattern_penalty)

        feedback = (
            f"{snippet['title']}: keyword_hits={keyword_hits}, "
            f"review_match={'yes' if review_match_bonus > 0 else 'no'}, anti_patterns={anti_pattern_hits}"
        )
        return min(1.0, base), feedback

    def _progress_bonus(self, new_score: float) -> float:
        if new_score > self._state["last_total_score"] + 0.1:
            self._state["no_progress_steps"] = 0
            return 0.08
        self._state["no_progress_steps"] += 1
        return 0.0

    def _repeat_penalty(self, action: Action) -> float:
        serialized = json.dumps(action.model_dump(), sort_keys=True, separators=(",", ":"))
        action_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        penalty = 0.0
        if action_hash in self._state["action_hashes"]:
            penalty = 0.08
        self._state["action_hashes"].append(action_hash)
        return penalty

    def _loop_penalty(self, action: Action) -> float:
        signature = f"{action.task_id.value}|{action.review_type.value}|{action.suggestion.lower()}"
        self._state["recent_actions"].append(signature)

        penalty = 0.0
        recent = list(self._state["recent_actions"])
        if len(recent) >= 3 and len(set(recent[-3:])) == 1:
            penalty += 0.15
        if self._state["no_progress_steps"] >= 3:
            penalty += 0.12
        return penalty

    def _destructive_penalty(self, action: Action) -> float:
        if self._DESTRUCTIVE_PATTERN.search(action.suggestion):
            return 0.25
        return 0.0

    def _task_metrics(self) -> Dict[str, Dict[str, float]]:
        metrics: Dict[str, Dict[str, float]] = {}
        for task_id, scores in self._state["per_task_scores"].items():
            if not scores:
                continue
            avg_score = sum(scores) / len(scores)
            metrics[task_id] = {
                "attempts": float(len(scores)),
                "avg_score": round(avg_score, 4),
                "max_score": round(max(scores), 4),
            }
        return metrics

    def _build_info(self, status: str) -> Dict[str, Any]:
        return {
            "status": status,
            "step": len(self._state["history"]),
            "max_steps": self.max_steps,
            "remaining_snippets": max(0, len(self.code_snippets) - self._state["current_snippet_idx"]),
            "penalties": {
                "repeat": round(self._state["penalties"]["repeat"], 4),
                "loop": round(self._state["penalties"]["loop"], 4),
                "destructive": round(self._state["penalties"]["destructive"], 4),
            },
            "task_metrics": self._task_metrics(),
        }

    def _get_observation(self) -> Observation:
        idx = self._state["current_snippet_idx"]
        snippet = self.code_snippets[idx]
        task_meta = TASK_DEFINITIONS[snippet["task_type"]]
        return Observation(
            code_snippets=[
                {
                    "id": snippet["id"],
                    "title": snippet["title"],
                    "task_type": snippet["task_type"],
                    "code": snippet["code"],
                    "difficulty": task_meta["difficulty"],
                    "objective": task_meta["objective"],
                }
            ],
            current_task={
                "task_id": snippet["task_type"],
                "difficulty": task_meta["difficulty"],
                "objective": task_meta["objective"],
                "step": len(self._state["history"]),
            },
            history=list(self._state["history"]),
            step_count=len(self._state["history"]),
            remaining_snippets=max(0, len(self.code_snippets) - idx - 1),
        )

    def _terminal_observation(self) -> Observation:
        return Observation(
            code_snippets=[],
            current_task={},
            history=list(self._state["history"]),
            step_count=len(self._state["history"]),
            remaining_snippets=0,
        )

    def task_catalog(self) -> Dict[str, Dict[str, str]]:
        return copy.deepcopy(TASK_DEFINITIONS)

    def action_schema(self) -> Dict[str, Any]:
        return Action.model_json_schema()

    def observation_schema(self) -> Dict[str, Any]:
        return Observation.model_json_schema()

    def reward_schema(self) -> Dict[str, Any]:
        return Reward.model_json_schema()
