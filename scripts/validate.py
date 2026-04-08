#!/usr/bin/env python3
"""Validate OpenEnv code review environment contract."""

from code_review_env import Action, CodeReviewEnv


def main() -> int:
    env = CodeReviewEnv()
    obs = env.reset()
    assert obs.current_task, "reset() must return initial task"

    action = Action(
        task_id=obs.current_task["task_id"],
        review_type="bug",
        suggestion="Add missing colon in for-loop and handle syntax error.",
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
