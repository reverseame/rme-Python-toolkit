import json
import re
from typing import Any

import requests
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PATTERNS_URL = "https://raw.githubusercontent.com/reverseame/rme-Python-toolkit/refs/heads/main/ioc-extractor/packages/ioc-extractor/data/patterns.json"


def compile_where(where: Any) -> Any:
    """
    Recursively compile any regex in the 'where' clause.
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
                flags = re.IGNORECASE if operand.startswith("(?i)") else 0
                pattern = operand[4:] if operand.startswith("(?i)") else operand
                try:
                    new[op] = re.compile(pattern, flags)
                    logger.debug(f"Compiled regex pattern: {pattern}")
                except re.error as e:
                    logger.error(f"Invalid regex pattern '{operand}': {e}")
                    raise
            else:
                new[op] = compile_where(operand)
        return new
    elif isinstance(where, list):
        return [compile_where(item) for item in where]
    else:
        return where


def load_query_rules(path: str = None) -> list[dict[str, Any]]:
    """
    Load query rules from a local file or URL and compile regex patterns.
    """
    try:
        if not path:
            logger.warning("No path provided for patterns. Using default URL.")
            resp = requests.get(DEFAULT_PATTERNS_URL)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Loaded patterns from default URL: '{DEFAULT_PATTERNS_URL}'")
        elif path.startswith(("http://", "https://")):
            logger.info(f"Fetching patterns from URL: '{path}'")
            resp = requests.get(path)
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Successfully fetched and parsed patterns from: '{path}'")
        else:
            logger.info(f"Loading patterns from local file: '{path}'")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Successfully loaded patterns from file: '{path}'")
    except (requests.RequestException, json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load rules from '{path}': {e}", exc_info=True)
        raise

    rules = data.get("rules", [])
    logger.debug(f"Compiling 'where' clauses for {len(rules)} rule(s)")
    for rule in rules:
        rule["where"] = compile_where(rule.get("where", {}))

    logger.info("Query rules loaded and compiled successfully")
    return rules
