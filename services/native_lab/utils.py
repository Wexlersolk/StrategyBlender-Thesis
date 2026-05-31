from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def stable_hash(payload: dict[str, Any]) -> str:
    dumped = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

def get_by_path(payload: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    curr = payload
    for part in parts:
        if not isinstance(curr, dict) or part not in curr:
            return None
        curr = curr[part]
    return curr

def set_by_path(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    curr = payload
    for part in parts[:-1]:
        if part not in curr:
            curr[part] = {}
        curr = curr[part]
    curr[parts[-1]] = value
