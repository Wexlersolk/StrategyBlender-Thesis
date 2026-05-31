from __future__ import annotations

import copy
from typing import Any

from services.native_lab.config import (
    DEFAULT_PROMOTION_POLICY,
    DEFAULT_SCORING_PROFILE,
)
from services.native_lab.family_registry import FamilyRegistry
from services.native_lab.utils import get_by_path as _get_by_path


def _normalize_mutation_values(path: str, current: Any, values: list[Any]) -> list[Any]:
    deduped = []
    seen = set()
    if current is not None:
        deduped.append(current)
        seen.add(str(current))
    for v in values:
        vs = str(v)
        if vs not in seen:
            deduped.append(v)
            seen.add(vs)
    return deduped


def default_family_mutation_space(template_name: str, base_payload: dict[str, Any]) -> dict[str, list[Any]]:
    family = FamilyRegistry.get(template_name)
    configured = family.get_mutation_space() if family else {}
    mutations: dict[str, list[Any]] = {}
    for path, values in configured.items():
        current = _get_by_path(base_payload, path)
        deduped = _normalize_mutation_values(path, current, list(values))
        if len(deduped) > 1:
            mutations[path] = deduped
    return mutations


def default_structural_mutation_space(template_name: str, base_payload: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        path: values
        for path, values in default_family_mutation_space(template_name, base_payload).items()
        if not path.startswith("params.")
    }


def default_parameter_mutation_space(template_name: str, base_payload: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        path: values
        for path, values in default_family_mutation_space(template_name, base_payload).items()
        if path.startswith("params.")
    }


def _effective_mutation_space(
    template_name: str,
    base_payload: dict[str, Any],
    provided_space: dict[str, list[Any]] | None = None,
    *,
    include_structural_mutations: bool = True,
) -> dict[str, list[Any]]:
    if not provided_space:
        if include_structural_mutations:
            return default_family_mutation_space(template_name, base_payload)
        return default_parameter_mutation_space(template_name, base_payload)
    
    space = dict(provided_space)
    if include_structural_mutations:
        default_struct = default_structural_mutation_space(template_name, base_payload)
        for k, v in default_struct.items():
            if k not in space:
                space[k] = v
    return space


def default_param_grid(params: dict[str, Any], *, numeric_limit: int = 4) -> dict[str, list[Any]]:
    grid: dict[str, list[Any]] = {}
    for key, val in params.items():
        if isinstance(val, bool):
            grid[key] = [True, False]
        elif isinstance(val, (int, float)):
            # Simple step grid
            grid[key] = [val * 0.8, val, val * 1.2]
    return grid


def default_wfo_param_grid_for_template(template_name: str, params: dict[str, Any]) -> dict[str, list[Any]]:
    family = FamilyRegistry.get(template_name)
    configured = family.get_wfo_param_grid() if family else {}
    if configured:
        return {k: v for k, v in configured.items() if k in params}
    return default_param_grid(params)


def default_promotion_policy_for_template(template_name: str) -> dict[str, Any]:
    family = FamilyRegistry.get(template_name)
    policy = copy.deepcopy(DEFAULT_PROMOTION_POLICY)
    if family:
        policy.update(family.get_promotion_policy())
    return policy


def resolve_promotion_policy(record: dict[str, Any]) -> dict[str, Any]:
    policy = default_promotion_policy_for_template(str(record.get("template_name", "")))
    policy.update(record.get("promotion_policy", {}) or {})
    return policy


def default_scoring_profile_for_template(template_name: str) -> dict[str, Any]:
    family = FamilyRegistry.get(template_name)
    profile = copy.deepcopy(DEFAULT_SCORING_PROFILE)
    if family:
        profile.update(family.get_scoring_profile())
    return profile
