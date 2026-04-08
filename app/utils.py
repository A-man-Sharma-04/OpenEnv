from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


DESTRUCTIVE_PATTERN = re.compile(
    r"\b(drop\s+table|truncate|delete\s+all|rm\s+-rf|disable\s+tests?|ship\s+without\s+tests?)\b",
    flags=re.IGNORECASE,
)


def load_json_dataset(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Dataset must be a JSON list: {path}")
    return data


def normalized_tokens(text: str) -> List[str]:
    clean = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [token for token in clean.split() if token]


def has_destructive_content(text: str) -> bool:
    return bool(DESTRUCTIVE_PATTERN.search(text))
