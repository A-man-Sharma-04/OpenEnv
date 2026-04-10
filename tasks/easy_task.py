from __future__ import annotations

from pathlib import Path

from tasks.graders.easy_grader import grade_easy_stage
from tasks.task_base import TaskDefinition


EASY_TASK = TaskDefinition(
    task_id="easy",
    difficulty="easy",
    objective="Identify the production bug in a support ticket and provide a safe direct fix.",
    required_stages=["identify_bug"],
    dataset_path=Path("data/easy_cases.json"),
    grader=grade_easy_stage,
)
