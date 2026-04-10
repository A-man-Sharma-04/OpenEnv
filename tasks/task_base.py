from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from env.utils import load_json_dataset


GraderFn = Callable[[str, Dict[str, Any], str], Tuple[float, str]]


@dataclass
class TaskDefinition:
    task_id: str
    difficulty: str
    objective: str
    required_stages: List[str]
    dataset_path: Path
    grader: GraderFn

    @property
    def dataset(self) -> List[Dict[str, Any]]:
        return load_json_dataset(self.dataset_path)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "difficulty": self.difficulty,
            "objective": self.objective,
            "required_stages": list(self.required_stages),
            "dataset_path": str(self.dataset_path),
        }
