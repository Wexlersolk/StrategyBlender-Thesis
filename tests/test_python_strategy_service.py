import importlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.backtester import Backtester
from services.python_strategy_service import (
    available_builder_symbols,
    available_presets,
    EntryRuleSpec,
    IndicatorSpec,
    SeriesSpec,
    StrategySpec,
    available_template_names,
    canonical_symbol,
    compile_strategy_spec,
    persist_strategy_spec,
    strategy_spec_from_template,
    template_profile,
    template_supports_market,
)


def _load_generated_strategy(compiled):
    module_name = compiled.strategy_module
    module = (
        importlib.reload(sys.modules[module_name])
        if module_name in sys.modules
        else importlib.import_module(module_name)
    )
    return getattr(module, compiled.strategy_class)


def test_compile_sq_style_strategy_and_run_backtest():
    spec = StrategySpec(
        name="PySQX Rule Engine Test",
        symbol="EURUSD",
        timeframe="H1",
        params={
            "FastEMA": 3,
            "ATRPeriod": 3,
            "mmLots": 1.0,
            "StopLossATR": 1.0,
            "ProfitTargetATR": 1.5,
        },
        min_bars=6,
        indicators=[
            IndicatorSpec(
                name="ema_fast",
                kind="ema",
                args={"series": "close", "period": {"param": "FastEMA"}},
            ),
            IndicatorSpec(
                name="wavetrend",
                kind="sq_wave_trend",
                args={"high": "high", "low": "low", "close": "close", "channel_length": 4, "average_length": 6},
                outputs={"main": "wt_main", "signal": "wt_signal"},
            ),
            IndicatorSpec(
                name="bbwr",
                kind="sq_bb_width_ratio",
                args={"series": "close", "period": 5, "deviations": 2.0},
            ),
            IndicatorSpec(
                name="atr",
                kind="sq_atr",
                args={"high": "high", "low": "low", "close": "close", "period": {"param": "ATRPeriod"}},
            ),
        ],
        series=[
            SeriesSpec(
                name="long_signal",
                expression='(_count_compare(df["close"], df["ema_fast"], 2, 0, greater=True, allow_equal=True) | (df["close"] > df["ema_fast"])) & (df["wt_main"].fillna(0.0) > -1e9)',
            ),
        ],
        entries=[
            EntryRuleSpec(
                name="long_entry",
                side="long",
                order_type="market",
                when='bool(df["long_signal"].iloc[i])',
                lots='float(self.p("mmLots"))',
                stop_loss='ctx.open - float(df["atr"].iloc[i - 1]) * float(self.p("StopLossATR"))',
                take_profit='ctx.open + float(df["atr"].iloc[i - 1]) * float(self.p("ProfitTargetATR"))',
                comment="sq_long",
                exit_after_bars=2,
            )
        ],
        description="Test fixture for the StrategySpec SQ-like compiler.",
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sq_rule_engine")
    paths = persist_strategy_spec(compiled)

    try:
        assert Path(paths["strategy_path"]).exists()
        assert Path(paths["spec_path"]).exists()
        assert "sq_wave_trend" in compiled.source
        assert "_count_compare" in compiled.source

        strat_cls = _load_generated_strategy(compiled)

        index = pd.date_range("2024-01-01", periods=96, freq="1h")
        close = [10.0 - (0.02 * idx) for idx in range(40)] + [9.2 + (0.08 * idx) for idx in range(56)]
        df = pd.DataFrame(
            {
                "open": close,
                "high": [value + 0.2 for value in close],
                "low": [value - 0.2 for value in close],
                "close": close,
                "volume": [100] * len(close),
            },
            index=index,
        )

        result = Backtester(initial_capital=50_000).run(strat_cls(), df)

        assert result.n_trades >= 1
        assert result.initial_capital == 50_000.0
    finally:
        Path(paths["strategy_path"]).unlink(missing_ok=True)
        Path(paths["spec_path"]).unlink(missing_ok=True)


def test_template_registry_exposes_expected_templates():
    names = available_template_names()

    assert "trend_pullback" in names
    assert "breakout_confirm" in names
    assert "reversion" in names
    assert "sqx_us30_wpr_stoch" in names
    assert "sqx_xau_osma_bb" in names
    assert "sqx_xau_ao_hour_breakout" in names
    assert "sqx_xau_short_keltner_breakout" in names
    assert "xau_breakout_session" in names
    assert "xau_discovery_grammar" in names
    assert "sqx_usdjpy_vwap_wt" in names
    assert "sqx_hk50_batch_h1" in names
    assert "sqx_hk50_after_retest_h4" in names
    assert "sqx_hk50_before_retest_h4" in names
    assert "sqx_uk100_ulcer_keltner_h1" in names


def test_template_registry_filters_by_symbol():
    usdjpy_templates = available_template_names("USDJPY")
    hk50_templates = available_template_names("HK50.cash")

    assert "sqx_usdjpy_vwap_wt" in usdjpy_templates
    assert "sqx_usdjpy_vwap_wt" not in hk50_templates
    assert "sqx_hk50_batch_h1" in hk50_templates
    assert "xau_breakout_session" in available_template_names("XAUUSD")
    assert "xau_discovery_grammar" in available_template_names("XAUUSD")


def test_template_supports_market_blocks_incompatible_scan_candidates():
    assert template_supports_market("xau_discovery_grammar", "XAUUSD", "H1") is True
    assert template_supports_market("xau_discovery_grammar", "AUDUSD", "H1") is False
    assert template_supports_market("sqx_hk50_after_retest_h4", "AUDUSD", "H1") is False
    assert template_supports_market("sqx_hk50_after_retest_h4", "HK50.cash", "H4") is True


def test_builder_symbol_universe_exposes_target_markets():
    symbols = available_builder_symbols()
    assert "USDJPY" in symbols
    assert "US500.cash" in symbols
    assert "US100.cash" in symbols
    assert "GER40.cash" in symbols


def test_template_profile_exposes_market_specific_metadata():
    profile = template_profile("sqx_usdjpy_vwap_wt")
    assert profile is not None
    assert profile["family"] == "fx_breakout_continuation"
    assert "USDJPY" in profile["supported_symbols"]
    assert "H4" in profile["preferred_timeframes"]


def test_preset_library_contains_template_payloads():
    presets = available_presets()

    assert len(presets) >= 3
    assert all("template" in preset for preset in presets)
    assert any(preset["template"] == "trend_pullback" for preset in presets)
    assert any(preset["template"] == "xau_breakout_session" for preset in presets)
    assert any(preset["template"] == "xau_discovery_grammar" for preset in presets)
    assert any(preset["template"] == "sqx_xau_ao_hour_breakout" for preset in presets)
    assert any(preset["template"] == "sqx_xau_short_keltner_breakout" for preset in presets)

    usdjpy_presets = available_presets(symbol="USDJPY")
    assert usdjpy_presets
    assert all(preset["payload"]["symbol"] == "USDJPY" for preset in usdjpy_presets)


def test_strategy_template_rejects_unsupported_symbol():
    try:
        strategy_spec_from_template(
            "sqx_hk50_batch_h1",
            {
                "name": "Wrong Market",
                "symbol": "EURUSD",
                "timeframe": "H1",
                "params": {},
            },
        )
    except ValueError as exc:
        assert "not configured for symbol" in str(exc)
    else:
        raise AssertionError("Expected unsupported symbol validation to fail")


def test_strategy_template_rejects_unsupported_timeframe():
    try:
        strategy_spec_from_template(
            "sqx_hk50_after_retest_h4",
            {
                "name": "Wrong Timeframe",
                "symbol": "HK50.cash",
                "timeframe": "H1",
                "params": {},
            },
        )
    except ValueError as exc:
        assert "not configured for timeframe" in str(exc)
    else:
        raise AssertionError("Expected unsupported timeframe validation to fail")


def test_symbol_aliases_are_canonicalized():
    assert canonical_symbol("US500") == "US500.cash"
    assert canonical_symbol("GER40") == "GER40.cash"
    assert canonical_symbol("US100") == "US100.cash"
    assert canonical_symbol("NAS100") == "US100.cash"
    assert canonical_symbol("NASDAQ") == "US100.cash"
    assert canonical_symbol("USDJPY") == "USDJPY"


def test_nasdaq_presets_are_exposed_via_us100_aliases():
    us100_presets = available_presets(symbol="US100.cash")
    nas100_presets = available_presets(symbol="NAS100")

    assert any(preset["id"] == "sqx_us100_wpr_stoch" for preset in us100_presets)
    assert any(preset["id"] == "sqx_us100_wpr_stoch" for preset in nas100_presets)


def test_nasdaq_template_alias_builds_against_us100_symbol():
    spec = strategy_spec_from_template(
        "sqx_us100_nasdaq_qqe",
        {
            "name": "NASDAQ Alias Template Test",
            "symbol": "NAS100",
            "timeframe": "H1",
            "params": {"mmLots": 1.0},
        },
    )

    assert spec.symbol == "US100.cash"


def test_breakout_template_builds_and_trades():
    spec = strategy_spec_from_template(
        "breakout_confirm",
        {
            "name": "Template Breakout Test",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "params": {
                "HighestPeriod": 10,
                "LowestPeriod": 10,
                "ATRPeriod": 3,
                "mmLots": 1.0,
                "StopLossATR": 1.0,
                "ProfitTargetATR": 1.5,
                "MaxDistancePct": 100.0,
                "BBWRPeriod": 5,
                "BBWRMin": -1.0,
            },
            "direction": "long",
            "expiry_bars": 2,
            "min_bars": 10,
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_template_breakout")
    paths = persist_strategy_spec(compiled)

    try:
        assert any(ind.kind == "sq_highest" for ind in spec.indicators)
        assert any(entry.order_type == "buy_stop" for entry in spec.entries)
        assert 'df["highest_level"]' in compiled.source

        strat_cls = _load_generated_strategy(compiled)

        index = pd.date_range("2024-01-01", periods=120, freq="1h")
        close = [100.0 + (0.01 * idx) for idx in range(80)] + [101.0 + (0.35 * idx) for idx in range(40)]
        df = pd.DataFrame(
            {
                "open": close,
                "high": [value + 0.25 for value in close],
                "low": [value - 0.25 for value in close],
                "close": close,
                "volume": [100] * len(close),
            },
            index=index,
        )

        result = Backtester(initial_capital=25_000).run(strat_cls(), df)

        assert result.n_trades >= 1
        assert result.initial_capital == 25_000.0
    finally:
        Path(paths["strategy_path"]).unlink(missing_ok=True)
        Path(paths["spec_path"]).unlink(missing_ok=True)


def test_sqx_xau_highest_breakout_uses_broker_bar_time_offset():
    spec = strategy_spec_from_template(
        "sqx_xau_highest_breakout",
        {
            "name": "SQX XAU Offset Test",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "params": {"mmLots": 1.0},
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sqx_xau_offset")

    assert spec.bar_time_offset_hours == 6.0
    assert "bar_time_offset_hours = 6.0" in compiled.source


def test_hk50_batch_template_compiles_to_native_strategy():
    spec = strategy_spec_from_template(
        "sqx_hk50_batch_h1",
        {
            "name": "HK50 Batch Template Test",
            "symbol": "HK50.cash",
            "timeframe": "H1",
            "params": {
                "mmLots": 1.0,
                "StopLossCoef1": 2.5,
                "ProfitTargetCoef1": 2.8,
                "TrailingActCef1": 1.4,
                "TrailingStop1": 127.5,
                "StopLossCoef2": 3.0,
                "ProfitTargetCoef2": 2.2,
                "TrailingStopCoef1": 1.0,
                "LWMAPeriod1": 14,
                "IndicatorCrsMAPrd1": 47,
                "ATR1_period": 19,
                "ATR2_period": 45,
                "ATR3_period": 14,
                "ATR4_period": 100,
                "Highest_period": 50,
                "Lowest_period": 50,
                "SignalTimeRangeFrom": "00:13",
                "SignalTimeRangeTo": "00:26"
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_hk50_batch")
    assert "wma" in compiled.source
    assert "sq_highest" in compiled.source
    assert "hk50_batch_long" in compiled.source


def test_us100_templates_use_single_closed_bar_shift_for_signals():
    payload = {
        "name": "US100 Template Shift Test",
        "symbol": "US100.cash",
        "timeframe": "H1",
        "params": {"mmLots": 1.0},
    }

    qqe = strategy_spec_from_template("sqx_us100_nasdaq_qqe", payload)
    qqe_series = {item.name: item.expression for item in qqe.series}
    assert qqe_series["long_signal"] == 'df["qqe_main_1"] > df["qqe_sig_1"]'
    assert qqe_series["short_signal"] == 'df["qqe_main_1"] < df["qqe_sig_1"]'
    assert qqe_series["long_exit_signal"] == 'df["close"] <= df["session_floor"]'
    assert qqe_series["short_exit_signal"] == 'df["qqe_main_2"] > df["qqe_sig_2"]'

    smma = strategy_spec_from_template("sqx_us100_nasdaq_smma_keltner", payload)
    smma_series = {item.name: item.expression for item in smma.series}
    assert smma_series["long_signal"] == 'df["smma_low"] > df["ema_close"]'
    assert smma_series["short_signal"] == 'df["smma_high"] < df["ema_close"]'

    ichi = strategy_spec_from_template("sqx_us100_nasdaq_ichi_keltner", payload)
    ichi_series = {item.name: item.expression for item in ichi.series}
    assert ichi_series["long_signal"] == '(df["low"] <= df["smma_close"]) & (df["close"] > df["ichi_kijun"])'
    assert ichi_series["short_signal"] == '(df["high"] >= df["smma_close"]) & (df["close"] < df["ichi_kijun"])'
    assert ichi_series["long_exit_signal"] == 'df["ichi_kijun"] < df["kc_mid"]'
    assert ichi_series["short_exit_signal"] == 'df["close"] > df["smma_close"]'


def test_xau_discovery_template_builds_with_structural_blocks():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "pullback_trend",
            "volatility_filter": "atr_expansion",
            "session_filter": "london_ny",
            "stop_model": "swing",
            "target_model": "trend_runner",
            "exit_model": "trailing_atr",
            "params": {
                "HighestPeriod": 12,
                "LowestPeriod": 12,
                "ATRPeriod": 5,
                "FastEMA": 5,
                "SlowEMA": 13,
                "BBWRPeriod": 10,
                "BBWRMin": 0.0,
                "EntryBufferATR": 0.1,
                "StopLossATR": 1.0,
                "ProfitTargetATR": 2.0,
                "TrailATR": 0.8,
                "ExitAfterBars": 10,
                "PullbackLookback": 3,
                "MaxDistancePct": 100.0,
                "mmLots": 1.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery")
    assert "xau_discovery_long" in compiled.source
    assert "trail_dist" in compiled.source


def test_xau_discovery_market_entries_use_closed_bar_signals():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery Closed Bar",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "ema_reclaim",
            "volatility_filter": "bb_width",
            "session_filter": "london_ny",
            "stop_model": "atr",
            "target_model": "fixed_rr",
            "exit_model": "session_close",
            "params": {
                "BBWRMin": 0.01,
                "MaxDistancePct": 100.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_closed_bar")
    assert 'df["long_signal"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'df["short_signal"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'df["volatility_ok"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'float(df["close"].shift(1).iloc[i])' in compiled.source


def test_xau_discovery_pending_entries_use_closed_bar_signals():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery Pending Closed Bar",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "breakout_stop",
            "volatility_filter": "bb_width",
            "session_filter": "london_ny",
            "stop_model": "channel",
            "target_model": "fixed_rr",
            "exit_model": "session_close",
            "params": {
                "BBWRMin": 0.01,
                "MaxDistancePct": 100.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_pending_closed_bar")
    assert 'df["long_signal"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'df["short_signal"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'df["volatility_ok"].shift(1).eq(True).iloc[i]' in compiled.source
    assert 'float(df["close"].shift(1).iloc[i])' in compiled.source


def test_xau_discovery_atr_time_stop_uses_open_position_entry_price():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery ATR Time Stop",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "ema_reclaim",
            "volatility_filter": "atr_expansion",
            "session_filter": "london_ny",
            "stop_model": "atr",
            "target_model": "fixed_rr",
            "exit_model": "atr_time_stop",
            "params": {
                "TimeStopATR": 0.3,
                "MaxDistancePct": 100.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_atr_time_stop")
    assert "ctx.long_entry_price - ctx.open" in compiled.source
    assert "ctx.open - ctx.short_entry_price" in compiled.source


def test_sqx_xau_highest_breakout_template_builds():
    spec = strategy_spec_from_template(
        "sqx_xau_highest_breakout",
        {
            "name": "SQX XAU Highest Breakout",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "long_signal_mode": "ha_reclaim",
            "short_signal_mode": "lwma_hour_quantile",
            "params": {
                "HighestPeriod": 210,
                "LowestPeriod": 210,
                "LongTrailATR": 1.0,
                "ShortTrailATR": 0.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sqx_xau_highest_breakout")
    assert "sqx_xau_highest_breakout_long" in compiled.source
    assert 'df.index.to_series().dt.hour.astype(float)' in compiled.source
    assert 'float(self.p("LongTrailATR")) * float(df["atr_long_trail"].iloc[i - 1])' in compiled.source


def test_sqx_xau_ao_hour_breakout_template_builds():
    spec = strategy_spec_from_template(
        "sqx_xau_ao_hour_breakout",
        {
            "name": "SQX XAU AO Hour Breakout",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "params": {
                "mmLots": 1.0,
                "TickSize": 0.01,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sqx_xau_ao_hour_breakout")
    assert "sq_awesome_oscillator" in compiled.source
    assert "_sq_lower_percentile" in compiled.source
    assert "sqx_xau_ao_hour_breakout_long" in compiled.source
    assert 'float(self.p("TrailingStop1")) * float(self.p("TickSize"))' in compiled.source
    assert 'int(ctx.time.dayofweek) == 4' in compiled.source
    assert "bar_time_offset_hours = 6.0" in compiled.source


def test_xau_breakout_session_supports_long_only_direction_mode():
    spec = strategy_spec_from_template(
        "xau_breakout_session",
        {
            "name": "XAU Breakout Long Only",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "direction_mode": "long_only",
            "params": {"mmLots": 1.0},
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_breakout_long_only")
    assert len(spec.entries) == 1
    assert spec.entries[0].side == "long"
    assert "xau_breakout_long" in compiled.source
    assert "xau_breakout_short" not in compiled.source


def test_xau_discovery_supports_short_only_direction_mode():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery Short Only",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "direction_mode": "short_only",
            "entry_archetype": "breakout_stop",
            "volatility_filter": "bb_width",
            "session_filter": "london_ny",
            "stop_model": "atr",
            "target_model": "fixed_rr",
            "exit_model": "session_close",
            "params": {"mmLots": 1.0},
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_short_only")
    assert len(spec.entries) == 1
    assert spec.entries[0].side == "short"
    assert "xau_discovery_short" in compiled.source
    assert "xau_discovery_long" not in compiled.source


def test_sqx_xau_ao_hour_breakout_supports_long_only_direction_mode():
    spec = strategy_spec_from_template(
        "sqx_xau_ao_hour_breakout",
        {
            "name": "SQX XAU AO Hour Long Only",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "direction_mode": "long_only",
            "params": {"mmLots": 1.0},
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sqx_xau_ao_hour_long_only")
    assert len(spec.entries) == 1
    assert spec.entries[0].side == "long"
    assert "sqx_xau_ao_hour_breakout_long" in compiled.source
    assert "sqx_xau_ao_hour_breakout_short" not in compiled.source


def test_sqx_xau_short_keltner_breakout_supports_short_only_direction_mode():
    spec = strategy_spec_from_template(
        "sqx_xau_short_keltner_breakout",
        {
            "name": "SQX XAU Short Keltner Short Only",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "direction_mode": "short_only",
            "short_keltner_band": "middle",
            "params": {"mmLots": 1.0},
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_sqx_xau_short_keltner_short_only")
    assert len(spec.entries) == 1
    assert spec.entries[0].side == "short"
    assert "sqx_xau_short_keltner_breakout_short" in compiled.source
    assert "sqx_xau_short_keltner_breakout_long" not in compiled.source
    assert 'df["kc_middle"]' in compiled.source
    assert "ShortExpiryBars" in compiled.source


def test_compiled_time_window_is_end_inclusive():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery Session Inclusive",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "ema_reclaim",
            "volatility_filter": "bb_width",
            "session_filter": "london_ny",
            "stop_model": "atr",
            "target_model": "fixed_rr",
            "exit_model": "session_close",
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_session_inclusive")
    assert "return start_hhmm <= current <= end_hhmm" in compiled.source


def test_xau_discovery_template_supports_extended_pullback_and_exit_blocks():
    spec = strategy_spec_from_template(
        "xau_discovery_grammar",
        {
            "name": "XAU Discovery Extended",
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "entry_archetype": "atr_pullback_limit",
            "volatility_filter": "bb_width",
            "session_filter": "london_ny",
            "stop_model": "atr",
            "target_model": "fixed_rr",
            "exit_model": "break_even_then_trail",
            "params": {
                "HighestPeriod": 24,
                "LowestPeriod": 24,
                "ATRPeriod": 14,
                "FastEMA": 21,
                "SlowEMA": 55,
                "BBWRPeriod": 24,
                "BBWRMin": 0.01,
                "EntryBufferATR": 0.15,
                "StopLossATR": 1.4,
                "ProfitTargetATR": 2.8,
                "TrailATR": 1.1,
                "ExitAfterBars": 18,
                "PullbackLookback": 5,
                "PullbackATR": 0.6,
                "BreakEvenATR": 0.8,
                "TimeStopATR": 0.4,
                "MaxDistancePct": 100.0,
                "mmLots": 1.0,
            },
        },
    )

    compiled = compile_strategy_spec(spec, strategy_id="pytest_xau_discovery_extended")
    assert "buy_limit" in compiled.source
    assert "BreakEvenATR" in compiled.source
    assert 'float(df["ema_fast"].shift(1).iloc[i])' in compiled.source
