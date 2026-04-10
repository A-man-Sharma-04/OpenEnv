from __future__ import annotations

import copy
import json
from collections import deque
from typing import Any, Deque, Dict, Tuple, Union

from pydantic import ValidationError

from env.config import MAX_STEPS_BY_TASK, TASK_IDS
from env.models import Action, Observation, Reward
from env.rewards import compose_reward, finalize_reward
from env.utils import has_destructive_content
from tasks.easy_task import EASY_TASK
from tasks.hard_task import HARD_TASK
from tasks.medium_task import MEDIUM_TASK


TASK_REGISTRY = {
    "easy": EASY_TASK,
    "medium": MEDIUM_TASK,
    "hard": HARD_TASK,
}


class CodeReviewEnv:
    """OpenEnv environment for realistic code review workflows."""

    def __init__(self, default_task_id: str = "easy"):
        if default_task_id not in TASK_IDS:
            raise ValueError(f"Unknown task_id: {default_task_id}")
        self.default_task_id = default_task_id
        self._state: Dict[str, Any] = {}
        self.reset(default_task_id)

    def reset(self, task_id: str | None = None) -> Observation:
        selected = task_id or self.default_task_id
        if selected not in TASK_REGISTRY:
            raise ValueError(f"Unsupported task_id: {selected}")

        task = TASK_REGISTRY[selected]
        ticket = copy.deepcopy(task.dataset[0])
        self._state = {
            "task_id": selected,
            "task": task,
            "ticket": ticket,
            "step_count": 0,
            "max_steps": MAX_STEPS_BY_TASK[selected],
            "history": [],
            "completed_stages": [],
            "done": False,
            "recent_signatures": deque(maxlen=4),
            "no_progress_steps": 0,
        }
        return self._observation()

    def state(self) -> Dict[str, Any]:
        snapshot = copy.deepcopy(self._state)
        if isinstance(snapshot.get("recent_signatures"), deque):
            snapshot["recent_signatures"] = list(snapshot["recent_signatures"])
        snapshot["task"] = snapshot["task"].as_dict()
        return snapshot

    def step(self, action: Union[Action, Dict[str, Any], str]) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self._state["done"]:
            reward = Reward(score=0.0, feedback="Episode already done. Call reset() before step().")
            return self._terminal_observation(), reward, True, {"status": "episode_already_done"}

        parsed, invalid_reason = self._coerce_action(action)
        self._state["step_count"] += 1

        invalid = invalid_reason is not None
        stage_score = 0.0
        stage_feedback = invalid_reason or ""
        completed_new_stage = False

        if parsed is not None:
            stage_score, stage_feedback, completed_new_stage = self._grade_and_update(parsed)

        looping = self._is_loop(parsed)
        destructive = has_destructive_content(parsed.payload if parsed else "")
        breakdown = compose_reward(
            score=stage_score,
            completed_new_stage=completed_new_stage,
            confidence=parsed.confidence if parsed else 0.0,
            invalid=invalid,
            looping=looping,
            destructive=destructive,
        )
        total = finalize_reward(breakdown)

        self._state["history"].append(
            {
                "step": self._state["step_count"],
                "action": parsed.model_dump() if parsed else None,
                "feedback": stage_feedback,
                "stage_score": stage_score,
                "reward": total,
            }
        )

        done = self._compute_done()
        self._state["done"] = done
        reward = Reward(
            score=total,
            feedback=stage_feedback,
            components={
                "base": round(breakdown.base, 4),
                "progress": round(breakdown.progress, 4),
                "confidence": round(breakdown.confidence, 4),
                "invalid_penalty": round(breakdown.invalid_penalty, 4),
                "loop_penalty": round(breakdown.loop_penalty, 4),
                "destructive_penalty": round(breakdown.destructive_penalty, 4),
            },
        )
        info = {
            "status": "completed" if done else "in_progress",
            "step": self._state["step_count"],
            "max_steps": self._state["max_steps"],
            "task_id": self._state["task_id"],
            "completed_stages": list(self._state["completed_stages"]),
            "required_stages": list(self._state["task"].required_stages),
        }

        if done:
            return self._terminal_observation(), reward, True, info
        return self._observation(), reward, False, info

    def _coerce_action(self, action: Union[Action, Dict[str, Any], str]) -> Tuple[Action | None, str | None]:
        try:
            if isinstance(action, Action):
                parsed = action
            elif isinstance(action, dict):
                parsed = Action.model_validate(action)
            elif isinstance(action, str):
                parsed = Action.model_validate_json(action)
            else:
                return None, "Invalid action type; expected Action, dict, or JSON string."
        except (ValidationError, ValueError) as exc:
            return None, f"Invalid action payload: {exc}"

        if parsed.task_id != self._state["task_id"]:
            return None, f"Task mismatch: expected {self._state['task_id']} but got {parsed.task_id}."

        return parsed, None

    def _grade_and_update(self, action: Action) -> Tuple[float, str, bool]:
        task = self._state["task"]
        if action.action_type not in task.required_stages:
            self._state["no_progress_steps"] += 1
            return 0.0, f"Invalid stage '{action.action_type}' for task '{task.task_id}'.", False

        if action.action_type in self._state["completed_stages"]:
            self._state["no_progress_steps"] += 1
            return 0.0, f"Stage '{action.action_type}' already completed.", False

        expected_stage = task.required_stages[len(self._state["completed_stages"])]
        if action.action_type != expected_stage:
            self._state["no_progress_steps"] += 1
            return 0.0, f"Stages must be completed in order. Expected '{expected_stage}'.", False

        score, feedback = task.grader(action.payload, self._state["ticket"], action.action_type)
        completed = score >= 0.80
        if completed:
            self._state["completed_stages"].append(action.action_type)
            self._state["no_progress_steps"] = 0
        else:
            self._state["no_progress_steps"] += 1
        return score, feedback, completed

    def _is_loop(self, action: Action | None) -> bool:
        if action is None:
            return self._state["no_progress_steps"] >= 2

        signature = json.dumps(
            {"action_type": action.action_type, "payload": action.payload.lower()},
            sort_keys=True,
            separators=(",", ":"),
        )
        self._state["recent_signatures"].append(signature)

        recent = list(self._state["recent_signatures"])
        repeated = len(recent) >= 3 and len(set(recent[-3:])) == 1
        no_progress_loop = self._state["no_progress_steps"] >= 2
        return repeated or no_progress_loop

    def _compute_done(self) -> bool:
        all_stages_done = len(self._state["completed_stages"]) == len(self._state["task"].required_stages)
        max_steps_reached = self._state["step_count"] >= self._state["max_steps"]
        return all_stages_done or max_steps_reached

    def _observation(self) -> Observation:
        task = self._state["task"]
        remaining = max(0, self._state["max_steps"] - self._state["step_count"])
        return Observation(
            task_id=task.task_id,
            difficulty=task.difficulty,
            objective=task.objective,
            ticket=copy.deepcopy(self._state["ticket"]),
            available_actions=list(task.required_stages),
            required_stages=list(task.required_stages),
            completed_stages=list(self._state["completed_stages"]),
            step_count=self._state["step_count"],
            remaining_steps=remaining,
            history=copy.deepcopy(self._state["history"]),
        )

    def _terminal_observation(self) -> Observation:
        task = self._state["task"]
        return Observation(
            task_id=task.task_id,
            difficulty=task.difficulty,
            objective=task.objective,
            ticket=copy.deepcopy(self._state["ticket"]),
            available_actions=[],
            required_stages=list(task.required_stages),
            completed_stages=list(self._state["completed_stages"]),
            step_count=self._state["step_count"],
            remaining_steps=0,
            history=copy.deepcopy(self._state["history"]),
        )
