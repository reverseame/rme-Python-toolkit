from ioc_extractor.engine.matcher import evaluate_conditions
from ioc_extractor.engine.selector import process_select


def extract_taxonomy(obj: dict, include: list[str] | None = None, exclude: list[str] | None = None) -> dict:
    """
    Extracts a subset of keys from the given object.
    - If `include` is None or empty, all keys are considered.
    - If `include` contains keys, only those are considered.
    - If `exclude` contains keys, they are removed from the result.
    """
    result = {}

    # Determine which keys to include
    keys = obj.keys() if not include else include

    # Filter and extract values
    for k in keys:
        if exclude and k in exclude:
            continue
        if k in obj:
            result[k] = obj[k]

    return result


def execute_rule(entry: dict, rule: dict, source_file: str) -> dict | None:
    """
    Executes a rule-variant pair on a given input entry.
    Input format: { meta: {...}, variant: {...} }
    """
    meta = rule["meta"]
    variant = rule["variant"]

    if not evaluate_conditions(entry, variant.get("where", {})):
        return None

    selected = process_select(entry, variant.get("select", []))
    fields = selected["fields"]
    raw_api = selected.get("api", "?")
    clean_api = raw_api.split("(")[0].strip() if isinstance(raw_api, str) else "?"

    rule_name = meta.get("name", "?")
    variant_name = variant.get("name")

    taxonomy_fields = ["attck", "mbcs", "tags", "categories", "description"]

    return {
        "api": clean_api,
        "attributes": fields,
        "rule": {
            "name": rule_name,
            "variant": None if variant_name == rule_name else variant_name
        },
        "metadata": {
            k: meta[k] for k in ("version", "authors") if k in meta
        },
        "taxonomy": {
            "rule": extract_taxonomy(meta, include=taxonomy_fields),
            "variant": extract_taxonomy(variant, include=taxonomy_fields)
        },
        "sources": {
            "input": source_file,
            "rule": variant.get("__source__")
        }
    }
