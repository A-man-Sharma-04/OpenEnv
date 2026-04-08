from __future__ import annotations

from pathlib import Path

from graders.medium_grader import grade_medium_stage
from tasks.task_base import TaskDefinition


MEDIUM_TASK = TaskDefinition(
    task_id="medium",
    difficulty="medium",
    objective="Perform a two-step code review workflow: identify style risks, then provide a maintainable fix plan.",
    required_stages=["identify_style_issues", "propose_refactor"],
    dataset_path=Path("data/medium_cases.json"),
    grader=grade_medium_stage,
)
