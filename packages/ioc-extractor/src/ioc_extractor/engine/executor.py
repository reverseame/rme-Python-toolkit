from ioc_extractor.engine.matcher import evaluate_conditions
from ioc_extractor.engine.selector import process_select


def execute_rule(entry, rule):
    if not evaluate_conditions(entry, rule.get("where", {})):
        return None
    return process_select(entry, rule.get("select", []))
