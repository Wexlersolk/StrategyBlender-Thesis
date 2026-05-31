from __future__ import annotations

import json
import os
import fcntl
import contextlib
from pathlib import Path
from typing import Any

from .config import CATALOG_PATH, BATCH_RUNS_PATH, GENERATOR_RUNS_PATH, LAB_DIR

def ensure_lab_dir():
    LAB_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path: Path, payload: Any):
    ensure_lab_dir()
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

@contextlib.contextmanager
def atomic_update(path: Path, default: Any = None):
    """
    Lock a JSON resource, load its content, allow modification via yield, 
    and save atomically before releasing the lock.
    """
    ensure_lab_dir()
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            data = load_json(path, default if default is not None else [])
            yield data
            save_json(path, data)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def get_catalog() -> list[dict]:
    return load_json(CATALOG_PATH, [])

def save_catalog(records: list[dict]):
    save_json(CATALOG_PATH, records)

def get_batch_runs() -> list[dict]:
    return load_json(BATCH_RUNS_PATH, [])

def save_batch_runs(records: list[dict]):
    save_json(BATCH_RUNS_PATH, records)

def get_generator_runs() -> list[dict]:
    return load_json(GENERATOR_RUNS_PATH, [])

def save_generator_runs(records: list[dict]):
    save_json(GENERATOR_RUNS_PATH, records)
