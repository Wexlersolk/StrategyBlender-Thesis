from __future__ import annotations

import importlib
import sys
from typing import Any
from pathlib import Path

from services.python_strategy_service import (
    StrategySpec,
    compile_strategy_spec,
    strategy_spec_from_template,
)

ROOT = Path(__file__).resolve().parent.parent.parent

def load_compiled_class(module_name: str, class_name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def compile_runtime_strategy(spec: StrategySpec, strategy_id: str):
    compiled = compile_strategy_spec(spec, strategy_id=f"{strategy_id}_fingerprint")
    with open("debug_strat.py", "w") as f:
        f.write(compiled.source)
    namespace: dict[str, Any] = {"__name__": f"_native_strategy_lab_{compiled.strategy_slug}"}
    exec(compiled.source, namespace)
    return namespace[compiled.strategy_class]


def load_runtime_strategy_class(record: dict[str, Any]):
    template_name = str(record.get("template_name", "") or "")
    template_payload = record.get("template_payload")
    if template_name and isinstance(template_payload, dict) and template_payload:
        spec = strategy_spec_from_template(template_name, template_payload)
        return compile_runtime_strategy(spec, str(record.get("strategy_id", "runtime")))
    return load_compiled_class(record["strategy_module"], record["strategy_class"])
