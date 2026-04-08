"""Grader for complex refactors."""

from typing import Tuple


def _tokenize(text: str) -> set[str]:
    return {tok.strip(".,:;()[]{}\"'").lower() for tok in text.split() if tok.strip()}

def grade_refactor(action: dict, snippet: dict) -> Tuple[float, str]:
    suggestion = (action.get("suggestion", "") or "").strip()
    if not suggestion or len(suggestion) < 20:
        return 0.0, "Refactor suggestion too brief"

    keywords = [kw.lower() for kw in snippet.get("expected_keywords", [])]
    if not keywords:
        return 0.2, "No expected keywords configured for snippet"

    suggestion_tokens = _tokenize(suggestion)
    relevance_hits = sum(1 for kw in keywords if kw in suggestion.lower() or kw in suggestion_tokens)
    relevance = relevance_hits / len(keywords)
    quality = 1.0 if len(suggestion.split()) > 15 else 0.5
    score = min(1.0, relevance * 0.7 + quality * 0.3)

    return score, f"Refactor quality: {score:.2f} (relevance: {relevance:.2f})"

