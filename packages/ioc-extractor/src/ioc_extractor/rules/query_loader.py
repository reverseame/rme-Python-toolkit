import json
import re
from typing import Any

import requests

DEFAULT_PATTERNS_URL = "https://raw.githubusercontent.com/ORG/REPO/main/patterns.json"


def compile_where(where: Any) -> Any:
    """
    Recursively walk the where-clause and compile any regex string into a Pattern.
    """
    if isinstance(where, dict):
        if "and" in where:
            return {"and": [compile_where(c) for c in where["and"]]}
        if "or" in where:
            return {"or": [compile_where(c) for c in where["or"]]}
        if "not" in where:
            return {"not": compile_where(where["not"])}
        new = {}
        for op, operand in where.items():
            if op == "regex" and isinstance(operand, str):
                # Detect inline (?i) flag
                flags = re.IGNORECASE if operand.startswith("(?i)") else 0
                pattern = operand
                if operand.startswith("(?i)"):
                    pattern = operand[4:]
                new[op] = re.compile(pattern, flags)
            else:
                new[op] = compile_where(operand)
        return new
    elif isinstance(where, list):
        return [compile_where(item) for item in where]
    else:
        return where


def load_query_rules(path: str = None) -> list[dict[str, Any]]:
    if not path:
        resp = requests.get(DEFAULT_PATTERNS_URL)
        resp.raise_for_status()
        data = resp.json()
    elif path.startswith(("http://", "https://")):
        resp = requests.get(path)
        resp.raise_for_status()
        data = resp.json()
    else:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

    rules = data.get("rules", [])
    # Pre-compile all regex operands in where-clauses
    for rule in rules:
        rule["where"] = compile_where(rule.get("where", {}))
    return rules
