from __future__ import annotations

from pathlib import Path

from tasks.graders.hard_grader import grade_hard_stage
from tasks.task_base import TaskDefinition


HARD_TASK = TaskDefinition(
    task_id="hard",
    difficulty="hard",
    objective="Run a full incident code-review workflow: triage risks, design fix plan, and define verification tests.",
    required_stages=["triage_risks", "propose_fix_plan", "define_test_plan"],
    dataset_path=Path("data/hard_cases.json"),
    grader=grade_hard_stage,
)
