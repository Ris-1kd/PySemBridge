"""Load and validate Semantic Bridge IR files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal environments.
    Draft202012Validator = None


SCHEMA_PATH = Path(__file__).with_name("semantic_bridge.schema.json")


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_bridge(path: Path) -> dict[str, Any]:
    bridge = json.loads(path.read_text(encoding="utf-8"))
    if Draft202012Validator is not None:
        validator = Draft202012Validator(load_schema())
        errors = sorted(validator.iter_errors(bridge), key=lambda error: list(error.path))
        if errors:
            messages = []
            for error in errors:
                location = ".".join(str(part) for part in error.path) or "<root>"
                messages.append(f"{location}: {error.message}")
            raise ValueError("Invalid Semantic Bridge IR:\n" + "\n".join(messages))
    else:
        _validate_minimal_bridge(bridge)
    return bridge


def _validate_minimal_bridge(bridge: dict[str, Any]) -> None:
    required_fields = ("version", "bridge_id", "language", "project", "gap_types")
    missing = [field for field in required_fields if field not in bridge]
    if missing:
        raise ValueError(f"Invalid Semantic Bridge IR: missing required fields: {', '.join(missing)}")
    if bridge["language"] != "python":
        raise ValueError("Invalid Semantic Bridge IR: language must be python")
    if not isinstance(bridge["gap_types"], list) or not bridge["gap_types"]:
        raise ValueError("Invalid Semantic Bridge IR: gap_types must be a non-empty list")
