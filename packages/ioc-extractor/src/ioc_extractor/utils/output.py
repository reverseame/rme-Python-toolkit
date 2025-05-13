import json
from collections import Counter


def save_results(results, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def summarize_results(results):
    summary = Counter(match["id"] for match in results)
    return dict(summary)
