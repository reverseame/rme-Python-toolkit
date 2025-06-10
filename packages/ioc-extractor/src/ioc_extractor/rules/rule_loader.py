import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from common.logger import get_logger

logger = get_logger(__name__)

def compile_where(where: Any) -> Any:
    """
    Recursively processes 'where' conditions, compiling regex patterns
    and preparing operator trees for evaluation.
    """
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
                flags = re.IGNORECASE if operand.startswith("(?i)") else 0
                pattern = operand[4:] if operand.startswith("(?i)") else operand
                compiled[op] = re.compile(pattern, flags)
            else:
                compiled[op] = compile_where(operand)
        return compiled
    elif isinstance(where, list):
        return [compile_where(w) for w in where]
    return where

def normalize_list(val: str | list | None) -> list:
    """
    Ensures values are always returned as lists, regardless of input format.
    """
    if val is None:
        return []
    return val if isinstance(val, list) else [val]

@dataclass
class Meta:
    name: str
    description: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    mbcs: list[str] = field(default_factory=list)
    attck: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    version: str = "1.0"

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Meta":
        return Meta(
            name=d.get("name", "?"),
            description=d.get("description", ""),
            categories=normalize_list(d.get("categories")),
            tags=normalize_list(d.get("tags")),
            mbcs=normalize_list(d.get("mbcs")),
            attck=normalize_list(d.get("att&ck")),
            authors=normalize_list(d.get("authors")),
            version=d.get("version", "1.0"),
        )

@dataclass
class Variant:
    name: Optional[str] = None
    description: str = ""
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    mbcs: list[str] = field(default_factory=list)
    attck: list[str] = field(default_factory=list)
    select: list[dict[str, Any]] = field(default_factory=list)
    where: Any = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Variant":
        return Variant(
            name=data.get("name"),
            description=data.get("description", ""),
            categories=normalize_list(data.get("categories")),
            tags=normalize_list(data.get("tags")),
            mbcs=normalize_list(data.get("mbcs")),
            attck=normalize_list(data.get("att&ck")),
            select=data.get("select", []),
            where=data.get("where", {}),
        )

@dataclass
class RuleWrapper:
    meta: Meta
    variant: Variant
    source: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.__dict__,
            "variant": self.variant.__dict__ | {"__source__": self.source}
        }

def _resolve_rule_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files += list(path.glob("*.yml")) + list(path.glob("*.yaml"))
        elif path.suffix in (".yml", ".yaml"):
            files.append(path)
    return files

def load_query_rules(paths: list[Path]) -> list[dict[str, Any]]:
    results = []

    for file in _resolve_rule_files(paths):
        with open(file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if isinstance(raw, list):
            for r in raw:
                meta = Meta.from_dict(r.get("meta", {}))
                variant = Variant.from_dict(r)
                results.append(RuleWrapper(meta, variant, source=str(file)).to_dict())

        elif isinstance(raw, dict) and "meta" in raw and "variants" in raw:
            meta = Meta.from_dict(raw["meta"])
            for v in raw["variants"]:
                variant = Variant.from_dict(v)
                results.append(RuleWrapper(meta, variant, source=str(file)).to_dict())

        elif isinstance(raw, dict) and "select" in raw and "where" in raw:
            meta = Meta.from_dict({})
            variant = Variant.from_dict(raw)
            results.append(RuleWrapper(meta, variant, source=str(file)).to_dict())

        else:
            raise ValueError(f"Invalid rule format in {file}")

    logger.info(f"Loaded {len(results)} rule(s)")
    return results
