from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from engine.results import BacktestResults


@dataclass
class HypothesisTestReport:
    sample_size: int
    mean_profit: float
    median_profit: float
    std_profit: float
    total_profit: float
    expectancy: float
    hit_rate: float
    positive_month_rate: float
    t_statistic: float
    t_pvalue_two_sided: float
    t_pvalue_positive: float
    sign_pvalue_two_sided: float
    permutation_pvalue_positive: float
    bootstrap_mean_ci_low: float
    bootstrap_mean_ci_high: float
    effect_size: float
    null_mean: float
    confidence_level: float

    @property
    def rejects_null_positive(self) -> bool:
        return bool(
            self.bootstrap_mean_ci_low > self.null_mean
            and self.t_pvalue_positive < 0.05
            and self.permutation_pvalue_positive < 0.05
        )

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "sample_size": self.sample_size,
            "mean_profit": round(self.mean_profit, 6),
            "median_profit": round(self.median_profit, 6),
            "std_profit": round(self.std_profit, 6),
            "total_profit": round(self.total_profit, 6),
            "expectancy": round(self.expectancy, 6),
            "hit_rate": round(self.hit_rate, 6),
            "positive_month_rate": round(self.positive_month_rate, 6),
            "t_statistic": round(self.t_statistic, 6),
            "t_pvalue_two_sided": round(self.t_pvalue_two_sided, 6),
            "t_pvalue_positive": round(self.t_pvalue_positive, 6),
            "sign_pvalue_two_sided": round(self.sign_pvalue_two_sided, 6),
            "permutation_pvalue_positive": round(self.permutation_pvalue_positive, 6),
            "bootstrap_mean_ci_low": round(self.bootstrap_mean_ci_low, 6),
            "bootstrap_mean_ci_high": round(self.bootstrap_mean_ci_high, 6),
            "effect_size": round(self.effect_size, 6),
            "null_mean": round(self.null_mean, 6),
            "confidence_level": round(self.confidence_level, 6),
            "rejects_null_positive": self.rejects_null_positive,
        }


def _safe_float(value: float | np.floating | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _trade_profit_series(results: BacktestResults) -> pd.Series:
    profits = pd.Series(results.profits, dtype=float)
    return profits.replace([np.inf, -np.inf], np.nan).dropna()


def _trade_frame(results: BacktestResults) -> pd.DataFrame:
    if not results.trades:
        return pd.DataFrame(columns=["closed_time", "profit", "direction"])
    return pd.DataFrame(
        {
            "closed_time": [trade.closed_time for trade in results.trades],
            "profit": [trade.net_profit for trade in results.trades],
            "direction": [trade.direction.value for trade in results.trades],
        }
    )


def analyze_trade_hypothesis(
    results: BacktestResults,
    *,
    null_mean: float = 0.0,
    confidence_level: float = 0.95,
    bootstrap_samples: int = 4000,
    permutation_samples: int = 4000,
    seed: int = 42,
) -> HypothesisTestReport:
    profits = _trade_profit_series(results)
    if len(profits) < 8:
        raise ValueError("Hypothesis testing needs at least 8 closed trades.")

    sample = profits.to_numpy(dtype=float)
    mean_profit = float(sample.mean())
    centered = sample - float(null_mean)
    std_profit = float(sample.std(ddof=1)) if len(sample) > 1 else 0.0
    effect_size = 0.0 if std_profit < 1e-9 else float(centered.mean() / std_profit)

    t_out = stats.ttest_1samp(sample, popmean=float(null_mean))
    t_stat = _safe_float(t_out.statistic)
    t_pvalue_two_sided = _safe_float(t_out.pvalue)
    if np.isnan(t_stat) or np.isnan(t_pvalue_two_sided):
        t_stat = 0.0
        t_pvalue_two_sided = 1.0
    t_dist = stats.t(df=max(len(sample) - 1, 1))
    t_pvalue_positive = float(1.0 - t_dist.cdf(t_stat))

    wins = int(np.sum(sample > float(null_mean)))
    losses = int(np.sum(sample <= float(null_mean)))
    sign_pvalue = float(stats.binomtest(wins, n=wins + losses, p=0.5, alternative="two-sided").pvalue)

    rng = np.random.default_rng(seed)
    boot = rng.choice(sample, size=(int(bootstrap_samples), len(sample)), replace=True).mean(axis=1)
    alpha = 1.0 - float(confidence_level)
    ci_low, ci_high = np.percentile(boot, [100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)])

    sign_flips = rng.choice([-1.0, 1.0], size=(int(permutation_samples), len(sample)), replace=True)
    perm_means = (sign_flips * centered).mean(axis=1)
    permutation_pvalue_positive = float(np.mean(perm_means >= centered.mean()))

    monthly = results.monthly_stats()
    positive_month_rate = float((monthly["profit"] > 0).mean()) if not monthly.empty else 0.0

    return HypothesisTestReport(
        sample_size=int(len(sample)),
        mean_profit=mean_profit,
        median_profit=float(np.median(sample)),
        std_profit=std_profit,
        total_profit=float(sample.sum()),
        expectancy=mean_profit,
        hit_rate=float(np.mean(sample > 0.0)),
        positive_month_rate=positive_month_rate,
        t_statistic=t_stat,
        t_pvalue_two_sided=t_pvalue_two_sided,
        t_pvalue_positive=t_pvalue_positive,
        sign_pvalue_two_sided=sign_pvalue,
        permutation_pvalue_positive=permutation_pvalue_positive,
        bootstrap_mean_ci_low=float(ci_low),
        bootstrap_mean_ci_high=float(ci_high),
        effect_size=effect_size,
        null_mean=float(null_mean),
        confidence_level=float(confidence_level),
    )


def yearly_trade_breakdown(results: BacktestResults) -> pd.DataFrame:
    frame = _trade_frame(results)
    if frame.empty:
        return pd.DataFrame(columns=["year", "trades", "total_profit", "avg_profit", "win_rate"])
    frame["closed_time"] = pd.to_datetime(frame["closed_time"], errors="coerce")
    frame = frame.dropna(subset=["closed_time"])
    frame["year"] = frame["closed_time"].dt.year.astype(int)
    yearly = (
        frame.groupby("year", as_index=False)
        .agg(
            trades=("profit", "size"),
            total_profit=("profit", "sum"),
            avg_profit=("profit", "mean"),
            median_profit=("profit", "median"),
            win_rate=("profit", lambda values: float((values > 0).mean())),
        )
        .sort_values("year")
        .reset_index(drop=True)
    )
    return yearly


def directional_trade_breakdown(results: BacktestResults) -> pd.DataFrame:
    frame = _trade_frame(results)
    if frame.empty:
        return pd.DataFrame(columns=["direction", "trades", "total_profit", "avg_profit", "win_rate"])
    breakdown = (
        frame.groupby("direction", as_index=False)
        .agg(
            trades=("profit", "size"),
            total_profit=("profit", "sum"),
            avg_profit=("profit", "mean"),
            median_profit=("profit", "median"),
            win_rate=("profit", lambda values: float((values > 0).mean())),
        )
        .sort_values("direction")
        .reset_index(drop=True)
    )
    return breakdown
