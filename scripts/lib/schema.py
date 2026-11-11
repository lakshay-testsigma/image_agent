"""Tiny JSON Schema validator (a subset of draft 2020-12) — enough for the files in schemas/, no dependency.

Supported keywords: type, enum, const, required, properties, additionalProperties, items, minItems,
minLength, minimum, maximum, pattern, allOf, $ref ("#/$defs/x" or "other.schema.json#/$defs/x").

  errors = validate(data, load("design#global"))     -> list of "path: problem" strings, [] when valid
  check(data, "design#global", "design/global.json")  -> dies with every error listed

A schema name is "<file stem>" or "<file stem>#<definition>" (a key under that file's $defs).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import die

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
    "number": (int, float), "integer": int,
}


def _file(stem_or_name: str) -> dict:
    name = stem_or_name if stem_or_name.endswith(".json") else f"{stem_or_name}.schema.json"
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def load(name: str) -> tuple[dict, dict]:
    """Returns (schema, root) — root is the whole file, needed to resolve local $refs."""
    stem, _, definition = name.partition("#")
    root = _file(stem)
    return (root["$defs"][definition] if definition else root), root


def _deref(ref: str, root: dict) -> tuple[dict, dict]:
    file, _, pointer = ref.partition("#")
    if file:
        root = _file(file)
    target = root
    for part in filter(None, pointer.split("/")):
        target = target[part]
    return target, root


def _is_type(value, name: str) -> bool:
    if name in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[name])


def validate(data, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    root = root or schema
    if "$ref" in schema:
        target, target_root = _deref(schema["$ref"], root)
        return validate(data, target, target_root, path)

    errors: list[str] = []
    for sub in schema.get("allOf", []):
        errors += validate(data, sub, root, path)
    if "type" in schema:
        allowed = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(data, t) for t in allowed):
            return [f"{path}: expected {' or '.join(allowed)}, got {type(data).__name__}"]
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{path}: {data!r} is not one of {schema['enum']}")
    if "const" in schema and data != schema["const"]:
        errors.append(f"{path}: must be {schema['const']!r}")

    if isinstance(data, str):
        if len(data.strip()) < schema.get("minLength", 0):
            errors.append(f"{path}: must not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errors.append(f"{path}: {data!r} does not match {schema['pattern']}")
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: {data} is below the minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: {data} is above the maximum {schema['maximum']}")
    elif isinstance(data, list):
        if len(data) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(data):
                errors += validate(item, schema["items"], root, f"{path}[{i}]")
    elif isinstance(data, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}: missing required '{key}'")
        extra = schema.get("additionalProperties", True)
        for key, value in data.items():
            if key in props:
                errors += validate(value, props[key], root, f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unknown key '{key}' (allowed: {', '.join(sorted(props))})")
            elif isinstance(extra, dict):
                errors += validate(value, extra, root, f"{path}.{key}")
    return errors


def check(data, name: str, what: str) -> None:
    errors = validate(data, *load(name))
    if errors:
        die(f"{what} does not match schemas/{name.partition('#')[0]}.schema.json:\n  - " + "\n  - ".join(errors))
