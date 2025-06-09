from typing import Any, Callable


class ValueTransformer:
    """Apply per-key and general value transformations."""

    def __init__(self):
        self.rules: dict[str, Callable[[str], Any]] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("id", self._to_int)
        self.register("tid", self._to_int)
        self.register("thread", self._to_int)
        self.register("duration", self._to_float)

    def register(self, key: str, func: Callable[[str], Any]):
        self.rules[key] = func

    def transform(self, key: str, value: Any) -> Any:
        if value is None:
            return None

        text = value.strip() if isinstance(value, str) else str(value)

        if key in self.rules:
            try:
                return self.rules[key](text)
            except Exception:
                pass

        low = text.lower()
        if low == "null":
            return None
        if low == "true":
            return True
        if low == "false":
            return False
        if text == "":
            return "undefined"

        return text

    def _to_int(self, val: str) -> int:
        try:
            return int(val)
        except Exception:
            return 0

    def _to_float(self, val: str) -> float:
        try:
            return float(val)
        except Exception:
            return 0.0
