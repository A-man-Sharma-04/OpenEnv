"""Grader for style issues."""
import re
from typing import Tuple

def grade_style(action: dict, snippet: dict) -> Tuple[float, str]:
    suggestion = (action.get("review_type", "") + " " + (action.get("suggestion", "") or "")).lower()
    
    if snippet["id"] == "style_longline":
        if re.search(r"pep8|line|length|79|80|break", suggestion):
            return 1.0, "Correct PEP8 line length fix"
        return 0.4, "Partial style recognition"
    elif snippet["id"] == "style_space":
        if re.search(r"space|indent|newline|format", suggestion):
            return 1.0, "Correct formatting fix"
        return 0.3, "Missed style issue"
    
    return 0.2, "Generic style feedback - check PEP8"

