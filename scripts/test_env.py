from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.env import CodeReviewOpenEnv
from app.models import Action, Observation, Reward


def _assert_interface() -> None:
    env = CodeReviewOpenEnv(default_task_id="easy")
    obs = env.reset("easy")
    assert isinstance(obs, Observation)

    action = Action(
        task_id="easy",
        action_type="identify_bug",
        payload="The for loop misses a colon and causes syntax failure.",
        confidence=0.8,
    )
    obs2, reward, done, info = env.step(action)
    assert isinstance(obs2, Observation)
    assert isinstance(reward, Reward)
    assert 0.0 <= reward.score <= 1.0
    assert isinstance(done, bool)
    assert isinstance(info, dict)
    assert isinstance(env.state(), dict)


def _assert_all_tasks() -> None:
    for task_id in ["easy", "medium", "hard"]:
        env = CodeReviewOpenEnv(default_task_id=task_id)
        obs = env.reset(task_id)
        assert obs.task_id == task_id
        assert len(obs.required_stages) >= 1


if __name__ == "__main__":
    _assert_interface()
    _assert_all_tasks()
    print("Environment checks passed")
