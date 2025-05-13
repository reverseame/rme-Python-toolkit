import re
from pathlib import Path
from typing import Any

import yaml
from ioc_extractor.utils.logger import get_logger

logger = get_logger(__name__)

def compile_where(where: Any) -> Any:
    if isinstance(where, dict):
        if "and" in where:
            return {"and": [compile_where(c) for c in where["and"]]}
        if "or" in where:
            return {"or": [compile_where(c) for c in where["or"]]}
        if "not" in where:
            return {"not": compile_where(where["not"])}
        compiled = {}
        for op, operand in where.items():
            if op == "regex" and isinstance(operand, str):
                pattern = operand[4:] if operand.startswith("(?i)") else operand
                flags = re.IGNORECASE if operand.startswith("(?i)") else 0
                compiled[op] = re.compile(pattern, flags)
            else:
                compiled[op] = compile_where(operand)
        return compiled
    elif isinstance(where, list):
        return [compile_where(w) for w in where]
    return where

def _resolve_rule_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files += list(path.glob("*.yml")) + list(path.glob("*.yaml"))
        elif path.suffix in (".yml", ".yaml"):
            files.append(path)
    return files

def _normalize_meta(rule: dict[str, Any]) -> dict[str, Any]:
    for key in ["mbcs", "attcks", "tags", "categories"]:
        if key in rule and not isinstance(rule[key], list):
            rule[key] = [rule[key]]
    return rule

def _normalize_rule(rule: dict[str, Any], source: Path) -> dict[str, Any]:
    rule["__source__"] = str(source)
    return _normalize_meta(rule)

def _expand_rule_definitions(data: Any, source: Path) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [_normalize_rule(r, source) for r in data]
    if isinstance(data, dict):
        if "meta" in data and "variants" in data:
            base = _normalize_meta(data["meta"])
            return [_normalize_rule({**base, **v}, source) for v in data["variants"]]
        if "select" in data and "where" in data:
            return [_normalize_rule(data, source)]
    raise ValueError(f"Invalid rule format in {source}")

def load_query_rules(paths: list[Path]) -> list[dict[str, Any]]:
    rules = []
    for file in _resolve_rule_files(paths):
        with open(file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        expanded = _expand_rule_definitions(data, file)
        for r in expanded:
            r["where"] = compile_where(r.get("where", {}))
            rules.append(r)
    logger.info(f"Loaded {len(rules)} rule(s)")
    return rules
