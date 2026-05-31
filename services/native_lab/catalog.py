from __future__ import annotations

from dataclasses import asdict
from typing import Any

from services.native_lab.models import NativeStrategyRecord
from services.native_lab.storage import (
    CATALOG_PATH,
    atomic_update,
    get_catalog as _catalog,
    save_catalog as _save_catalog,
)


def list_native_strategy_records() -> list[dict]:
    return _catalog()


def get_native_strategy_record(strategy_id: str) -> dict | None:
    for record in _catalog():
        if record.get("strategy_id") == strategy_id:
            return record
    return None


def upsert_native_strategy_record(record: NativeStrategyRecord | dict[str, Any]) -> dict:
    payload = asdict(record) if isinstance(record, NativeStrategyRecord) else dict(record)
    
    with atomic_update(CATALOG_PATH) as records:
        for idx, existing in enumerate(records):
            if existing.get("strategy_id") == payload["strategy_id"]:
                records[idx] = payload
                return payload
        records.append(payload)
    
    return payload


def update_native_strategy_status(strategy_id: str, *, status: str, notes: str | None = None) -> dict | None:
    record = get_native_strategy_record(strategy_id)
    if not record:
        return None
    record["status"] = status
    if notes is not None:
        record["notes"] = notes
    return upsert_native_strategy_record(record)


def update_native_strategy_mt5_validation(
    strategy_id: str,
    *,
    mt5_backtest: dict[str, Any] | None = None,
    mt5_comparison: dict[str, Any] | None = None,
    # Compatibility with older signature
    report_path: str | None = None,
    metrics: dict[str, Any] | None = None,
    comparison: dict[str, Any] | None = None,
    accepted: bool | None = None,
) -> dict | None:
    record = get_native_strategy_record(strategy_id)
    if not record:
        return None

    if mt5_backtest is None and metrics is not None:
        mt5_backtest = metrics
    if mt5_comparison is None and comparison is not None:
        mt5_comparison = comparison

    if mt5_backtest:
        record["mt5_backtest"] = mt5_backtest
    if mt5_comparison:
        record["mt5_comparison"] = mt5_comparison
    if report_path or accepted is not None:
        val = record.get("mt5_validation", {})
        if report_path: val["report_path"] = report_path
        if accepted is not None: val["accepted"] = accepted
        record["mt5_validation"] = val

    from services.native_lab.scoring import mt5_correlation_score
    record["mt5_correlation_score"] = mt5_correlation_score(mt5_comparison)
    return upsert_native_strategy_record(record)


def strategy_children(parent_strategy_id: str) -> list[dict]:
    return [r for r in _catalog() if r.get("parent_id") == parent_strategy_id]


def strategy_lineage_tree(strategy_id: str) -> list[dict]:
    records = _catalog()
    record_map = {r["strategy_id"]: r for r in records}
    tree = []
    curr = strategy_id
    while curr and curr in record_map:
        rec = record_map[curr]
        tree.append(rec)
        curr = rec.get("parent_id")
    return tree


def strategy_payload_diff(left_strategy_id: str, right_strategy_id: str) -> dict[str, Any]:
    left = get_native_strategy_record(left_strategy_id)
    right = get_native_strategy_record(right_strategy_id)
    if not left or not right:
        return {"payload_changed": False, "param_changes": []}
    l_pay = left.get("payload", {}) or left.get("template_payload", {})
    r_pay = right.get("payload", {}) or right.get("template_payload", {})
    
    diff = {"payload_changed": False, "param_changes": [], "structural_changes": []}
    all_keys = set(l_pay.keys()) | set(r_pay.keys())
    for k in all_keys:
        lv = l_pay.get(k)
        rv = r_pay.get(k)
        if lv != rv:
            diff["payload_changed"] = True
            if k == "params":
                l_params = lv or {}
                r_params = rv or {}
                all_p = set(l_params.keys()) | set(r_params.keys())
                for p in all_p:
                    if l_params.get(p) != r_params.get(p):
                        diff["param_changes"].append({"param": p, "left": l_params.get(p), "right": r_params.get(p)})
            else:
                diff["structural_changes"].append({"key": k, "left": lv, "right": rv})
    return diff
