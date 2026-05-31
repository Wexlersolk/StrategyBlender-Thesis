from pathlib import Path
import pytest

from services.mt5_export_service import export_native_strategy_to_mt5
from services.native_strategy_lab import CATALOG_PATH, get_native_strategy_record, register_generated_strategy
from services.native_lab.catalog import upsert_native_strategy_record


def _out_dir(symbol: str, timeframe: str, strategy_id: str) -> Path:
    symbol_dir = symbol.replace(".cash", "").replace(".", "_")
    return Path("mt5/generated") / symbol_dir / timeframe / strategy_id


def test_export_native_strategy_to_mt5_generates_payload_driven_ea():
    strategy_id = "pytest_mt5_export"
    payload = {
        "name": "Payload Export",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "entry_archetype": "ema_reclaim",
        "volatility_filter": "atr_expansion",
        "session_filter": "london_ny",
        "stop_model": "atr",
        "target_model": "fixed_rr",
        "exit_model": "atr_time_stop",
        "params": {
            "ATRPeriod": 21,
            "FastEMA": 13,
            "SlowEMA": 55,
            "StopLossATR": 1.1,
            "ProfitTargetATR": 3.6,
            "TimeStopATR": 0.3,
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("XAUUSD", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="xau_discovery_grammar",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        ea_path = Path(exported["ea_path"])
        source = ea_path.read_text(encoding="utf-8")
        assert ea_path.exists()
        assert 'InpEntryArchetype = "ema_reclaim"' in source
        assert 'InpVolatilityFilter = "atr_expansion"' in source
        assert 'InpExitModel = "atr_time_stop"' in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_xau_pending_entries_convert_marketable_orders():
    strategy_id = "pytest_mt5_export_xau_pending"
    payload = {
        "name": "XAU Pending Export",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "entry_archetype": "breakout_stop",
        "volatility_filter": "session_impulse",
        "session_filter": "london_ny",
        "stop_model": "atr_anchor",
        "target_model": "asymmetric_runner",
        "exit_model": "ema_flip",
        "params": {
            "EntryBufferATR": 0.08,
            "StopLossATR": 1.4,
            "ProfitTargetATR": 2.8,
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("XAUUSD", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="xau_discovery_grammar",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        source = Path(exported["ea_path"]).read_text(encoding="utf-8")
        assert "bool PlaceLongEntry(" in source
        assert "if(entry_price <= ask)" in source
        assert "return trade.Buy(InpLots, _Symbol, ask, sl, tp" in source
        assert "if(entry_price >= bid)" in source
        assert "return trade.Sell(InpLots, _Symbol, bid, sl, tp" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_native_strategy_to_mt5_rejects_bad_xau_region():
    strategy_id = "pytest_mt5_export_xau_rejected"
    payload = {
        "name": "Rejected XAU Export",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "entry_archetype": "atr_pullback_limit",
        "volatility_filter": "none",
        "session_filter": "london_only",
        "stop_model": "swing",
        "target_model": "fixed_rr",
        "exit_model": "friday_flat",
        "params": {
            "EntryBufferATR": 0.15,
            "StopLossATR": 1.4,
            "ProfitTargetATR": 2.8,
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("XAUUSD", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="xau_discovery_grammar",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        with pytest.raises(ValueError, match="Rejected XAU export region"):
            export_native_strategy_to_mt5(strategy_id)
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_native_strategy_to_mt5_rejects_incompatible_market_template():
    strategy_id = "pytest_mt5_export_incompatible_market"
    payload = {
        "name": "Invalid AUDUSD XAU Export",
        "symbol": "AUDUSD",
        "timeframe": "H1",
        "entry_archetype": "pullback_trend",
        "volatility_filter": "bb_width",
        "session_filter": "london_ny",
        "stop_model": "atr",
        "target_model": "fixed_rr",
        "exit_model": "ema_flip",
        "params": {
            "ATRPeriod": 14,
            "FastEMA": 21,
            "SlowEMA": 55,
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("AUDUSD", "H1", strategy_id)
    try:
        upsert_native_strategy_record(
            {
                "strategy_id": strategy_id,
                "template_name": "xau_discovery_grammar",
                "template_payload": payload,
                "strategy_path": str(out_dir / f"{strategy_id}.py"),
                "spec_path": str(out_dir / f"{strategy_id}.json"),
                "origin": "pytest",
                "status": "draft",
            }
        )
        with pytest.raises(ValueError, match="not supported for AUDUSD H1"):
            export_native_strategy_to_mt5(strategy_id)
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_sqx_xau_highest_breakout_to_mt5():
    strategy_id = "pytest_mt5_export_sqx_xau"
    payload = {
        "name": "SQX Highest Export",
        "symbol": "XAUUSD",
        "timeframe": "H1",
        "long_signal_mode": "sma_bias",
        "short_signal_mode": "lwma_lowest_count",
        "params": {
            "HighestPeriod": 245,
            "LowestPeriod": 245,
            "LongStopATR": 2.0,
            "LongTargetATR": 3.5,
            "ShortStopATR": 1.5,
            "ShortTargetATR": 4.8,
            "LongExpiryBars": 10,
            "ShortExpiryBars": 18,
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("XAUUSD", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="sqx_xau_highest_breakout",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        ea_path = Path(exported["ea_path"])
        source = ea_path.read_text(encoding="utf-8")
        assert ea_path.exists()
        assert 'InpLongSignalMode = "sma_bias"' in source
        assert 'InpShortSignalMode = "lwma_lowest_count"' in source
        assert "trade.BuyStop" in source
        assert "trade.SellStop" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_sqx_hk50_batch_h1_to_mt5():
    strategy_id = "pytest_mt5_export_hk50"
    payload = {
        "name": "HK50 Batch Export",
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
            "IndicatorCrsMAPrd1": 34,
            "ATR1_period": 19,
            "ATR2_period": 45,
            "ATR3_period": 14,
            "ATR4_period": 100,
            "Highest_period": 50,
            "Lowest_period": 34,
            "SignalTimeRangeFrom": "00:13",
            "SignalTimeRangeTo": "00:26",
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("HK50.cash", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="sqx_hk50_batch_h1",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        ea_path = Path(exported["ea_path"])
        source = ea_path.read_text(encoding="utf-8")
        assert ea_path.exists()
        assert "IndicatorCrsMAPrd1 = 34" in source
        assert "trade.BuyStop" in source
        assert "trade.SellStop" in source
        assert "ManageTrailingStops" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_sqx_us30_wpr_stoch_to_mt5():
    strategy_id = "pytest_mt5_export_us30"
    payload = {
        "name": "US30 Export",
        "symbol": "US30.cash",
        "timeframe": "H1",
        "params": {
            "WPRPeriod": 50,
            "StochK": 14,
            "StochD": 3,
            "StochSlow": 3,
            "HighestPeriod": 105,
            "LowestPeriod": 105,
            "ATRPeriod1": 14,
            "ATRPeriod2": 29,
            "mmLots": 1.0,
            "StopLossCoef1": 2.0,
            "ProfitTargetCoef1": 2.5,
            "StopLossCoef2": 2.0,
            "ProfitTargetCoef2": 2.5,
            "TrailingStopCoef1": 1.0,
            "MaxDistancePct": 6.0,
            "SignalTimeRangeFrom": "00:00",
            "SignalTimeRangeTo": "23:59",
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("US30.cash", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="sqx_us30_wpr_stoch",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        ea_path = Path(exported["ea_path"])
        source = ea_path.read_text(encoding="utf-8")
        assert ea_path.exists()
        assert "input int WPRPeriod = 50" in source
        assert "iWPR" in source
        assert "trade.BuyStop" in source
        assert "trade.SellStop" in source
        assert "ManageTrailingStops" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_sqx_uk100_ulcer_keltner_h1_to_mt5():
    strategy_id = "pytest_mt5_export_uk100"
    payload = {
        "name": "UK100 Export",
        "symbol": "UK100.cash",
        "timeframe": "H1",
        "params": {
            "UlcerPeriod": 48,
            "KCPeriod": 14,
            "KCMult1": 2.75,
            "KCMult2": 2.5,
            "ATR1_period": 50,
            "ATR2_period": 19,
            "ATR3_period": 100,
            "ATR4_period": 14,
            "mmLots": 1.0,
            "SignalTimeRangeFrom": "00:13",
            "SignalTimeRangeTo": "00:26",
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("UK100.cash", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="sqx_uk100_ulcer_keltner_h1",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        ea_path = Path(exported["ea_path"])
        source = ea_path.read_text(encoding="utf-8")
        assert ea_path.exists()
        assert "input int UlcerPeriod = 48" in source
        assert "UlcerIndexValue" in source
        assert "HAOpen" in source
        assert "trade.BuyStop" in source
        assert "trade.Sell(" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")


def test_export_us100_qqe_preserves_signal_window():
    strategy_id = "pytest_mt5_export_us100_qqe_window"
    payload = {
        "name": "US100 QQE Window Export",
        "symbol": "US100.cash",
        "timeframe": "H1",
        "params": {
            "QQERsiPeriod1": 10,
            "QQESmooth1": 5,
            "QQERsiPeriod2": 42,
            "QQESmooth2": 5,
            "SMAEntryPeriod1": 34,
            "PriceEntryMult1": 1.2,
            "PriceEntryMult2": 0.9,
            "ExitAfterBars1": 24,
            "ExitAfterBars2": 19,
            "ProfitTargetCoef1": 4.2,
            "StopLossCoef1": 1.9,
            "ProfitTargetCoef2": 3.7,
            "StopLossCoef2": 1.7,
            "SignalTimeRangeFrom": "00:00",
            "SignalTimeRangeTo": "22:30",
            "mmLots": 1.0,
        },
    }
    original_catalog = CATALOG_PATH.read_text(encoding="utf-8") if CATALOG_PATH.exists() else None
    out_dir = _out_dir("US100.cash", "H1", strategy_id)
    try:
        register_generated_strategy(
            template_name="sqx_us100_nasdaq_qqe",
            payload=payload,
            strategy_id=strategy_id,
            origin="pytest",
        )
        exported = export_native_strategy_to_mt5(strategy_id)
        source = Path(exported["ea_path"]).read_text(encoding="utf-8")
        assert "input int SignalFromHour = 0" in source
        assert "input int SignalToHour = 22" in source
        assert "input int SignalToMinute = 30" in source
    finally:
        record = get_native_strategy_record(strategy_id)
        if record:
            Path(record["strategy_path"]).unlink(missing_ok=True)
            Path(record["spec_path"]).unlink(missing_ok=True)
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                else:
                    path.rmdir()
            out_dir.rmdir()
        if original_catalog is None:
            CATALOG_PATH.unlink(missing_ok=True)
        else:
            CATALOG_PATH.write_text(original_catalog, encoding="utf-8")
