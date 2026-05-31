from __future__ import annotations

from pathlib import Path

from convert.mt5_to_python import ConversionResult, convert_mql5_to_python
from services.conversion.models import ConvertedEA
from services.conversion.templates import _build_engine_strategy_source
from services.conversion.utils import (
    CONVERTED_DIR,
    _generated_strategy_dir,
    _generated_strategy_module,
    class_name_from_slug,
    normalize_symbol,
    slugify,
)


def convert_ea_source(
    *,
    source: str,
    strategy_name: str,
    symbol: str,
    timeframe: str,
    ea_id: str | None = None,
) -> ConvertedEA:
    review_result: ConversionResult = convert_mql5_to_python(
        source=source,
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
    )

    slug_base = slugify(f"{strategy_name}_{ea_id or symbol}_{timeframe}")
    class_name = class_name_from_slug(slug_base)
    engine_source, engine_warnings = _build_engine_strategy_source(
        strategy_name=strategy_name,
        class_name=class_name,
        symbol=symbol,
        timeframe=timeframe,
        params=review_result.inputs,
        mql_source=source,
    )

    strategy_path = _generated_strategy_dir(symbol, timeframe) / f"{slug_base}.py"
    return ConvertedEA(
        params=review_result.inputs,
        review_source=review_result.review_source,
        engine_source=engine_source,
        warnings=[*review_result.warnings, *engine_warnings],
        functions=review_result.functions,
        strategy_path=str(strategy_path),
        strategy_module=_generated_strategy_module(symbol, timeframe, slug_base),
        strategy_class=class_name,
        strategy_slug=slug_base,
    )


def persist_converted_ea(result: ConvertedEA, strategy_name: str):
    CONVERTED_DIR.mkdir(parents=True, exist_ok=True)
    Path(result.strategy_path).parent.mkdir(parents=True, exist_ok=True)

    review_path = CONVERTED_DIR / f"{slugify(strategy_name)}.py"
    review_path.write_text(result.review_source, encoding="utf-8")
    Path(result.strategy_path).write_text(result.engine_source, encoding="utf-8")
    return {
        "review_path": str(review_path),
        "engine_path": result.strategy_path,
    }
