from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class RewardConfig:
    stage_weight: float = 0.70
    progress_bonus: float = 0.20
    confidence_bonus_cap: float = 0.05
    invalid_action_penalty: float = 0.25
    loop_penalty: float = 0.12
    destructive_penalty: float = 0.30
    max_reward: float = 1.0


MAX_STEPS_BY_TASK: Dict[str, int] = {
    "easy": 3,
    "medium": 6,
    "hard": 9,
}


TASK_IDS: List[str] = ["easy", "medium", "hard"]
