import jmespath
from ioc_extractor.rules.modifiers import apply_modifiers


def resolve_selector(entry: dict, selector: str):
    try:
        return jmespath.search(selector, entry)
    except Exception as e:
        raise RuntimeError(f"JMESPath error in selector '{selector}': {e}")

def process_select(entry, select_list):
    fields = {}
    for sel in select_list:
        field = sel["field"]
        alias = sel.get("alias", field)
        transforms = sel.get("transform", [])
        val = resolve_selector(entry, field)

        # Aplana listas de un solo valor
        if isinstance(val, list):
            if len(val) == 1:
                val = val[0]
            elif not val:
                val = None

        if isinstance(val, str) and transforms:
            val = apply_modifiers(val, transforms)
        fields[alias] = val

    return {
        "id": entry.get("id", "?"),
        "api": entry.get("api", "?"),
        "fields": fields,
    }
