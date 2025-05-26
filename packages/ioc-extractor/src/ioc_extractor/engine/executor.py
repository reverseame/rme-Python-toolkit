from ioc_extractor.engine.matcher import evaluate_conditions
from ioc_extractor.engine.selector import process_select
from ioc_extractor.utils.formatter import build_rule_name


def execute_rule(entry: dict, rule: dict, source_file: str) -> dict | None:
    """
    Executes a full rule against a single input entry.
    Returns a match result with selected fields and full rule context.
    """
    if not evaluate_conditions(entry, rule.get("where", {})):
        return None

    selected = process_select(entry, rule.get("select", []))
    fields = selected["fields"]
    raw_api = selected.get("api", "?")
    clean_api = raw_api.split("(")[0].strip() if isinstance(raw_api, str) else "?"

    meta = rule.get("meta", {})
    variant = rule.get("name")

    return {
        "api": clean_api,
        "attributes": fields,
        "rule": {
            "name": meta.get("name", "?"),
            "variant": variant
        },
        "metadata": {
            "description": meta.get("description", ""),
            "version": meta.get("version", "1.0"),
            "authors": meta.get("authors", [])
        },
        "taxonomy": {
            "rule": {
                "attack": meta.get("attck", []),
                "mbcs": meta.get("mbcs", []),
                "tags": meta.get("tags", []),
                "categories": meta.get("categories", [])
            },
            "variant": {
                "attack": rule.get("attck", []),
                "mbcs": rule.get("mbcs", []),
                "tags": rule.get("tags", []),
                "categories": rule.get("categories", [])
            }
        },
        "sources": {
            "input": source_file,
            "rule": rule.get("__source__")
        }
    }
