#!/usr/bin/env python3
"""Validate OpenEnv code review environment contract."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code_review_env import Action, CodeReviewEnv


def main() -> int:
    env = CodeReviewEnv(default_task_id="easy")
    obs = env.reset("easy")
    assert obs.task_id == "easy", "reset() must return initial task"

    action = Action(
        task_id="easy",
        action_type="identify_bug",
        payload="Add the missing colon in the for loop to resolve the syntax failure.",
        confidence=0.85,
    )
    next_obs, reward, done, info = env.step(action)

    assert 0.0 <= reward.score <= 1.0, "reward must be normalized"
    assert isinstance(done, bool), "done must be bool"
    assert isinstance(info, dict), "info must be dict"
    _ = next_obs

    print("OpenEnv validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
