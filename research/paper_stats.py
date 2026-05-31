from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class OverlayComparisonResult:
    overlay: str
    baseline_overlay: str
    sample_size: int
    mean_delta_profit: float
    median_delta_profit: float
    std_delta_profit: float
    positive_window_rate: float
    t_statistic: float
    t_pvalue_two_sided: float
    t_pvalue_positive: float
    sign_pvalue_positive: float
    permutation_pvalue_positive: float
    bootstrap_ci_low: float
    bootstrap_ci_high: float

    @property
    def significant_positive(self) -> bool:
        return bool(
            self.sample_size > 0
            and self.bootstrap_ci_low > 0.0
            and self.t_pvalue_positive < 0.05
            and self.permutation_pvalue_positive < 0.05
        )

    def to_dict(self) -> dict[str, float | int | str | bool]:
        return {
            "overlay": self.overlay,
            "baseline_overlay": self.baseline_overlay,
            "sample_size": self.sample_size,
            "mean_delta_profit": self.mean_delta_profit,
            "median_delta_profit": self.median_delta_profit,
            "std_delta_profit": self.std_delta_profit,
            "positive_window_rate": self.positive_window_rate,
            "t_statistic": self.t_statistic,
            "t_pvalue_two_sided": self.t_pvalue_two_sided,
            "t_pvalue_positive": self.t_pvalue_positive,
            "sign_pvalue_positive": self.sign_pvalue_positive,
            "permutation_pvalue_positive": self.permutation_pvalue_positive,
            "bootstrap_ci_low": self.bootstrap_ci_low,
            "bootstrap_ci_high": self.bootstrap_ci_high,
            "significant_positive": self.significant_positive,
        }


def aligned_window_deltas(
    split_metrics: pd.DataFrame,
    *,
    baseline_overlay: str = "Baseline",
    metric: str = "oos_net_profit",
) -> pd.DataFrame:
    if split_metrics is None or split_metrics.empty:
        return pd.DataFrame()

    frame = split_metrics.copy()
    keys = ["window_id"]
    if "asset_id" in frame.columns:
        keys = ["asset_id", "window_id"]

    baseline = frame[frame["overlay"] == baseline_overlay][keys + [metric]].rename(columns={metric: "baseline_value"})
    if baseline.empty:
        return pd.DataFrame()

    rows: list[pd.DataFrame] = []
    for overlay in sorted(set(frame["overlay"]) - {baseline_overlay}):
        candidate = frame[frame["overlay"] == overlay][keys + [metric]].rename(columns={metric: "overlay_value"})
        merged = candidate.merge(baseline, on=keys, how="inner")
        if merged.empty:
            continue
        merged["overlay"] = overlay
        merged["baseline_overlay"] = baseline_overlay
        merged["metric"] = metric
        merged["delta"] = pd.to_numeric(merged["overlay_value"], errors="coerce") - pd.to_numeric(merged["baseline_value"], errors="coerce")
        rows.append(merged)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def compare_overlays_to_baseline(
    split_metrics: pd.DataFrame,
    *,
    baseline_overlay: str = "Baseline",
    metric: str = "oos_net_profit",
    bootstrap_samples: int = 4000,
    permutation_samples: int = 4000,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    deltas = aligned_window_deltas(split_metrics, baseline_overlay=baseline_overlay, metric=metric)
    if deltas.empty:
        return pd.DataFrame(), deltas

    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int | str | bool]] = []

    for overlay, frame in deltas.groupby("overlay", as_index=False):
        sample = pd.to_numeric(frame["delta"], errors="coerce").dropna().to_numpy(dtype=float)
        if len(sample) == 0:
            continue

        t_out = stats.ttest_1samp(sample, popmean=0.0)
        t_stat = float(0.0 if np.isnan(t_out.statistic) else t_out.statistic)
        t_pvalue_two_sided = float(1.0 if np.isnan(t_out.pvalue) else t_out.pvalue)
        t_pvalue_positive = float(1.0 - stats.t(df=max(len(sample) - 1, 1)).cdf(t_stat))

        wins = int(np.sum(sample > 0.0))
        sign_pvalue_positive = float(stats.binomtest(wins, n=len(sample), p=0.5, alternative="greater").pvalue)

        boot = rng.choice(sample, size=(int(bootstrap_samples), len(sample)), replace=True).mean(axis=1)
        ci_low, ci_high = np.percentile(boot, [2.5, 97.5])

        sign_flips = rng.choice([-1.0, 1.0], size=(int(permutation_samples), len(sample)), replace=True)
        perm_means = (sign_flips * sample).mean(axis=1)
        permutation_pvalue_positive = float(np.mean(perm_means >= sample.mean()))

        result = OverlayComparisonResult(
            overlay=str(overlay),
            baseline_overlay=baseline_overlay,
            sample_size=int(len(sample)),
            mean_delta_profit=float(sample.mean()),
            median_delta_profit=float(np.median(sample)),
            std_delta_profit=float(sample.std(ddof=1)) if len(sample) > 1 else 0.0,
            positive_window_rate=float(np.mean(sample > 0.0)),
            t_statistic=t_stat,
            t_pvalue_two_sided=t_pvalue_two_sided,
            t_pvalue_positive=t_pvalue_positive,
            sign_pvalue_positive=sign_pvalue_positive,
            permutation_pvalue_positive=permutation_pvalue_positive,
            bootstrap_ci_low=float(ci_low),
            bootstrap_ci_high=float(ci_high),
        )
        rows.append(result.to_dict())

    return pd.DataFrame(rows), deltas
