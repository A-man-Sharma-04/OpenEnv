from __future__ import annotations

from typing import Any, Dict, Tuple

from app.utils import normalized_tokens


def _coverage(payload: str, terms: list[str]) -> float:
    payload_l = payload.lower()
    tokens = set(normalized_tokens(payload_l))
    hits = sum(1 for term in terms if term.lower() in payload_l or term.lower() in tokens)
    return hits / len(terms) if terms else 0.0


def grade_hard_stage(payload: str, ticket: Dict[str, Any], stage: str) -> Tuple[float, str]:
    if stage == "triage_risks":
        ratio = _coverage(payload, ticket["risk_terms"])
        score = min(1.0, ratio)
        return score, f"hard.triage_risks coverage={ratio:.2f}"

    if stage == "propose_fix_plan":
        ratio = _coverage(payload, ticket["fix_terms"])
        rollback = 1.0 if "rollback" in payload.lower() else 0.0
        score = min(1.0, ratio * 0.85 + rollback * 0.15)
        return score, f"hard.propose_fix_plan coverage={ratio:.2f}, rollback={rollback:.2f}"

    if stage == "define_test_plan":
        ratio = _coverage(payload, ticket["test_terms"])
        has_monitoring = 1.0 if "monitor" in payload.lower() else 0.0
        score = min(1.0, ratio * 0.85 + has_monitoring * 0.15)
        return score, f"hard.define_test_plan coverage={ratio:.2f}, monitoring={has_monitoring:.2f}"

    return 0.0, "Unsupported stage for hard task."
