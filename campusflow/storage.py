"""Small local JSON persistence helpers (single-user prototype)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("campusflow_data.json")

def save_state(state: dict[str, Any], path: str | Path = DEFAULT_PATH) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, indent=2), encoding="utf-8")

def load_state(path: str | Path = DEFAULT_PATH) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))
