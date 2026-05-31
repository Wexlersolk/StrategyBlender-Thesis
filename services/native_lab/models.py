from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class NativeStrategyRecord:
    strategy_id: str
    created_at: str
    updated_at: str
    name: str
    template_name: str
    origin: str
    symbol: str
    timeframe: str
    status: str
    params: dict[str, Any]
    template_payload: dict[str, Any]
    lineage: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    strategy_path: str = ""
    spec_path: str = ""
    strategy_module: str = ""
    strategy_class: str = ""
    notes: str = ""
    promotion_policy: dict[str, Any] = field(default_factory=dict)
    scoring_profile: dict[str, Any] = field(default_factory=dict)
