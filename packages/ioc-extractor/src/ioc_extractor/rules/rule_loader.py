import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

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
                flags = re.IGNORECASE if operand.startswith("(?i)") else 0
                pattern = operand[4:] if operand.startswith("(?i)") else operand
                compiled[op] = re.compile(pattern, flags)
            else:
                compiled[op] = compile_where(operand)
        return compiled
    elif isinstance(where, list):
        return [compile_where(w) for w in where]
    return where

def normalize_list(val: Union[str, list, None]) -> list:
    if val is None:
        return []
    return val if isinstance(val, list) else [val]

@dataclass
class Meta:
    name: str
    description: str = ""
    version: str = "1.0"
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    attck: list[str] = field(default_factory=list)
    mbcs: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Meta":
        return Meta(
            name=d.get("name", "?"),
            description=d.get("description", ""),
            version=d.get("version", "1.0"),
            authors=normalize_list(d.get("authors")),
            categories=normalize_list(d.get("categories")),
            tags=normalize_list(d.get("tags")),
            attck=normalize_list(d.get("att&ck")),
            mbcs=normalize_list(d.get("mbcs")),
        )

@dataclass
class Variant:
    name: Optional[str] = None
    select: list[dict[str, Any]] = field(default_factory=list)
    where: Any = field(default_factory=dict)
    mbcs: list[str] = field(default_factory=list)
    attck: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Variant":
        return Variant(
            name=data.get("name"),
            select=data.get("select", []),
            where=data.get("where", {}),
            mbcs=normalize_list(data.get("mbcs")),
            attck=normalize_list(data.get("att&ck")),
            tags=normalize_list(data.get("tags")),
            categories=normalize_list(data.get("categories")),
        )

    def to_rule(self, meta: Meta, source: Optional[Path] = None) -> "Rule":
        def merged(field):
            return list({*getattr(meta, field), *getattr(self, field)})
        return Rule(
            name=self.name or meta.name,
            select=self.select,
            where=compile_where(self.where),
            meta=meta,
            mbcs=merged("mbcs"),
            attck=merged("attck"),
            tags=merged("tags"),
            categories=merged("categories"),
            __source__=str(source) if source else None,
        )

@dataclass
class Rule:
    name: str
    select: list[dict[str, Any]] = field(default_factory=list)
    where: Any = field(default_factory=dict)
    meta: Meta = field(default_factory=Meta)
    mbcs: list[str] = field(default_factory=list)
    attck: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    __source__: Optional[str] = None

    @staticmethod
    def from_dict(data: dict[str, Any], meta: Optional[Meta] = None, source: Optional[Path] = None) -> "Rule":
        rule_meta = Meta.from_dict(data.get("meta", {})) if meta is None else meta
        inherited_fields = ["mbcs", "attck", "tags", "categories"]

        for key in inherited_fields:
            meta_vals = getattr(rule_meta, key, [])
            local_vals = normalize_list(data.get(key, []))
            combined = list({*meta_vals, *local_vals})
            data[key] = combined

        return Rule(
            name=data.get("name", rule_meta.name),
            select=data.get("select", []),
            where=compile_where(data.get("where", {})),
            meta=rule_meta,
            mbcs=data.get("mbcs", []),
            attck=data.get("attck", []),
            tags=data.get("tags", []),
            categories=data.get("categories", []),
            __source__=str(source) if source else None,
        )

def _resolve_rule_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        if path.is_dir():
            files += list(path.glob("*.yml")) + list(path.glob("*.yaml"))
        elif path.suffix in (".yml", ".yaml"):
            files.append(path)
    return files

def load_query_rules(paths: list[Path]) -> list[dict[str, Any]]:
    rules: list[Rule] = []
    for file in _resolve_rule_files(paths):
        with open(file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if isinstance(raw, list):
            for r in raw:
                rules.append(Rule.from_dict(r, source=file))

        elif isinstance(raw, dict) and "meta" in raw and "variants" in raw:
            base_meta = Meta.from_dict(raw["meta"])
            for variant in raw["variants"]:
                v = Variant.from_dict(variant)
                rules.append(v.to_rule(base_meta, source=file))

        elif isinstance(raw, dict) and "select" in raw and "where" in raw:
            rules.append(Rule.from_dict(raw, source=file))

        else:
            raise ValueError(f"Invalid rule format in {file}")

    logger.info(f"Loaded {len(rules)} rule(s)")

    return [
        {
            **r.__dict__,
            "meta": r.meta.__dict__
        }
        for r in rules
    ]
