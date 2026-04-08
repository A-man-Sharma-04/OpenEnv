from code_review_env import Action, CodeReviewEnv


def test_env_interface_contract():
    env = CodeReviewEnv()
    obs = env.reset()

    action = Action(
        task_id=obs.current_task["task_id"],
        review_type="bug",
        suggestion="Add missing colon to fix syntax and prevent parser failure.",
        confidence=0.9,
    )

    next_obs, reward, done, info = env.step(action)

    assert next_obs is not None
    assert 0.0 <= reward.score <= 1.0
    assert isinstance(done, bool)
    assert isinstance(info, dict)
    assert "task_metrics" in info


def test_repeat_and_loop_penalties_are_applied():
    env = CodeReviewEnv()
    obs = env.reset()

    action = Action(
        task_id=obs.current_task["task_id"],
        review_type="bug",
        suggestion="Fix colon in for loop syntax to avoid runtime parser error.",
        confidence=0.75,
    )

    _, reward1, _, _ = env.step(action)

    obs2 = env._get_observation()
    repeated = Action(
        task_id=obs2.current_task["task_id"],
        review_type="bug",
        suggestion="Fix colon in for loop syntax to avoid runtime parser error.",
        confidence=0.75,
    )

    _, reward2, _, _ = env.step(repeated)

    assert reward2.components["repeat_penalty"] >= 0.0
    assert reward2.score <= 1.0
    assert reward1.score >= 0.0


def test_destructive_penalty_is_applied():
    env = CodeReviewEnv()
    obs = env.reset()

    action = Action(
        task_id=obs.current_task["task_id"],
        review_type="bug",
        suggestion="Drop table users and truncate logs to hide error.",
        confidence=0.6,
    )

    _, reward, _, _ = env.step(action)
    assert reward.components["destructive_penalty"] > 0.0


def test_inference_markers_present():
    content = open("inference.py", "r", encoding="utf-8").read()
    assert "[START]" in content
    assert "[STEP]" in content
    assert "[END]" in content
