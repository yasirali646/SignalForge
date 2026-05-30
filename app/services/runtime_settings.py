"""Persist user-tunable settings (scheduler, etc.) across API restarts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SETTINGS_PATH = _PROJECT_ROOT / "data" / "runtime_settings.json"

ALLOWED_KEYS = frozenset({"scheduler_enabled", "scheduler_interval_hours"})


def _ensure_data_dir() -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_overrides() -> dict[str, Any]:
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return {k: data[k] for k in ALLOWED_KEYS if k in data}
    except (json.JSONDecodeError, OSError):
        return {}


def save_overrides(updates: dict[str, Any]) -> dict[str, Any]:
    _ensure_data_dir()
    current = load_overrides()
    for key, value in updates.items():
        if key in ALLOWED_KEYS:
            current[key] = value
    _SETTINGS_PATH.write_text(
        json.dumps(current, indent=2) + "\n",
        encoding="utf-8",
    )
    return current
