"""Deterministic, real-world code review snippets used by CodeReviewEnv."""

TASK_DEFINITIONS = {
    "simple_bug": {
        "difficulty": "easy",
        "objective": "Detect and fix correctness issues that cause syntax/runtime failures.",
    },
    "style_issue": {
        "difficulty": "medium",
        "objective": "Propose PEP8-compliant improvements while preserving behavior.",
    },
    "complex_refactor": {
        "difficulty": "hard",
        "objective": "Recommend architecture-level refactors that improve maintainability.",
    },
}


CODE_SNIPPETS = [
    {
        "id": "bug_syntax",
        "task_type": "simple_bug",
        "title": "Missing Colon In Production Billing Path",
        "code": """def calculate_total(items):
    total = 0
    for item in items
        total += item.price
    return total""",
        "expected_keywords": ["colon", "for", "syntax"],
        "anti_patterns": ["ignore", "looks fine"],
    },
    {
        "id": "bug_runtime",
        "task_type": "simple_bug",
        "title": "Unsafe Dictionary Access In User Profile Service",
        "code": """def get_user_name(users, user_id):
    return users[user_id].name""",
        "expected_keywords": ["keyerror", "get", "check"],
        "anti_patterns": ["disable", "try/except pass"],
    },
    {
        "id": "style_longline",
        "task_type": "style_issue",
        "title": "Unmaintainable SQL Construction",
        "code": """result = database.query('SELECT * FROM users WHERE status = \'active\' AND age > 18 AND country = \'US\'', timeout=30)""",
        "expected_keywords": ["line length", "pep8", "wrap", "79"],
        "anti_patterns": ["ignore pep8", "disable linter"],
    },
    {
        "id": "style_space",
        "task_type": "style_issue",
        "title": "Unreadable One-Liner In ETL Step",
        "code": """def process_data(data):result=[x*2 for x in data]""",
        "expected_keywords": ["newline", "indent", "whitespace", "format"],
        "anti_patterns": ["one-liner", "keep compact"],
    },
    {
        "id": "refactor_loop",
        "task_type": "complex_refactor",
        "title": "Imperative Filtering In Core Path",
        "code": """def filter_users(users):
    active = []
    for u in users:
        if u.active:
            active.append(u)
    return active""",
        "expected_keywords": ["list comprehension", "readability", "test"],
        "anti_patterns": ["rewrite everything", "remove tests"],
    },
    {
        "id": "refactor_func",
        "task_type": "complex_refactor",
        "title": "Parsing Logic Coupled To Utility Layer",
        "code": """def parse_json(json_str):
    import json
    return json.loads(json_str)""",
        "expected_keywords": ["abstraction", "class", "service", "single responsibility"],
        "anti_patterns": ["global state", "monkey patch"],
    },
]

