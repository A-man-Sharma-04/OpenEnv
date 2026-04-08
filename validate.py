#!/usr/bin/env python3
"""Repository validation for OpenEnv hackathon compliance-critical checks."""

import json
from pathlib import Path

from code_review_env import Action, CodeReviewEnv


def validate_environment_interface() -> None:
    env = CodeReviewEnv()
    obs = env.reset()
    assert hasattr(env, "step") and callable(env.step)
    assert hasattr(env, "reset") and callable(env.reset)
    assert hasattr(env, "state") and callable(env.state)

    action = Action(
        task_id=obs.current_task["task_id"],
        review_type="bug",
        suggestion="Fix syntax by adding the missing colon in the loop header.",
        confidence=0.8,
    )
    _, reward, done, info = env.step(action)
    assert 0.0 <= reward.score <= 1.0
    assert isinstance(done, bool)
    assert isinstance(info, dict)


def validate_openenv_yaml() -> None:
    config_path = Path("openenv.yaml")
    assert config_path.exists(), "openenv.yaml must exist"
    text = config_path.read_text(encoding="utf-8")
    for required_key in ["tasks:", "entrypoint:", "schemas:"]:
        assert required_key in text, f"Missing key in openenv.yaml: {required_key}"


def validate_inference_markers() -> None:
    inference = Path("inference.py").read_text(encoding="utf-8")
    for marker in ["[START]", "[STEP]", "[END]"]:
        assert marker in inference, f"Missing inference marker {marker}"


def main() -> int:
    validate_environment_interface()
    validate_openenv_yaml()
    validate_inference_markers()
    print(json.dumps({"status": "ok", "checks": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
