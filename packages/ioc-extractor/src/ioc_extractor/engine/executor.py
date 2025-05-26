from ioc_extractor.engine.matcher import evaluate_conditions
from ioc_extractor.engine.selector import process_select
from ioc_extractor.utils.formatter import format_result


def execute_rule(entry: dict, rule: dict) -> dict | None:
    """
    Executes a full rule against a single input entry.
    Returns structured match output only if 'where' conditions are satisfied.
    """
    if not evaluate_conditions(entry, rule.get("where", {})):
        return None
    partial = process_select(entry, rule.get("select", []))
    return format_result(partial["id"], partial["api"], partial["fields"], rule)
