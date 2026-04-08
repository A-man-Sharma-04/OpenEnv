"""Grader for simple bug tasks."""
import re
from typing import Tuple

def grade_bug(action: dict, snippet: dict) -> Tuple[float, str]:
    code = snippet["code"].lower()
    suggestion = (action.get("review_type", "") + " " + (action.get("suggestion", "") or "")).lower()
    
    if snippet["id"] == "bug_syntax":
        if re.search(r"bug|syntax|colon|for", suggestion):
            conf = action.get("confidence", 0.0)
            score = 1.0 if conf > 0.7 else 0.8
            return score, "Correct syntax detection"
    elif snippet["id"] == "bug_runtime":
        if re.search(r"runtime|get|index|keyerror", suggestion):
            conf = action.get("confidence", 0.0)
            score = 1.0 if conf > 0.7 else 0.8
            return score, "Correct runtime fix"
    
    return 0.0, "Bug missed - check syntax/runtime errors"

