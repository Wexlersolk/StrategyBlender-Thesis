from __future__ import annotations

from typing import Any

# Re-exporting everything for backward compatibility and a clean facade

from services.python_strategy_service import PRESET_DIR
from services.native_lab.config import (
    BATCH_RUNS_PATH,
    CATALOG_PATH,
    GENERATOR_RUNS_PATH,
    LAB_DIR,
)
from engine.data_loader import load_bars
from services.backtest_service import (
    backtest_result_payload,
    run_backtest,
)
from services.native_lab.analysis import (
    archetype_bucket as _archetype_bucket,
    behavioral_fingerprint as _behavioral_fingerprint,
    fast_filter_behavioral_duplicates as _fast_filter_behavioral_duplicates,
    load_fast_filter_df as _load_fast_filter_df,
    structural_signature as _structural_signature,
)
from services.native_lab.batch import (
    create_batch_run,
    evaluate_batch_run,
    generate_batch_candidates,
    get_batch_run,
    list_batch_runs,
    rank_batch_candidates,
    run_batch_generation,
)
from services.native_lab.catalog import (
    get_native_strategy_record,
    list_native_strategy_records,
    strategy_children,
    strategy_lineage_tree,
    strategy_payload_diff,
    update_native_strategy_mt5_validation,
    update_native_strategy_status,
    upsert_native_strategy_record,
)
from services.native_lab.evaluation import (
    evaluate_native_strategy,
    register_generated_strategy,
    regenerate_native_strategy_version,
)
from services.native_lab.generator import (
    _bucket_limit,
    _generator_execution_config,
    _get_global_seen_signatures,
    _reject_generator_payload,
    _sample_generator_candidate,
    _seed_generator_payload,
    _structural_signature_limit,
    _top_generator_candidates,
    get_generator_run,
    list_generator_runs,
    run_generator_session,
    upsert_generator_run,
)
from services.native_lab.mutation import (
    default_family_mutation_space,
    default_parameter_mutation_space,
    default_promotion_policy_for_template,
    default_scoring_profile_for_template,
    default_structural_mutation_space,
    default_wfo_param_grid_for_template,
)
from services.native_lab.runtime import (
    load_runtime_strategy_class as _load_runtime_strategy_class,
)
from services.native_lab.scoring import (
    mt5_correlation_score as _mt5_correlation_score,
    param_stability_score as _param_stability_score,
    score_candidate as _score_candidate,
    suspicious_score as _suspicious_score,
)


def save_custom_preset(*, label: str, description: str, template_name: str, payload: dict[str, Any]) -> str:
    import json
    from pathlib import Path
    from services.python_strategy_service import PRESET_DIR
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in label).strip("_") or "preset"
    path = PRESET_DIR / f"{slug}.json"
    body = {
        "label": label,
        "description": description,
        "template": template_name,
        "payload": payload,
    }
    path.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return str(path)


# Backward compatibility for private helpers if needed by tests or other modules
def _effective_mutation_space(*args, **kwargs):
    from services.native_lab.mutation import _effective_mutation_space as _ems
    return _ems(*args, **kwargs)

def _load_compiled_class(*args, **kwargs):
    from services.native_lab.runtime import load_compiled_class
    return load_compiled_class(*args, **kwargs)

def _compile_runtime_strategy(*args, **kwargs):
    from services.native_lab.runtime import compile_runtime_strategy
    return compile_runtime_strategy(*args, **kwargs)
