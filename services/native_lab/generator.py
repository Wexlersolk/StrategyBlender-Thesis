from __future__ import annotations

import copy
import random
import sys
from datetime import datetime, timezone
from typing import Any

from services.backtest_service import resolve_execution_config
from services.native_lab.analysis import (
    archetype_bucket,
    behavioral_fingerprint,
    load_fast_filter_df,
    structural_signature,
)
from services.native_lab.batch import rank_batch_candidates
from services.native_lab.catalog import (
    upsert_native_strategy_record,
)
from services.native_lab.evaluation import (
    evaluate_native_strategy,
    register_generated_strategy,
)
from services.native_lab.storage import (
    GENERATOR_RUNS_PATH,
    atomic_update,
    get_catalog as _catalog,
    get_generator_runs as _generator_runs,
    save_generator_runs as _save_generator_runs,
)
from services.native_lab.mutation import (
    default_promotion_policy_for_template,
    _effective_mutation_space as effective_mutation_space,
)
from services.native_lab.utils import get_by_path, set_by_path, stable_hash, utc_now


def list_generator_runs() -> list[dict]:
    return _generator_runs()


def get_generator_run(run_id: str) -> dict | None:
    for record in _generator_runs():
        if record.get("run_id") == run_id:
            return record
    return None


def upsert_generator_run(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    with atomic_update(GENERATOR_RUNS_PATH) as records:
        for idx, existing in enumerate(records):
            if existing.get("run_id") == payload.get("run_id"):
                records[idx] = payload
                return payload
        records.append(payload)
    return payload


def _top_generator_candidates(candidates: list[dict[str, Any]], *, limit: int = 25) -> list[dict[str, Any]]:
    ranked = rank_batch_candidates(candidates)
    return ranked[: max(1, int(limit))]


def _generator_execution_config(symbol: str) -> dict[str, Any]:
    config = resolve_execution_config(symbol)
    normalized = str(symbol or "").strip().upper()
    if normalized == "XAUUSD":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.15, 0.20), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.25, 0.03), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.15), 5)
    elif normalized == "HK50.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.5, 4.5), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 3.5, 1.5), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.5), 5)
    elif normalized == "US100.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.20, 0.85), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.5, 0.35), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.25), 5)
    elif normalized == "US30.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.30, 3.5), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 3.0, 1.5), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.35), 5)
    elif normalized == "US500.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.10, 0.6), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.0, 0.2), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.10), 5)
    elif normalized == "GER40.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.20, 1.5), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.5, 1.0), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.20), 5)
    elif normalized == "USOIL.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.25, 0.05), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 3.0, 0.03), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.30), 5)
    elif normalized == "USDJPY":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.25, 0.009), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.0, 0.002), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.25), 5)
    elif normalized == "GBPJPY":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.35, 0.015), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.5, 0.005), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.35), 5)
    elif normalized == "UK100.CASH":
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.25, 2.5), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 3.0, 1.5), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.30), 5)
    elif normalized in {"EURUSD", "GBPUSD"}:
        config["spread_pips"] = round(max(float(config["spread_pips"]) * 1.20, 0.00011), 5)
        config["slippage_pips"] = round(max(float(config["slippage_pips"]) * 2.0, 0.00003), 5)
        config["bar_spread_multiplier"] = round(max(float(config.get("bar_spread_multiplier", 1.0)), 1.20), 5)
    return config


def _get_global_seen_signatures() -> set[str]:
    records = _catalog()
    signatures = set()
    for record in records:
        lineage = record.get("lineage", {})
        if isinstance(lineage, dict) and lineage.get("structural_signature"):
            signatures.add(str(lineage["structural_signature"]))
    return signatures


def _structural_signature_limit(template_name: str, max_candidates: int = 500) -> int:
    normalized = str(template_name or "").strip()
    # For templates with structural mutations, we want to force some diversity,
    # but we allow enough for a decent parameter search within that structure.
    return max(32, (max_candidates // 3) + 1)


def _bucket_limit(template_name: str, max_candidates: int) -> int:
    normalized = str(template_name or "").strip()
    return max(64, (max_candidates // 2) + 1)


def _reject_generator_payload(template_name: str, payload: dict[str, Any]) -> bool:
    normalized = str(template_name or "").strip()
    if normalized == "xau_discovery_grammar":
        entry_archetype = str(payload.get("entry_archetype", ""))
        volatility_filter = str(payload.get("volatility_filter", ""))
        session_filter = str(payload.get("session_filter", ""))
        stop_model = str(payload.get("stop_model", ""))
        target_model = str(payload.get("target_model", ""))
        if entry_archetype == "atr_pullback_limit":
            return True
        if session_filter == "london_only" and volatility_filter == "none":
            return True
        if session_filter == "london_only" and stop_model == "swing":
            return True
        if session_filter == "london_only" and target_model == "fixed_rr":
            return True
    return False


def _seed_generator_payload(
    *,
    base_payload: dict[str, Any],
    effective_space: dict[str, list[Any]],
    keys: list[str],
    rng: random.Random,
    generation_style: str,
    elite_payloads: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if generation_style != "sqx_like" or not elite_payloads:
        return copy.deepcopy(base_payload), {}

    parent_a = copy.deepcopy(rng.choice(elite_payloads))
    parent_b = copy.deepcopy(rng.choice(elite_payloads)) if len(elite_payloads) > 1 else copy.deepcopy(base_payload)
    payload = copy.deepcopy(parent_a)
    seeded_changes: dict[str, Any] = {}

    crossover_budget = max(1, min(len(keys), 2 if len(keys) < 4 else 4))
    crossover_keys = rng.sample(keys, k=crossover_budget)
    for key in crossover_keys:
        base_value = get_by_path(base_payload, key)
        value_a = get_by_path(parent_a, key)
        value_b = get_by_path(parent_b, key)
        chosen = value_a if rng.random() < 0.5 else value_b
        if isinstance(chosen, (int, float)) and isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)) and value_a != value_b and rng.random() < 0.35:
            blended = (float(value_a) + float(value_b)) / 2.0
            if isinstance(base_value, int):
                chosen = int(round(blended))
            else:
                chosen = round(float(blended), 6)
        allowed = effective_space.get(key, [])
        if allowed and chosen not in allowed:
            chosen = min(allowed, key=lambda item: abs(float(item) - float(chosen))) if isinstance(chosen, (int, float)) else rng.choice(allowed)
        if chosen is None:
            continue
        set_by_path(payload, key, chosen)
        if chosen != base_value:
            seeded_changes[key] = chosen

    if rng.random() < 0.35:
        inject_key = rng.choice(keys)
        options = [value for value in effective_space[inject_key] if value != get_by_path(payload, inject_key)]
        if options:
            chosen = rng.choice(options)
            set_by_path(payload, inject_key, chosen)
            if chosen != get_by_path(base_payload, inject_key):
                seeded_changes[inject_key] = chosen

    return payload, seeded_changes


def _sample_generator_candidate(
    *,
    template_name: str,
    base_payload: dict[str, Any],
    mutation_space: dict[str, list[Any]],
    include_structural_mutations: bool,
    rng: random.Random,
    discovery_mode: str,
    seen_hashes: set[str],
    generation_style: str = "random_mutation",
    elite_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    effective = effective_mutation_space(
        template_name,
        base_payload,
        mutation_space,
        include_structural_mutations=include_structural_mutations,
    )
    keys = sorted(effective)
    if not keys:
        return None

    max_changes = min(len(keys), 2 if discovery_mode == "conservative" else 3 if discovery_mode == "balanced" else 5)
    min_changes = 1
    if max_changes < 1:
        return None

    for _ in range(50):
        payload, seeded_changes = _seed_generator_payload(
            base_payload=base_payload,
            effective_space=effective,
            keys=keys,
            rng=rng,
            generation_style=generation_style,
            elite_payloads=elite_payloads or [],
        )
        chosen_keys = list(seeded_changes)
        remaining_keys = [key for key in keys if key not in chosen_keys]
        target_change_count = rng.randint(min_changes, max_changes)
        if len(chosen_keys) < target_change_count and remaining_keys:
            chosen_keys.extend(rng.sample(remaining_keys, k=min(len(remaining_keys), target_change_count - len(chosen_keys))))
        lineage_mutations: dict[str, Any] = {}
        changed_paths: list[str] = []
        for key in chosen_keys:
            current = get_by_path(payload, key)
            options = [value for value in effective[key] if value != current]
            if not options:
                continue
            if key in seeded_changes and current != get_by_path(base_payload, key):
                value = current
            else:
                value = rng.choice(options)
            set_by_path(payload, key, value)
            lineage_mutations[key] = value
            changed_paths.append(key)
        if not changed_paths:
            continue
        candidate_hash = stable_hash({"template": template_name, "payload": payload})
        if candidate_hash in seen_hashes:
            continue
        seen_hashes.add(candidate_hash)
        return {
            "candidate_id": f"cand_{candidate_hash}",
            "payload": payload,
            "mutations": lineage_mutations,
            "mutation_distance": len(changed_paths),
            "structural_changes": [path for path in changed_paths if not path.startswith("params.")],
        }
    return None


def run_generator_session(
    *,
    template_name: str,
    base_payload: dict[str, Any],
    mutation_space: dict[str, list[Any]],
    date_from: str,
    date_to: str,
    retest_date_from: str | None = None,
    retest_date_to: str | None = None,
    max_candidates: int = 500,
    run_mc: bool = False,
    run_wfo_checks: bool = False,
    intrabar_steps: int = 60,
    include_structural_mutations: bool = True,
    discovery_mode: str = "conservative",
    generation_style: str = "random_mutation",
    random_seed: int = 42,
    progress_callback=None,
    use_global_seen_signatures: bool = True,
    resume: bool = False,
) -> dict[str, Any]:
    if not template_name:
        raise ValueError("Generator session requires template_name.")
    effective_space = effective_mutation_space(
        template_name,
        base_payload,
        mutation_space,
        include_structural_mutations=include_structural_mutations,
    )
    if not effective_space:
        raise ValueError("Generator session requires a non-empty mutation space.")

    max_candidates = max(1, int(max_candidates))
    rng = random.Random(int(random_seed))
    
    symbol = str(base_payload.get("symbol", "unknown")).upper()
    tf = str(base_payload.get("timeframe", "H1")).upper()
    
    run_hash = stable_hash({'template': template_name, 'payload': base_payload, 'seed': random_seed})[:6]
    
    run_record = None
    if resume:
        # Search for recent run with same run_hash and status != "completed"
        runs = list_generator_runs()
        for run in reversed(runs):
            if run.get("run_id", "").endswith(f"_{run_hash}") and run.get("status") != "completed":
                print(f">>> Resuming incomplete session: {run.get('run_id')}")
                run_record = run
                # Update status to running
                run_record["status"] = "running"
                run_record["stage"] = "running"
                run_record["updated_at"] = utc_now()
                upsert_generator_run(run_record)
                break
        
        if not run_record:
            print(">>> No resumeable session found. Starting fresh.")

    if not run_record:
        ts_id = datetime.now().strftime("%y%m%d_%H%M%S")
        run_id = f"gen_{symbol}_{tf}_{ts_id}_{run_hash}"
        
        run_record = {
            "run_id": run_id,
            "label": f"{symbol} {tf} | {template_name} | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "symbol": symbol,
            "timeframe": tf,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "finished_at": "",
            "template_name": template_name,
            "base_payload": copy.deepcopy(base_payload),
            "mutation_space": copy.deepcopy(mutation_space),
            "effective_mutation_space": copy.deepcopy(effective_space),
            "date_from": date_from,
            "date_to": date_to,
            "max_candidates": max_candidates,
            "intrabar_steps": int(intrabar_steps),
            "run_mc": bool(run_mc),
            "run_wfo_checks": bool(run_wfo_checks),
            "include_structural_mutations": bool(include_structural_mutations),
            "discovery_mode": discovery_mode,
            "generation_style": generation_style,
            "status": "running",
            "stage": "running",
            "attempted": 0,
            "duplicates": 0,
            "evaluated": 0,
            "accepted": 0,
            "best_score": 0.0,
            "best_strategy_id": "",
            "candidates": [],
            "leaderboard": [],
        }
        upsert_generator_run(run_record)

    seen_hashes: set[str] = set()
    seen_fingerprints: set[str] = set()
    global_signatures = _get_global_seen_signatures() if use_global_seen_signatures else set()
    structural_signature_counts: dict[str, int] = {sig: 1 for sig in global_signatures}
    bucket_counts: dict[str, int] = {}
    elite_pool: list[dict[str, Any]] = []

    # Reconstruct state if resuming
    if run_record.get("candidates"):
        print(f">>> Reconstructing state from {len(run_record['candidates'])} existing candidates...")
        for cand in run_record["candidates"]:
            # Reconstruct seen_hashes from strategy_id: cand_<hash>_<idx>
            parts = cand["strategy_id"].split("_")
            if len(parts) >= 2:
                seen_hashes.add(parts[1])
            
            if cand.get("behavioral_fingerprint"):
                seen_fingerprints.add(cand["behavioral_fingerprint"])
            
            if cand.get("structural_signature"):
                sig = cand["structural_signature"]
                structural_signature_counts[sig] = structural_signature_counts.get(sig, 0) + 1
        
        bucket_counts = dict(run_record.get("bucket_counts", {}))
        
        # Reconstruct elite_pool
        catalog_records = {r["strategy_id"]: r.get("payload", {}) for r in _catalog()}
        best_cands = sorted(run_record["candidates"], key=lambda x: float(x.get("score", 0.0)), reverse=True)[:12]
        for c in best_cands:
            payload = catalog_records.get(c["strategy_id"])
            if payload:
                elite_pool.append({"payload": payload, "score": float(c.get("score", 0.0))})

    df = load_fast_filter_df(str(base_payload.get("symbol", "")), str(base_payload.get("timeframe", "")))
    generation_execution_config = _generator_execution_config(str(base_payload.get("symbol", "")))
    
    if max_candidates <= 0:
        run_record["status"] = "completed"
        run_record["finished_at"] = datetime.now(timezone.utc).isoformat()
        upsert_generator_run(run_record)
        return run_record

    attempt_budget = max(max_candidates * 12, 100)

    has_structural_mutations = any(not k.startswith("params.") for k in effective_space)
    struct_sig_limit = _structural_signature_limit(template_name, max_candidates)
    if not has_structural_mutations or generation_style == "sqx_like":
        # If no structural mutations are possible, or we are doing a deep parameter search
        # via sqx_like, we must allow multiple parameter sets for the same structure.
        struct_sig_limit = max(struct_sig_limit, max_candidates + 1)

    try:
        for attempt in range(run_record.get("attempted", 0) + 1, attempt_budget + 1):
            run_record["attempted"] = attempt
            if progress_callback:
                progress_callback(
                    run_record["evaluated"] / max_candidates,
                    "generating",
                    f"Generated {run_record['evaluated']}/{max_candidates} unique candidates after {attempt} attempts.",
                )
            candidate = _sample_generator_candidate(
                template_name=template_name,
                base_payload=base_payload,
                mutation_space=mutation_space,
                include_structural_mutations=include_structural_mutations,
                rng=rng,
                discovery_mode=discovery_mode,
                seen_hashes=seen_hashes,
                generation_style=generation_style,
                elite_payloads=[item["payload"] for item in elite_pool],
            )
            if candidate is None:
                continue
            if _reject_generator_payload(template_name, candidate["payload"]):
                run_record["duplicates"] += 1
                continue
            arch_bucket = archetype_bucket(template_name, candidate["payload"])
            struct_sig = structural_signature(template_name, candidate["payload"])
            bucket_lim = _bucket_limit(template_name, max_candidates)
            if bucket_counts.get(arch_bucket, 0) >= bucket_lim:
                run_record["duplicates"] += 1
                continue
            if structural_signature_counts.get(struct_sig, 0) >= struct_sig_limit:
                run_record["duplicates"] += 1
                continue
            fingerprint = behavioral_fingerprint(candidate["payload"], template_name, df)
            if fingerprint in seen_fingerprints:
                run_record["duplicates"] += 1
                continue
            seen_fingerprints.add(fingerprint)
            bucket_counts[arch_bucket] = bucket_counts.get(arch_bucket, 0) + 1
            structural_signature_counts[struct_sig] = structural_signature_counts.get(struct_sig, 0) + 1
            novelty_score = round(
                max(
                    0.2,
                    1.0
                    - (0.25 * max(0, structural_signature_counts.get(struct_sig, 1) - 1))
                    - (0.10 * max(0, bucket_counts.get(arch_bucket, 1) - 1)),
                ),
                4,
            )

            strategy_id = f"{candidate['candidate_id']}_{run_record['evaluated']:04d}"
            payload = copy.deepcopy(candidate["payload"])
            payload["name"] = f"{payload.get('name', template_name)} [G{run_record['evaluated'] + 1:04d}]"
            register_generated_strategy(
                template_name=template_name,
                payload=payload,
                strategy_id=strategy_id,
                origin="generator_run",
                lineage={
                    "generator_run_id": run_record["run_id"],
                    "mutations": candidate["mutations"],
                    "mutation_distance": candidate["mutation_distance"],
                    "structural_changes": candidate.get("structural_changes", []),
                    "archetype_bucket": arch_bucket,
                    "structural_signature": struct_sig,
                    "novelty_score": novelty_score,
                },
                tags=["generator", template_name],
                promotion_policy=dict(payload.get("promotion_policy", {}) or default_promotion_policy_for_template(template_name)),
            )
            evaluation = evaluate_native_strategy(
                strategy_id,
                date_from=date_from,
                date_to=date_to,
                intrabar_steps=intrabar_steps,
                run_mc=run_mc,
                run_wfo_checks=run_wfo_checks,
                execution_config=generation_execution_config,
            )
            candidate_record = {
                "strategy_id": strategy_id,
                "name": payload.get("name", strategy_id),
                "status": "evaluated",
                "evaluated": True,
                "template_name": template_name,
                "mutations": candidate["mutations"],
                "mutation_distance": candidate["mutation_distance"],
                "structural_changes": candidate.get("structural_changes", []),
                "behavioral_fingerprint": fingerprint,
                "archetype_bucket": arch_bucket,
                "structural_signature": struct_sig,
                "novelty_score": novelty_score,
                "score": evaluation.get("score", 0.0),
                "accepted": evaluation.get("accepted", False),
                "backtest": evaluation.get("backtest", {}),
                "wfo": evaluation.get("wfo", {}),
                "parameter_stability": evaluation.get("parameter_stability", {}),
                "monte_carlo": evaluation.get("monte_carlo", {}),
                "mt5_correlation_score": evaluation.get("mt5_correlation_score", 0.0),
                "suspicious_score": evaluation.get("suspicious_score", 0.0),
                "needs_mt5_validation": evaluation.get("needs_mt5_validation", False),
            }
            run_record["candidates"].append(candidate_record)
            run_record["evaluated"] += 1
            if candidate_record["accepted"]:
                run_record["accepted"] += 1
            if float(candidate_record.get("score", 0.0)) >= float(run_record.get("best_score", 0.0)):
                run_record["best_score"] = float(candidate_record.get("score", 0.0))
                run_record["best_strategy_id"] = strategy_id
            elite_pool.append({"payload": copy.deepcopy(candidate["payload"]), "score": float(candidate_record.get("score", 0.0))})
            elite_pool.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
            elite_pool = elite_pool[:12]
            run_record["leaderboard"] = _top_generator_candidates(run_record["candidates"])
            run_record["bucket_counts"] = dict(bucket_counts)
            run_record["updated_at"] = utc_now()
            upsert_generator_run(run_record)
            
            # Log progress to stdout
            status_char = "✓" if candidate_record["accepted"] else "✗"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {status_char} Eval {run_record['evaluated']}/{max_candidates}: {strategy_id} | Score: {candidate_record['score']:.2f} | PF: {candidate_record['backtest'].get('profit_factor', 0.0):.2f} | Trades: {candidate_record['backtest'].get('num_trades', 0)}")
            sys.stdout.flush()

            if run_record["evaluated"] >= max_candidates:
                break
    except KeyboardInterrupt:
        print("\n>>> Generation interrupted by user. Saving state...")
        run_record["status"] = "stopped"
        run_record["stage"] = "stopped"
        run_record["updated_at"] = utc_now()
        upsert_generator_run(run_record)
        return run_record

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto-retesting top candidates...")
    sys.stdout.flush()
    # Select the top candidates by score, regardless of accepted status, since accepted requires WFO/MC which haven't run yet.
    top_cands = sorted(run_record["candidates"], key=lambda x: float(x.get("score", 0.0)), reverse=True)[:5]
    
    for i, top_cand in enumerate(top_cands):
        print(f"  Retesting #{i+1}: {top_cand['strategy_id']} (Initial Score: {top_cand.get('score', 0.0):.2f})")
        sys.stdout.flush()
        try:
            retest_eval = evaluate_native_strategy(
                top_cand["strategy_id"],
                date_from=retest_date_from or date_from,
                date_to=retest_date_to or date_to,
                intrabar_steps=intrabar_steps,
                run_mc=run_mc,
                run_wfo_checks=run_wfo_checks,
                execution_config=generation_execution_config,
            )
            top_cand["wfo"] = retest_eval.get("wfo", {})
            top_cand["parameter_stability"] = retest_eval.get("parameter_stability", {})
            top_cand["monte_carlo"] = retest_eval.get("monte_carlo", {})
            top_cand["score"] = retest_eval.get("score", top_cand.get("score", 0.0))
            top_cand["accepted"] = retest_eval.get("accepted", top_cand.get("accepted", False))
            
            for cand in run_record["candidates"]:
                if cand["strategy_id"] == top_cand["strategy_id"]:
                    cand.update(top_cand)
                    break
        except Exception as e:
            print(f"  Failed to retest {top_cand['strategy_id']}: {e}")
            
    run_record["leaderboard"] = _top_generator_candidates(run_record["candidates"])

    run_record["updated_at"] = utc_now()
    run_record["finished_at"] = utc_now()
    run_record["status"] = "completed" if run_record["evaluated"] >= max_candidates else "stopped"
    run_record["stage"] = run_record["status"]
    upsert_generator_run(run_record)
    return run_record
