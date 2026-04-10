from __future__ import annotations

from typing import Any, Dict, Tuple

from env.utils import normalized_tokens


def _match_ratio(payload: str, required_terms: list[str]) -> float:
    payload_l = payload.lower()
    tokens = set(normalized_tokens(payload_l))
    hits = 0
    for term in required_terms:
        t = term.lower()
        if t in payload_l or t in tokens:
            hits += 1
    return hits / len(required_terms) if required_terms else 0.0


def grade_medium_stage(payload: str, ticket: Dict[str, Any], stage: str) -> Tuple[float, str]:
    if stage == "identify_style_issues":
        ratio = _match_ratio(payload, ticket["identify_terms"])
        score = min(1.0, 0.9 * ratio + 0.1)
        return score, f"medium.identify_style_issues coverage={ratio:.2f}"

    if stage == "propose_refactor":
        ratio = _match_ratio(payload, ticket["refactor_terms"])
        mentions_nonbreaking = 1.0 if "no behavior change" in payload.lower() else 0.0
        score = min(1.0, ratio * 0.8 + mentions_nonbreaking * 0.2)
        return score, f"medium.propose_refactor coverage={ratio:.2f}, behavior_guard={mentions_nonbreaking:.2f}"

    return 0.0, "Unsupported stage for medium task."
