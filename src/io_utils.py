"""Small deterministic JSON/CSV and output-directory helpers."""
from __future__ import annotations

import csv
import json
from pathlib import Path


def parse_json(text):
    """Decode JSON without silently choosing between duplicate object fields."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object field: " + key)
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError("non-JSON numeric constant: " + value)

    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def load_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")


def write_csv(path, rows, fields=None):
    path = Path(path)
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fresh_directory(path):
    path = Path(path)
    if path.exists():
        if any(path.iterdir()):
            raise ValueError("output directory must be absent or empty")
        path.rmdir()
    path.mkdir(parents=True)
    return path
