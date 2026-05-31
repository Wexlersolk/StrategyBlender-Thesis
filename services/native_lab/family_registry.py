from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategyFamily:
    name: str
    mutation_space: dict[str, list[Any]] = field(default_factory=dict)
    wfo_param_grid: dict[str, list[Any]] = field(default_factory=dict)
    scoring_profile: dict[str, Any] = field(default_factory=dict)
    promotion_policy: dict[str, Any] = field(default_factory=dict)

    def get_mutation_space(self) -> dict[str, list[Any]]:
        return copy.deepcopy(self.mutation_space)

    def get_wfo_param_grid(self) -> dict[str, list[Any]]:
        return copy.deepcopy(self.wfo_param_grid)

    def get_scoring_profile(self) -> dict[str, Any]:
        return copy.deepcopy(self.scoring_profile)

    def get_promotion_policy(self) -> dict[str, Any]:
        return copy.deepcopy(self.promotion_policy)


class FamilyRegistry:
    _families: dict[str, StrategyFamily] = {}

    @classmethod
    def register(cls, family: StrategyFamily) -> None:
        cls._families[family.name] = family

    @classmethod
    def get(cls, name: str) -> StrategyFamily | None:
        return cls._families.get(name)

    @classmethod
    def all(cls) -> dict[str, StrategyFamily]:
        return cls._families.copy()


# Ensure all families are registered when the registry is imported
import services.native_lab.families  # noqa: E402, F401
