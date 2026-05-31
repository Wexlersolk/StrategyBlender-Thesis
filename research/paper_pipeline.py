from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import settings
from engine.backtester import Backtester
from engine.data_loader import load_bars
from engine.policy import ModelOverlayPolicy, NullOverlayPolicy, OverlayPolicy
from engine.results import BacktestResults
from research.meta_models import fit_filter_model, fit_sizing_model
from research.monte_carlo import run_monte_carlo
from research.overlay_evaluation import (
    OverlayEvaluationReport,
    OverlayEvaluationWindow,
    _aggregate_split_metrics,
    _calibration_frame,
    _result_equity_curve,
    _result_trade_log,
    _split_metric_row,
    _validation_diagnostics,
    _window_detail_row,
    build_benchmark_policy,
    evaluate_portfolio_overlay_walk_forward,
)
from research.paper_stats import compare_overlays_to_baseline
from research.purged_walk_forward import generate_purged_splits
from research.trade_dataset import build_trade_dataset
from services.backtest_service import default_intrabar_steps, discover_strategies, resolve_execution_config
from services.python_strategy_service import compile_strategy_spec, strategy_spec_from_template


ROOT = Path(__file__).resolve().parent.parent
PAPER_EXPORT_ROOT = ROOT / "data" / "exports" / "paper_reports"


@dataclass(frozen=True)
class PaperAssetConfig:
    asset_id: str
    strategy_ref: str
    symbol: str
    timeframe: str = "H1"
    date_from: str = "2020-01-01"
    date_to: str = "2025-12-31"
    train_bars: int = 240
    test_bars: int = 120
    embargo_bars: int = 5
    intrabar_steps: int = 1
    execution_config: dict | None = None


@dataclass(frozen=True)
class PaperModelConfig:
    benchmark_name: str = "composite"
    benchmark_settings: dict[str, float] = field(
        default_factory=lambda: {
            "target_vol": 0.20,
            "min_multiplier": 0.50,
            "max_multiplier": 1.50,
            "soft_dd": 5.0,
            "hard_dd": 10.0,
            "soft_multiplier": 0.50,
        }
    )
    filter_threshold: float = 0.55
    positive_return_cutoff: float = 0.0
    filter_label_mode: str = "hybrid"
    filter_top_quantile: float = 0.65
    filter_cost_buffer_fraction: float = 0.25
    train_ml_on_benchmark: bool = True
    filter_only: bool = True
    sizing_min_multiplier: float = 0.50
    sizing_max_multiplier: float = 1.50


@dataclass
class PaperExperimentReport:
    reports_by_asset: dict[str, OverlayEvaluationReport]
    portfolio_report: OverlayEvaluationReport
    comparison_summary: pd.DataFrame
    comparison_deltas: pd.DataFrame
    monte_carlo_summary: pd.DataFrame
    output_dir: str = ""


def _infer_template(payload: dict) -> str:
    symbol = str(payload.get("symbol", "")).strip().upper()
    timeframe = str(payload.get("timeframe", "")).strip().upper()
    params = dict(payload.get("params", {}) or {})
    param_keys = {str(key) for key in params.keys()}
    payload_keys = {str(key) for key in payload.keys()}

    def has_any(*names: str) -> bool:
        return any(name in payload_keys or name in param_keys for name in names)

    if symbol == "HK50.CASH" and timeframe == "H1":
        return "sqx_hk50_batch_h1"
    if symbol == "HK50.CASH" and timeframe == "H4":
        if "trend_bias_mode" in payload:
            return "sqx_hk50_after_retest_h4"
        return "sqx_hk50_before_retest_h4"
    if symbol == "XAUUSD":
        if has_any("entry_archetype", "volatility_filter", "session_filter", "stop_model", "target_model", "exit_model"):
            return "xau_discovery_grammar"
        if has_any("Hour", "HourTrigger", "AOHour", "AOPercentile"):
            return "sqx_xau_ao_hour_breakout"
        if has_any("KeltnerAtrPeriod", "KeltnerPeriod", "KeltnerMultiplier"):
            return "sqx_xau_short_keltner_breakout"
        if has_any("HighestPeriod", "LowestPeriod") and not has_any("entry_archetype"):
            return "sqx_xau_highest_breakout"
        return "xau_breakout_session"
    if symbol == "US100.CASH":
        if has_any("QQERsiPeriod1", "QQERsiPeriod2", "QQESmooth1", "QQESmooth2"):
            return "sqx_us100_nasdaq_qqe"
        if has_any("IchimokuTenkan", "IchimokuKijun", "IchimokuSenkou", "KeltnerAtrPeriod"):
            return "sqx_us100_nasdaq_ichi_keltner"
        if has_any("SMMAPeriod", "SMMAPeriod", "KeltnerPeriod", "KeltnerAtrPeriod"):
            return "sqx_us100_nasdaq_smma_keltner"
        return "sqx_us100_nasdaq_qqe"
    if symbol == "US30.CASH":
        return "sqx_us30_wpr_stoch"
    if symbol == "UK100.CASH":
        return "sqx_uk100_ulcer_keltner_h1"
    raise ValueError(f"Unable to infer template from payload for {symbol} {timeframe}")


def _slugify(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value))
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "run"


def load_strategy_class(strategy_ref: str):
    if strategy_ref.startswith("native_payload:"):
        payload_path = Path(strategy_ref.split(":", 1)[1]).resolve()
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        template_name = _infer_template(payload)
        spec = strategy_spec_from_template(template_name, payload)
        compiled = compile_strategy_spec(spec, strategy_id=f"{payload_path.stem}_paper")
        namespace: dict[str, object] = {"__name__": f"_paper_{payload_path.stem}"}
        exec(compiled.source, namespace)
        return namespace[compiled.strategy_class]
    strategies = discover_strategies()
    if strategy_ref in strategies:
        return strategies[strategy_ref]
    if ":" in strategy_ref:
        module_name, class_name = strategy_ref.split(":", 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    raise ValueError(f"Unknown strategy reference: {strategy_ref}")


def _backtester_factory(
    strategy_class: type,
    *,
    symbol: str,
    timeframe: str,
    execution_config: dict | None,
    intrabar_steps: int,
) -> Callable[[OverlayPolicy], Backtester]:
    resolved = resolve_execution_config(symbol, execution_config)
    strategy_intrabar_steps = default_intrabar_steps(symbol, timeframe, intrabar_steps)

    def _factory(policy: OverlayPolicy) -> Backtester:
        return Backtester(
            initial_capital=100_000.0,
            lot_value=getattr(strategy_class, "lot_value", 1.0),
            intrabar_steps=int(strategy_intrabar_steps),
            overlay_policy=policy,
            commission_per_lot=float(resolved["commission_per_lot"]),
            spread_pips=float(resolved["spread_pips"]),
            slippage_pips=float(resolved["slippage_pips"]),
            tick_size=float(resolved.get("tick_size", settings.DEFAULT_TICK_SIZE)),
            tick_value=float(resolved.get("tick_value", settings.DEFAULT_TICK_VALUE)),
            contract_size=float(resolved.get("contract_size", settings.DEFAULT_CONTRACT_SIZE)),
            swap_per_lot_long=float(resolved.get("swap_per_lot_long", settings.DEFAULT_SWAP_PER_LOT_LONG)),
            swap_per_lot_short=float(resolved.get("swap_per_lot_short", settings.DEFAULT_SWAP_PER_LOT_SHORT)),
            swap_weekday_multipliers=dict(resolved.get("swap_weekday_multipliers", settings.DEFAULT_SWAP_WEEKDAY_MULTIPLIERS)),
            session_timezone_offset_hours=float(resolved.get("session_timezone_offset_hours", settings.DEFAULT_SESSION_TIMEZONE_OFFSET_HOURS)),
            use_bar_spread=bool(resolved.get("use_bar_spread", False)),
            bar_spread_multiplier=float(resolved.get("bar_spread_multiplier", settings.DEFAULT_BAR_SPREAD_MULTIPLIER)),
            tradable_session_windows=dict(resolved.get("tradable_session_windows", {})),
            force_flat_weekday=int(resolved.get("force_flat_weekday", settings.DEFAULT_FORCE_FLAT_WEEKDAY)),
            force_flat_hhmm=str(resolved.get("force_flat_hhmm", settings.DEFAULT_FORCE_FLAT_HHMM)),
        )

    return _factory


def _ml_policy_factories(
    model_config: PaperModelConfig,
    *,
    backtester_factory: Callable[[OverlayPolicy], Backtester],
    strategy_class: type,
) -> list[tuple[str, Callable[[pd.DataFrame, BacktestResults], OverlayPolicy]]]:
    def _benchmark_factory(_train_df: pd.DataFrame, _train_result: BacktestResults) -> OverlayPolicy:
        return build_benchmark_policy(model_config.benchmark_name, dict(model_config.benchmark_settings))

    benchmark_cache: dict[tuple[object, object, int], tuple[BacktestResults, pd.DataFrame]] = {}

    def _benchmark_training_data(train_df: pd.DataFrame, train_result: BacktestResults) -> tuple[BacktestResults, pd.DataFrame]:
        key = (train_df.index[0], train_df.index[-1], len(train_df))
        cached = benchmark_cache.get(key)
        if cached is not None:
            return cached
        benchmark_policy = _benchmark_factory(train_df, train_result)
        benchmark_result = backtester_factory(benchmark_policy).run(strategy_class(), train_df.copy())
        benchmark_dataset = build_trade_dataset(benchmark_result)
        benchmark_cache[key] = (benchmark_result, benchmark_dataset)
        return benchmark_result, benchmark_dataset

    def _safe_filter_model(dataset: pd.DataFrame) -> dict:
        try:
            return fit_filter_model(
                dataset,
                threshold=float(model_config.filter_threshold),
                positive_return_cutoff=float(model_config.positive_return_cutoff),
                label_mode=str(model_config.filter_label_mode),
                top_quantile=float(model_config.filter_top_quantile),
                cost_buffer_fraction=float(model_config.filter_cost_buffer_fraction),
            )
        except Exception:
            return {}

    def _safe_sizing_model(dataset: pd.DataFrame) -> dict:
        try:
            return fit_sizing_model(
                dataset,
                min_multiplier=float(model_config.sizing_min_multiplier),
                max_multiplier=float(model_config.sizing_max_multiplier),
            )
        except Exception:
            return {}

    def _filter_only_factory(_train_df: pd.DataFrame, train_result: BacktestResults) -> OverlayPolicy:
        dataset = build_trade_dataset(train_result)
        if model_config.train_ml_on_benchmark:
            _, dataset = _benchmark_training_data(_train_df, train_result)
        filter_model = _safe_filter_model(dataset)
        return ModelOverlayPolicy(
            filter_model=filter_model,
            sizing_model={},
            base_policy=_benchmark_factory(_train_df, train_result),
        )

    def _sizing_only_factory(_train_df: pd.DataFrame, train_result: BacktestResults) -> OverlayPolicy:
        dataset = build_trade_dataset(train_result)
        if model_config.train_ml_on_benchmark:
            _, dataset = _benchmark_training_data(_train_df, train_result)
        sizing_model = _safe_sizing_model(dataset)
        return ModelOverlayPolicy(
            filter_model={},
            sizing_model=sizing_model,
            base_policy=_benchmark_factory(_train_df, train_result),
        )

    def _full_ml_factory(_train_df: pd.DataFrame, train_result: BacktestResults) -> OverlayPolicy:
        dataset = build_trade_dataset(train_result)
        if model_config.train_ml_on_benchmark:
            _, dataset = _benchmark_training_data(_train_df, train_result)
        filter_model = _safe_filter_model(dataset)
        sizing_model = _safe_sizing_model(dataset)
        return ModelOverlayPolicy(
            filter_model=filter_model,
            sizing_model=sizing_model,
            base_policy=_benchmark_factory(_train_df, train_result),
        )

    variants = [
        ("Baseline", lambda _train_df, _train_result: NullOverlayPolicy()),
        ("Benchmark", _benchmark_factory),
        ("ML Filter", _filter_only_factory),
    ]
    if not model_config.filter_only:
        variants.extend(
            [
                ("ML Sizing", _sizing_only_factory),
                ("ML Overlay", _full_ml_factory),
            ]
        )
    return variants


def evaluate_ablation_walk_forward(
    *,
    df: pd.DataFrame,
    asset_id: str,
    strategy_class: type,
    backtester_factory: Callable[[OverlayPolicy], Backtester],
    model_config: PaperModelConfig,
    train_bars: int,
    test_bars: int,
    embargo_bars: int = 0,
) -> OverlayEvaluationReport:
    splits = generate_purged_splits(
        df.index,
        train_bars=int(train_bars),
        test_bars=int(test_bars),
        embargo_bars=int(embargo_bars),
    )
    overlay_specs = _ml_policy_factories(
        model_config,
        backtester_factory=backtester_factory,
        strategy_class=strategy_class,
    )
    windows: list[OverlayEvaluationWindow] = []

    for split in splits:
        train_df = df[(df.index >= split.train_start) & (df.index <= split.train_end)].copy()
        test_df = df[(df.index >= split.test_start) & (df.index <= split.test_end)].copy()
        if train_df.empty or test_df.empty:
            continue

        train_bt = backtester_factory(NullOverlayPolicy())
        train_result = train_bt.run(strategy_class(), train_df)
        train_dataset = build_trade_dataset(train_result)

        for label, overlay_factory in overlay_specs:
            overlay = overlay_factory(train_df, train_result)
            test_bt = backtester_factory(overlay)
            test_result = test_bt.run(strategy_class(), test_df)
            windows.append(
                OverlayEvaluationWindow(
                    overlay_label=label,
                    split=split,
                    train_result=train_result,
                    test_result=test_result,
                    train_dataset=train_dataset,
                    test_dataset=build_trade_dataset(test_result),
                    asset_id=asset_id,
                )
            )

    split_metrics = pd.DataFrame([_split_metric_row(window) for window in windows])
    aggregate_metrics = _aggregate_split_metrics(split_metrics)
    window_details = pd.DataFrame([_window_detail_row(window) for window in windows])
    trade_logs = (
        pd.concat(
            [
                _result_trade_log(
                    window.test_result,
                    overlay=window.overlay_label,
                    window_id=window.split.window_id,
                    asset_id=window.asset_id,
                )
                for window in windows
            ],
            ignore_index=True,
        )
        if windows
        else pd.DataFrame()
    )
    equity_curves = (
        pd.concat(
            [
                _result_equity_curve(
                    window.test_result,
                    overlay=window.overlay_label,
                    window_id=window.split.window_id,
                    asset_id=window.asset_id,
                )
                for window in windows
            ],
            ignore_index=True,
        )
        if windows
        else pd.DataFrame()
    )
    calibration = _calibration_frame(windows)

    return OverlayEvaluationReport(
        windows=windows,
        split_metrics=split_metrics,
        aggregate_metrics=aggregate_metrics,
        metadata={
            "window_details": window_details,
            "trade_logs": trade_logs,
            "equity_curves": equity_curves,
            "calibration": calibration,
            "validation": _validation_diagnostics(
                split_metrics=split_metrics,
                splits=splits,
                windows=windows,
            ),
        },
    )


def _full_sample_overlay_runs(
    *,
    df: pd.DataFrame,
    strategy_class: type,
    backtester_factory: Callable[[OverlayPolicy], Backtester],
    model_config: PaperModelConfig,
) -> dict[str, BacktestResults]:
    baseline_result = backtester_factory(NullOverlayPolicy()).run(strategy_class(), df.copy())
    baseline_dataset = build_trade_dataset(baseline_result)
    benchmark_policy = build_benchmark_policy(model_config.benchmark_name, dict(model_config.benchmark_settings))
    benchmark_result = backtester_factory(benchmark_policy).run(strategy_class(), df.copy())
    benchmark_dataset = build_trade_dataset(benchmark_result)
    ml_training_dataset = benchmark_dataset if model_config.train_ml_on_benchmark else baseline_dataset
    try:
        filter_model = fit_filter_model(
            ml_training_dataset,
            threshold=float(model_config.filter_threshold),
            positive_return_cutoff=float(model_config.positive_return_cutoff),
            label_mode=str(model_config.filter_label_mode),
            top_quantile=float(model_config.filter_top_quantile),
            cost_buffer_fraction=float(model_config.filter_cost_buffer_fraction),
        )
    except Exception:
        filter_model = {}
    try:
        sizing_model = fit_sizing_model(
            ml_training_dataset,
            min_multiplier=float(model_config.sizing_min_multiplier),
            max_multiplier=float(model_config.sizing_max_multiplier),
        )
    except Exception:
        sizing_model = {}
    ml_policy = ModelOverlayPolicy(
        filter_model=filter_model,
        sizing_model=sizing_model,
        base_policy=benchmark_policy,
    )
    runs = {
        "Baseline": baseline_result,
        "Benchmark": benchmark_result,
        "ML Filter": backtester_factory(ModelOverlayPolicy(filter_model=filter_model, sizing_model={}, base_policy=benchmark_policy)).run(strategy_class(), df.copy()),
    }
    if not model_config.filter_only:
        runs["ML Overlay"] = backtester_factory(ml_policy).run(strategy_class(), df.copy())
    return runs


def _monte_carlo_summary(asset_id: str, runs: dict[str, BacktestResults]) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for overlay, result in runs.items():
        if result.n_trades < 8:
            continue
        mc = run_monte_carlo(result, n_simulations=1000)
        rows.append(
            {
                "asset_id": asset_id,
                "overlay": overlay,
                "n_trades": int(result.n_trades),
                "mc_prob_profit": float(mc.prob_profit),
                "mc_prob_ruin_20pct": float(mc.prob_ruin(20.0)),
                "mc_profit_p5": float(mc.profit_percentiles[5]),
                "mc_profit_p50": float(mc.profit_percentiles[50]),
                "mc_profit_p95": float(mc.profit_percentiles[95]),
                "mc_drawdown_p50": float(mc.drawdown_percentiles[50]),
                "mc_drawdown_p95": float(mc.drawdown_percentiles[95]),
            }
        )
    return pd.DataFrame(rows)


def run_paper_experiment(
    asset_configs: list[PaperAssetConfig],
    *,
    model_config: PaperModelConfig | None = None,
) -> PaperExperimentReport:
    model_config = model_config or PaperModelConfig()
    reports_by_asset: dict[str, OverlayEvaluationReport] = {}
    monte_carlo_frames: list[pd.DataFrame] = []

    for asset in asset_configs:
        strategy_class = load_strategy_class(asset.strategy_ref)
        bars = load_bars(asset.symbol, asset.timeframe, date_from=asset.date_from, date_to=asset.date_to)
        if bars.empty:
            raise ValueError(f"No bars loaded for {asset.asset_id} ({asset.symbol} {asset.timeframe}).")

        backtester_factory = _backtester_factory(
            strategy_class,
            symbol=asset.symbol,
            timeframe=asset.timeframe,
            execution_config=asset.execution_config,
            intrabar_steps=asset.intrabar_steps,
        )
        report = evaluate_ablation_walk_forward(
            df=bars,
            asset_id=asset.asset_id,
            strategy_class=strategy_class,
            backtester_factory=backtester_factory,
            model_config=model_config,
            train_bars=asset.train_bars,
            test_bars=asset.test_bars,
            embargo_bars=asset.embargo_bars,
        )
        reports_by_asset[asset.asset_id] = report
        monte_carlo_frames.append(
            _monte_carlo_summary(
                asset.asset_id,
                _full_sample_overlay_runs(
                    df=bars,
                    strategy_class=strategy_class,
                    backtester_factory=backtester_factory,
                    model_config=model_config,
                ),
            )
        )

    portfolio_report = (
        next(iter(reports_by_asset.values()))
        if len(reports_by_asset) == 1
        else evaluate_portfolio_overlay_walk_forward(reports_by_asset=reports_by_asset)
    )
    comparison_summary, comparison_deltas = compare_overlays_to_baseline(portfolio_report.split_metrics)
    monte_carlo_summary = pd.concat(monte_carlo_frames, ignore_index=True) if monte_carlo_frames else pd.DataFrame()

    return PaperExperimentReport(
        reports_by_asset=reports_by_asset,
        portfolio_report=portfolio_report,
        comparison_summary=comparison_summary,
        comparison_deltas=comparison_deltas,
        monte_carlo_summary=monte_carlo_summary,
    )


def _write_table_variants(df: pd.DataFrame, base_path: Path) -> dict[str, str]:
    outputs: dict[str, str] = {}
    csv_path = base_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    outputs["csv"] = str(csv_path)
    tex_path = base_path.with_suffix(".tex")
    tex_path.write_text(df.to_latex(index=False, float_format=lambda value: f"{value:0.4f}"), encoding="utf-8")
    outputs["tex"] = str(tex_path)
    return outputs


def _html_table(df: pd.DataFrame, *, title: str, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return f"<h2>{title}</h2><p>No data available.</p>"
    preview = df.head(int(max_rows)).copy()
    return f"<h2>{title}</h2>{preview.to_html(index=False, border=0, classes='paper-table')}"


def _window_profit_figure(split_metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if split_metrics.empty:
        return fig
    for overlay, frame in split_metrics.groupby("overlay", as_index=False):
        fig.add_trace(
            go.Scatter(
                x=frame["window_id"],
                y=frame["oos_net_profit"],
                mode="lines+markers",
                name=str(overlay),
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="Out-of-sample net profit by walk-forward window",
        xaxis_title="Window",
        yaxis_title="OOS net profit",
    )
    return fig


def _aggregate_profit_figure(aggregate_metrics: pd.DataFrame) -> go.Figure:
    if aggregate_metrics.empty:
        return go.Figure()
    fig = px.bar(
        aggregate_metrics,
        x="overlay",
        y="total_oos_net_profit",
        color="overlay",
        title="Total OOS net profit by overlay",
        template="plotly_white",
    )
    fig.update_layout(showlegend=False)
    return fig


def _delta_distribution_figure(comparison_deltas: pd.DataFrame) -> go.Figure:
    if comparison_deltas.empty:
        return go.Figure()
    fig = px.box(
        comparison_deltas,
        x="overlay",
        y="delta",
        color="overlay",
        title="Window-level improvement over baseline",
        template="plotly_white",
    )
    fig.update_layout(showlegend=False)
    return fig


def _calibration_figure(calibration: pd.DataFrame) -> go.Figure:
    if calibration is None or calibration.empty:
        return go.Figure()
    fig = go.Figure()
    if "overlay" in calibration.columns:
        grouped = calibration.groupby("overlay", as_index=False)
        for overlay, frame in grouped:
            fig.add_trace(
                go.Scatter(
                    x=frame["avg_predicted_probability"],
                    y=frame["realized_win_rate"],
                    mode="lines+markers",
                    name=str(overlay),
                )
            )
    else:
        fig.add_trace(
            go.Scatter(
                x=calibration["avg_predicted_probability"],
                y=calibration["realized_win_rate"],
                mode="lines+markers",
                name="Observed",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[0.0, 1.0],
            y=[0.0, 1.0],
            mode="lines",
            line=dict(dash="dash"),
            name="Ideal",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="ML filter calibration",
        xaxis_title="Predicted win probability",
        yaxis_title="Observed win rate",
    )
    return fig


def export_paper_experiment(
    report: PaperExperimentReport,
    *,
    output_dir: str | Path | None = None,
    title: str = "paper_experiment",
) -> Path:
    run_slug = _slugify(title)
    export_dir = Path(output_dir) if output_dir else PAPER_EXPORT_ROOT / run_slug
    export_dir.mkdir(parents=True, exist_ok=True)
    stale_paths = [
        export_dir / "aggregate_metrics.csv",
        export_dir / "aggregate_metrics.tex",
        export_dir / "split_metrics.csv",
        export_dir / "split_metrics.tex",
        export_dir / "comparison_summary.csv",
        export_dir / "comparison_summary.tex",
        export_dir / "comparison_deltas.csv",
        export_dir / "comparison_deltas.tex",
        export_dir / "monte_carlo_summary.csv",
        export_dir / "monte_carlo_summary.tex",
        export_dir / "validation.json",
        export_dir / "window_details.csv",
        export_dir / "trade_logs.csv",
        export_dir / "equity_curves.csv",
        export_dir / "calibration.csv",
        export_dir / "paper_summary.html",
        export_dir / "paper_report_manifest.json",
    ]
    figures_dir = export_dir / "figures"
    stale_paths.extend(
        [
            figures_dir / "window_profit.html",
            figures_dir / "aggregate_profit.html",
            figures_dir / "delta_distribution.html",
            figures_dir / "calibration.html",
        ]
    )
    for path in stale_paths:
        if path.exists():
            path.unlink()

    files: dict[str, str] = {}
    files.update({f"aggregate_{k}": v for k, v in _write_table_variants(report.portfolio_report.aggregate_metrics, export_dir / "aggregate_metrics").items()})
    files.update({f"split_{k}": v for k, v in _write_table_variants(report.portfolio_report.split_metrics, export_dir / "split_metrics").items()})
    files.update({f"comparison_{k}": v for k, v in _write_table_variants(report.comparison_summary, export_dir / "comparison_summary").items()})
    files.update({f"deltas_{k}": v for k, v in _write_table_variants(report.comparison_deltas, export_dir / "comparison_deltas").items()})
    if not report.monte_carlo_summary.empty:
        files.update({f"monte_carlo_{k}": v for k, v in _write_table_variants(report.monte_carlo_summary, export_dir / "monte_carlo_summary").items()})

    validation = report.portfolio_report.metadata.get("validation", {})
    validation_path = export_dir / "validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, default=str), encoding="utf-8")
    files["validation"] = str(validation_path)

    for name in ["window_details", "trade_logs", "equity_curves", "calibration"]:
        frame = report.portfolio_report.metadata.get(name)
        if isinstance(frame, pd.DataFrame) and not frame.empty:
            path = export_dir / f"{name}.csv"
            frame.to_csv(path, index=False)
            files[name] = str(path)

    figures_dir.mkdir(exist_ok=True)
    figure_specs = {
        "window_profit.html": _window_profit_figure(report.portfolio_report.split_metrics),
        "aggregate_profit.html": _aggregate_profit_figure(report.portfolio_report.aggregate_metrics),
        "delta_distribution.html": _delta_distribution_figure(report.comparison_deltas),
        "calibration.html": _calibration_figure(report.portfolio_report.metadata.get("calibration", pd.DataFrame())),
    }
    for filename, fig in figure_specs.items():
        fig.write_html(figures_dir / filename, include_plotlyjs="cdn")
        files[filename] = str(figures_dir / filename)

    summary_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #102030; background: #f7f8fb; }}
    h1, h2 {{ color: #17324d; }}
    .meta {{ margin-bottom: 24px; }}
    .paper-table {{ border-collapse: collapse; width: 100%; background: white; margin-bottom: 24px; }}
    .paper-table th, .paper-table td {{ border: 1px solid #d8dee8; padding: 8px 10px; font-size: 13px; }}
    .paper-table th {{ background: #edf2f7; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    iframe {{ width: 100%; height: 420px; border: 1px solid #d8dee8; background: white; }}
    .links a {{ display: inline-block; margin-right: 12px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">
    <p><strong>Assets:</strong> {", ".join(report.reports_by_asset.keys())}</p>
    <p><strong>Output directory:</strong> {export_dir}</p>
    <div class="links">
      <a href="aggregate_metrics.csv">Aggregate CSV</a>
      <a href="comparison_summary.csv">Comparison CSV</a>
      <a href="split_metrics.csv">Split Metrics CSV</a>
      <a href="paper_report_manifest.json">Manifest JSON</a>
    </div>
  </div>
  <div class="grid">
    <iframe src="figures/aggregate_profit.html"></iframe>
    <iframe src="figures/window_profit.html"></iframe>
    <iframe src="figures/delta_distribution.html"></iframe>
    <iframe src="figures/calibration.html"></iframe>
  </div>
  {_html_table(report.portfolio_report.aggregate_metrics, title="Aggregate Metrics")}
  {_html_table(report.comparison_summary, title="Overlay vs Baseline Significance")}
  {_html_table(report.monte_carlo_summary, title="Monte Carlo Summary")}
  {_html_table(report.portfolio_report.metadata.get("window_details", pd.DataFrame()), title="Window Details")}
</body>
</html>
"""
    summary_path = export_dir / "paper_summary.html"
    summary_path.write_text(summary_html, encoding="utf-8")
    files["summary_html"] = str(summary_path)

    metadata = {
        "title": title,
        "asset_ids": list(report.reports_by_asset.keys()),
        "output_dir": str(export_dir),
        "files": files,
    }
    metadata_path = export_dir / "paper_report_manifest.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    report.output_dir = str(export_dir)
    return export_dir
