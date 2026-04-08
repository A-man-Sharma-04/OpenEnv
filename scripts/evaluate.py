from __future__ import annotations

from statistics import mean
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.env import CodeReviewOpenEnv


DETERMINISTIC_POLICY = {
    "easy": [
        {"action_type": "identify_bug", "payload": "The for loop is missing a colon, causing syntax failure in the loop header.", "confidence": 0.82}
    ],
    "medium": [
        {"action_type": "identify_style_issues", "payload": "There are PEP8 readability issues: line length, compact whitespace, and unclear formatting.", "confidence": 0.8},
        {"action_type": "propose_refactor", "payload": "Extract helper functions and format the expression with clear indentation and docstring; no behavior change.", "confidence": 0.78},
    ],
    "hard": [
        {"action_type": "triage_risks", "payload": "Risk triage: duplicate charges under retry storms due to missing idempotency and atomic handling.", "confidence": 0.76},
        {"action_type": "propose_fix_plan", "payload": "Introduce idempotency key checks, transactional writes, retry policy guardrails, and rollback on partial failure.", "confidence": 0.8},
        {"action_type": "define_test_plan", "payload": "Create unit, integration, load, and regression tests; monitor charge duplication in production.", "confidence": 0.79},
    ],
}


def evaluate_task(task_id: str) -> float:
    env = CodeReviewOpenEnv(default_task_id=task_id)
    observation = env.reset(task_id)
    done = False
    scores = []

    for item in DETERMINISTIC_POLICY[task_id]:
        if done:
            break
        action = {
            "task_id": task_id,
            "action_type": item["action_type"],
            "payload": item["payload"],
            "confidence": item["confidence"],
        }
        observation, reward, done, _ = env.step(action)
        scores.append(reward.score)

    return round(mean(scores), 3) if scores else 0.0


def main() -> None:
    for task_id in ["easy", "medium", "hard"]:
        print(f"{task_id}: {evaluate_task(task_id)}")


if __name__ == "__main__":
    main()
