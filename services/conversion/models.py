from dataclasses import dataclass

@dataclass
class ConvertedEA:
    params: dict
    review_source: str
    engine_source: str
    warnings: list[str]
    functions: list[str]
    strategy_path: str
    strategy_module: str
    strategy_class: str
    strategy_slug: str
