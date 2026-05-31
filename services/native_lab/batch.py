from __future__ import annotations

import copy
import itertools
from typing import Any

from services.native_lab.analysis import fast_filter_behavioral_duplicates
from services.native_lab.mutation import default_family_mutation_space
from services.native_lab.storage import (
    BATCH_RUNS_PATH,
    atomic_update,
    get_batch_runs as _batch_runs,
    save_batch_runs as _save_batch_runs,
    save_json as _save_json,
)
from services.native_lab.utils import get_by_path as _get_by_path, set_by_path as _set_by_path, stable_hash as _stable_hash, utc_now as _utc_now


def generate_batch_candidates(
    *,
    template_name: str,
    base_payload: dict[str, Any],
    mutation_space: dict[str, list[Any]],
    limit: int = 50,
    search_mode: str = "grid",
    random_seed: int = 42,
    include_structural_mutations: bool = False,
) -> list[dict[str, Any]]:
    from services.native_lab.mutation import _effective_mutation_space
    mutation_space = _effective_mutation_space(
        template_name,
        base_payload,
        mutation_space,
        include_structural_mutations=include_structural_mutations,
    )
    keys = sorted(mutation_space)
    if not keys:
        return []
    candidates: list[dict[str, Any]] = []
    combos = list(itertools.product(*(mutation_space[key] for key in keys)))
    if search_mode == "random":
        combos.sort(key=lambda combo: _stable_hash({"combo": combo, "seed": int(random_seed)}))
    elif search_mode == "progressive":
        base_combo = tuple(
            _get_by_path(base_payload, key)
            for key in keys
        )
        combos.sort(key=lambda combo: sum(0 if combo[idx] == base_combo[idx] else 1 for idx in range(len(keys))))
    seen_hashes: set[str] = set()
    for combo in combos[: int(limit)]:
        payload = copy.deepcopy(base_payload)
        lineage_mutations: dict[str, Any] = {}
        mutation_distance = 0
        changed_paths: list[str] = []
        for key, value in zip(keys, combo):
            target_path = key
            _set_by_path(payload, target_path, value)
            lineage_mutations[key] = value
            base_value = _get_by_path(base_payload, target_path)
            if value != base_value:
                mutation_distance += 1
                changed_paths.append(key)
        candidate_hash = _stable_hash({"template": template_name, "payload": payload})
        if candidate_hash in seen_hashes:
            continue
        seen_hashes.add(candidate_hash)
        candidates.append(
            {
                "candidate_id": f"cand_{candidate_hash}",
                "strategy_id": f"cand_{candidate_hash}",
                "template_name": template_name,
                "payload": payload,
                "mutations": lineage_mutations,
                "mutation_distance": mutation_distance,
                "structural_changes": [path for path in changed_paths if "." in path or path in {"direction", "expiry_bars", "min_bars"}],
            }
        )
    return candidates


def create_batch_run(
    *,
    template_name: str,
    base_payload: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
    date_from: str = "",
    date_to: str = "",
    intrabar_steps: int = 1,
    mutation_space: dict[str, list[Any]] | None = None,
    limit: int | None = None,
) -> str:
    duplicates = []
    requested_count = len(candidates) if candidates is not None else 0
    if candidates is None:
        candidates = generate_batch_candidates(
            template_name=template_name,
            base_payload=base_payload,
            mutation_space=mutation_space or {},
            limit=limit or 50,
        )
        requested_count = len(candidates)
        # Filter duplicates if generated internally
        candidates, duplicates = fast_filter_behavioral_duplicates(candidates=candidates, template_name=template_name)
    
    symbol = str(base_payload.get("symbol", "unknown")).upper()
    tf = str(base_payload.get("timeframe", "H1")).upper()
    ts_id = _utc_now().replace("-", "").replace(":", "").split(".")[0].replace("T", "_")[2:] # Short TS
    batch_hash = _stable_hash({'template': template_name, 'payload': base_payload})[:6]
    batch_id = f"batch_{symbol}_{tf}_{ts_id}_{batch_hash}"

    record = {
        "batch_id": batch_id,
        "label": f"{symbol} {tf} | {template_name} | {_utc_now()[:16].replace('T', ' ')}",
        "symbol": symbol,
        "timeframe": tf,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "template_name": template_name,
        "base_payload": base_payload,
        "mutation_space": mutation_space or {},
        "date_from": date_from,
        "date_to": date_to,
        "intrabar_steps": int(intrabar_steps),
        "status": "created",
        "candidates": candidates,
        "duplicate_candidates": duplicates,
        "requested_candidates": requested_count,
        "generated_candidates": len(candidates),
    }
    with atomic_update(BATCH_RUNS_PATH) as runs:
        runs.append(record)
    
    # Register candidates in the catalog so they are available immediately
    from services.native_lab.evaluation import register_generated_strategy
    from services.native_lab.catalog import get_native_strategy_record
    from services.native_lab.mutation import default_promotion_policy_for_template
    
    for c in record["candidates"]:
        if not get_native_strategy_record(c["strategy_id"]):
            try:
                register_generated_strategy(
                    template_name=record["template_name"],
                    payload=c["payload"],
                    strategy_id=c["strategy_id"],
                    origin="batch_run",
                    lineage={
                        "batch_id": batch_id,
                        "mutations": c["mutations"],
                        "mutation_distance": c["mutation_distance"],
                        "structural_changes": c["structural_changes"],
                    },
                    tags=["batch", record["template_name"]],
                    promotion_policy=default_promotion_policy_for_template(record["template_name"]),
                )
            except Exception:
                # In some test environments, directory structures might be mocked or missing
                pass

    return record


def list_batch_runs() -> list[dict]:
    return _batch_runs()


def get_batch_run(batch_id: str) -> dict | None:
    for run in _batch_runs():
        if run.get("batch_id") == batch_id:
            return run
    return None


def evaluate_batch_run(
    batch_id: str,
    *,
    run_mc: bool = True,
    run_wfo_checks: bool = True,
    progress_callback=None,
) -> dict:
    from services.native_lab.evaluation import evaluate_native_strategy
    
    with atomic_update(BATCH_RUNS_PATH) as runs:
        run = next((r for r in runs if r.get("batch_id") == batch_id), None)
        if not run:
            raise ValueError(f"Unknown batch: {batch_id}")
        run["status"] = "evaluating"
        run["updated_at"] = _utc_now()
        # Create a deep copy for local processing to avoid working on the locked list directly 
        # (though yield handles the lock duration, we want to unlock during evaluation)
        local_run = copy.deepcopy(run)

    candidates = local_run["candidates"]
    total = len(candidates)
    for idx, c in enumerate(candidates):
        if progress_callback:
            progress_callback(idx / total, "evaluating", f"Evaluating {idx+1}/{total}: {c['candidate_id']}")
        strategy_id = c["candidate_id"]
        from services.native_lab.catalog import get_native_strategy_record
        from services.native_lab.mutation import default_promotion_policy_for_template
        from services.native_lab.evaluation import register_generated_strategy
        if not get_native_strategy_record(strategy_id):
            register_generated_strategy(
                template_name=local_run["template_name"],
                payload=c["payload"],
                strategy_id=strategy_id,
                origin="batch_run",
                lineage={
                    "batch_id": batch_id,
                    "mutations": c["mutations"],
                    "mutation_distance": c["mutation_distance"],
                    "structural_changes": c["structural_changes"],
                },
                tags=["batch", local_run["template_name"]],
                promotion_policy=default_promotion_policy_for_template(local_run["template_name"]),
            )
        eval_result = evaluate_native_strategy(
            strategy_id,
            date_from=local_run["date_from"],
            date_to=local_run["date_to"],
            intrabar_steps=local_run["intrabar_steps"],
            run_mc=run_mc,
            run_wfo_checks=run_wfo_checks,
        )
        c.update(eval_result)
        
        # Save progress atomically for each candidate
        with atomic_update(BATCH_RUNS_PATH) as runs:
            target_run = next((r for r in runs if r.get("batch_id") == batch_id), None)
            if target_run:
                target_run["candidates"][idx].update(eval_result)
                target_run["updated_at"] = _utc_now()

    with atomic_update(BATCH_RUNS_PATH) as runs:
        target_run = next((r for r in runs if r.get("batch_id") == batch_id), None)
        if target_run:
            target_run["status"] = "completed"
            target_run["updated_at"] = _utc_now()
            target_run["finished_at"] = _utc_now()
            local_run = target_run
            
    return local_run


def rank_batch_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)
    for c in ranked:
        score = float(c.get("score", 0.0))
        if score >= 60:
            c["quality_bucket"] = "promote"
        elif score >= 45:
            c["quality_bucket"] = "evaluate"
        else:
            c["quality_bucket"] = "reject"
    return ranked


def run_batch_generation(
    *,
    template_name: str,
    base_payload: dict[str, Any],
    mutation_space: dict[str, list[Any]],
    date_from: str,
    date_to: str,
    limit: int = 50,
    search_mode: str = "grid",
    intrabar_steps: int = 1,
    run_mc: bool = True,
    run_wfo_checks: bool = True,
    filter_duplicates: bool = True,
) -> str:
    candidates = generate_batch_candidates(
        template_name=template_name,
        base_payload=base_payload,
        mutation_space=mutation_space,
        limit=limit * 3 if filter_duplicates else limit,
        search_mode=search_mode,
    )
    if filter_duplicates:
        kept, _ = fast_filter_behavioral_duplicates(candidates=candidates, template_name=template_name)
        candidates = kept[:limit]
    batch_record = create_batch_run(
        template_name=template_name,
        base_payload=base_payload,
        candidates=candidates,
        date_from=date_from,
        date_to=date_to,
        intrabar_steps=intrabar_steps,
    )
    evaluate_batch_run(batch_record["batch_id"], run_mc=run_mc, run_wfo_checks=run_wfo_checks)
    return batch_record["batch_id"]
