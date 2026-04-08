from __future__ import annotations

from typing import Any, Dict, Tuple

from app.utils import normalized_tokens


def _keyword_recall(text: str, expected_keywords: list[str]) -> float:
    tokens = set(normalized_tokens(text))
    if not expected_keywords:
        return 0.0
    hits = sum(1 for kw in expected_keywords if kw.lower() in tokens or kw.lower() in text.lower())
    return hits / len(expected_keywords)


def grade_easy_stage(payload: str, ticket: Dict[str, Any], stage: str) -> Tuple[float, str]:
    if stage != "identify_bug":
        return 0.0, "Easy task accepts only identify_bug."

    recall = _keyword_recall(payload, ticket.get("required_terms", []))
    safe = 1.0 if "try/except pass" not in payload.lower() else 0.0
    score = min(1.0, 0.85 * recall + 0.15 * safe)
    return score, f"easy.identify_bug recall={recall:.2f}, safe={safe:.2f}"
