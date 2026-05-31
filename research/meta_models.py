from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from engine.policy import POLICY_FEATURE_NAMES


CURATED_CONTEXT_FEATURES = {
    "ctx_bar_return",
    "ctx_bar_range",
    "ctx_bar_range_pct",
}

CURATED_CONTEXT_PREFIXES = (
    "ctx_rel_ema",
    "ctx_rel_sma",
    "ctx_rel_kama",
    "ctx_rel_rsi",
    "ctx_rel_atr",
    "ctx_rel_qqe",
    "ctx_rel_stoch",
    "ctx_rel_keltner",
    "ctx_rel_ichimoku",
    "ctx_rel_wpr",
    "ctx_rel_ao",
    "ctx_rel_ulcer",
    "ctx_rel_pivot",
    "ctx_rel_channel",
    "ctx_rel_heiken",
    "ctx_rel_wavetrend",
    "ctx_rel_smma",
)

MAX_DYNAMIC_CONTEXT_FEATURES = 12


def _safe_series(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default)


def _selected_feature_suffixes(dataset: pd.DataFrame) -> list[str]:
    available = [
        str(column)[len("feature_") :]
        for column in dataset.columns
        if str(column).startswith("feature_")
    ]
    selected: list[str] = list(POLICY_FEATURE_NAMES)
    dynamic_candidates: list[str] = []
    for suffix in sorted(set(available)):
        if suffix in POLICY_FEATURE_NAMES:
            continue
        if suffix in CURATED_CONTEXT_FEATURES or suffix.startswith(CURATED_CONTEXT_PREFIXES):
            dynamic_candidates.append(suffix)
    if dynamic_candidates:
        profit_col = _safe_series(dataset, "realized_net_profit", 0.0)
        if float(profit_col.std(ddof=0)) >= 1e-9:
            ranked: list[tuple[float, str]] = []
            for suffix in dynamic_candidates:
                values = _safe_series(dataset, f"feature_{suffix}", 0.0)
                if float(values.std(ddof=0)) < 1e-9:
                    continue
                corr = values.corr(profit_col)
                score = abs(float(corr)) if pd.notna(corr) else 0.0
                ranked.append((score, suffix))
            ranked.sort(key=lambda item: item[0], reverse=True)
            selected.extend([suffix for _, suffix in ranked[:MAX_DYNAMIC_CONTEXT_FEATURES]])
    return list(dict.fromkeys(selected))


def build_policy_feature_frame(dataset: pd.DataFrame) -> pd.DataFrame:
    if dataset is None or dataset.empty:
        return pd.DataFrame(columns=POLICY_FEATURE_NAMES)

    frame = pd.DataFrame(index=dataset.index)
    time_col = pd.to_datetime(dataset.get("time"), errors="coerce")

    ordered_feature_names = _selected_feature_suffixes(dataset)
    for name in ordered_feature_names:
        frame[name] = _safe_series(dataset, f"feature_{name}", 0.0)
    direction = dataset["direction"] if "direction" in dataset.columns else pd.Series("", index=dataset.index)
    order_type = dataset["order_type"] if "order_type" in dataset.columns else pd.Series("", index=dataset.index)
    frame["is_long"] = (direction == "long").astype(float)
    frame["is_short"] = (direction == "short").astype(float)
    frame["is_market_order"] = (order_type == "market").astype(float)
    frame["is_pending_order"] = 1.0 - frame["is_market_order"]
    frame["hour_of_day"] = pd.Series(time_col.dt.hour, index=dataset.index).fillna(0).astype(float)
    frame["weekday"] = pd.Series(time_col.dt.weekday, index=dataset.index).fillna(0).astype(float)
    symbol = dataset["symbol"] if "symbol" in dataset.columns else pd.Series("", index=dataset.index)
    timeframe = dataset["timeframe"] if "timeframe" in dataset.columns else pd.Series("", index=dataset.index)
    for value in sorted({str(item) for item in symbol.fillna("").unique() if str(item)}):
        frame[f"symbol::{value}"] = (symbol == value).astype(float)
    for value in sorted({str(item) for item in timeframe.fillna("").unique() if str(item)}):
        frame[f"timeframe::{value}"] = (timeframe == value).astype(float)
    return frame.astype(float)


def _standardize_features(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = frame.to_numpy(dtype=float)
    means = values.mean(axis=0)
    stds = values.std(axis=0)
    stds[stds < 1e-9] = 1.0
    standardized = np.clip((values - means) / stds, -5.0, 5.0)
    return standardized, means, stds


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def _classification_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    preds = (probabilities >= threshold).astype(int)
    tp = float(np.sum((preds == 1) & (y_true == 1)))
    tn = float(np.sum((preds == 0) & (y_true == 0)))
    fp = float(np.sum((preds == 1) & (y_true == 0)))
    fn = float(np.sum((preds == 0) & (y_true == 1)))
    accuracy = (tp + tn) / max(len(y_true), 1)
    precision = tp / max(tp + fp, 1.0)
    recall = tp / max(tp + fn, 1.0)
    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "positive_rate": float(np.mean(preds)) if len(preds) else 0.0,
    }


def _fit_group_thresholds(
    dataset: pd.DataFrame,
    probabilities: np.ndarray,
    profits: np.ndarray,
    *,
    min_trade_rate: float,
    default_threshold: float,
) -> dict[str, float]:
    if dataset.empty or "symbol" not in dataset.columns:
        return {}
    symbol_series = dataset["symbol"].fillna("").astype(str)
    thresholds: dict[str, float] = {}
    for symbol in sorted({value for value in symbol_series.unique() if value}):
        mask = symbol_series == symbol
        if int(mask.sum()) < 10:
            continue
        min_count = max(5, int(np.ceil(int(mask.sum()) * float(min_trade_rate))))
        best_threshold = float(default_threshold)
        best_score = float("-inf")
        local_probabilities = probabilities[mask.to_numpy()]
        local_profits = profits[mask.to_numpy()]
        for candidate in np.linspace(0.05, 0.95, 19):
            accepted = local_probabilities >= float(candidate)
            count = int(np.sum(accepted))
            if count < min_count:
                continue
            accepted_profits = local_profits[accepted]
            score = float(np.sum(accepted_profits) / np.sqrt(max(count, 1)))
            if score > best_score:
                best_score = score
                best_threshold = float(candidate)
        thresholds[str(symbol)] = float(best_threshold)
    return thresholds


def _safe_group_key(frame: pd.DataFrame, column: str, default: str = "unknown") -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=str)
    return frame[column].fillna(default).astype(str)


def _compute_filter_targets(
    dataset: pd.DataFrame,
    *,
    positive_return_cutoff: float,
    label_mode: str,
    top_quantile: float,
    cost_buffer_fraction: float,
) -> tuple[np.ndarray, dict[str, float | str]]:
    working = dataset.copy()
    profits = _safe_series(working, "realized_net_profit", 0.0)
    symbol = _safe_group_key(working, "symbol", "unknown")
    direction = _safe_group_key(working, "direction", "flat")
    comment = _safe_group_key(working, "comment", "")

    non_zero_profit = profits[profits.abs() > 1e-9].abs()
    fallback_scale = float(non_zero_profit.median()) if not non_zero_profit.empty else 0.0
    raw_positive = profits > float(positive_return_cutoff)

    symbol_quantiles = profits.groupby(symbol).transform(
        lambda values: float(values.quantile(float(top_quantile))) if len(values) >= 4 else float(values.median())
    )
    top_quantile_positive = profits >= symbol_quantiles

    symbol_buffers = profits.groupby(symbol).transform(
        lambda values: max(
            float(positive_return_cutoff),
            float(values.abs().median()) * float(cost_buffer_fraction) if len(values) else 0.0,
        )
    )
    cost_buffer_positive = profits > symbol_buffers

    regime_key = symbol + "|" + direction + "|" + comment.replace("", "")
    regime_baseline = profits.groupby(regime_key).transform(
        lambda values: float(values.median()) if len(values) >= 3 else float(values.mean()) if len(values) else 0.0
    )
    regime_relative_positive = profits > regime_baseline

    mode = str(label_mode or "hybrid").strip().lower()
    if mode == "net_profit":
        target = raw_positive
    elif mode == "cost_buffer":
        target = cost_buffer_positive
    elif mode == "top_quantile":
        target = top_quantile_positive
    elif mode == "regime_relative":
        target = regime_relative_positive
    else:
        composite_score = (
            cost_buffer_positive.astype(int)
            + top_quantile_positive.astype(int)
            + regime_relative_positive.astype(int)
        )
        target = (composite_score >= 2) | (raw_positive & top_quantile_positive)

    if len(np.unique(target.astype(int))) < 2:
        target = raw_positive

    summary = {
        "label_mode": mode,
        "top_quantile": float(top_quantile),
        "cost_buffer_fraction": float(cost_buffer_fraction),
        "median_abs_profit": float(fallback_scale),
        "positive_rate": float(target.mean()) if len(target) else 0.0,
    }
    return target.astype(float).to_numpy(), summary


def _time_ordered_calibration_split(length: int, fraction: float = 0.25) -> tuple[np.ndarray, np.ndarray]:
    if length < 12:
        indices = np.arange(length)
        return indices, indices
    calib_size = max(8, int(np.ceil(length * float(fraction))))
    calib_size = min(calib_size, max(length - 4, 1))
    split_idx = max(length - calib_size, 1)
    return np.arange(split_idx), np.arange(split_idx, length)


def _fit_probability_calibrator(
    x: np.ndarray,
    target: np.ndarray,
) -> tuple[dict, np.ndarray]:
    train_idx, calib_idx = _time_ordered_calibration_split(len(target))
    if len(train_idx) < 4 or len(calib_idx) < 4 or len(np.unique(target[train_idx])) < 2:
        full_model = LogisticRegression(
            C=0.05,
            solver="liblinear",
            class_weight="balanced",
            max_iter=2000,
            random_state=42,
        )
        full_model.fit(x, target.astype(int))
        raw_full = full_model.predict_proba(x)[:, 1]
        return (
            {
                "base_coefficients": full_model.coef_[0].astype(float).tolist(),
                "base_intercept": float(full_model.intercept_[0]),
                "score_temperature": 1.75,
                "calibration_type": "none",
                "calibration_model": {},
            },
            raw_full,
        )

    base_model = LogisticRegression(
        C=0.05,
        solver="liblinear",
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )
    base_model.fit(x[train_idx], target[train_idx].astype(int))
    raw_calib = base_model.predict_proba(x[calib_idx])[:, 1]
    calibration_target = target[calib_idx].astype(int)
    if len(np.unique(calibration_target)) < 2:
        raw_full = base_model.predict_proba(x)[:, 1]
        return (
            {
                "base_coefficients": base_model.coef_[0].astype(float).tolist(),
                "base_intercept": float(base_model.intercept_[0]),
                "score_temperature": 1.75,
                "calibration_type": "none",
                "calibration_model": {},
            },
            raw_full,
        )

    platt = LogisticRegression(
        C=0.5,
        solver="lbfgs",
        max_iter=2000,
        random_state=42,
    )
    platt.fit(_logit(raw_calib).reshape(-1, 1), calibration_target)
    calibration_model = {
        "coefficient": float(platt.coef_[0][0]),
        "intercept": float(platt.intercept_[0]),
    }
    calibration_type = "platt"

    full_model = LogisticRegression(
        C=0.05,
        solver="liblinear",
        class_weight="balanced",
        max_iter=2000,
        random_state=42,
    )
    full_model.fit(x, target.astype(int))
    raw_full = full_model.predict_proba(x)[:, 1]
    return (
        {
            "base_coefficients": full_model.coef_[0].astype(float).tolist(),
            "base_intercept": float(full_model.intercept_[0]),
            "score_temperature": 1.75,
            "calibration_type": calibration_type,
            "calibration_model": calibration_model,
        },
        raw_full,
    )


def _apply_probability_calibration(probabilities: np.ndarray, calibration_type: str, calibration_model: dict) -> np.ndarray:
    raw = np.clip(np.asarray(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
    mode = str(calibration_type or "none").lower()
    if mode == "isotonic":
        xs = np.asarray(calibration_model.get("x_thresholds", []), dtype=float)
        ys = np.asarray(calibration_model.get("y_thresholds", []), dtype=float)
        if len(xs) >= 2 and len(xs) == len(ys):
            return np.interp(raw, xs, ys, left=ys[0], right=ys[-1])
        return raw
    if mode == "platt":
        coef = float(calibration_model.get("coefficient", 1.0))
        intercept = float(calibration_model.get("intercept", 0.0))
        calibrated = _sigmoid(_logit(raw) * coef + intercept)
        return np.clip(calibrated, 0.02, 0.98)
    return np.clip(raw, 0.02, 0.98)


def fit_filter_model(
    dataset: pd.DataFrame,
    *,
    threshold: float = 0.55,
    positive_return_cutoff: float = 0.0,
    iterations: int = 500,
    learning_rate: float = 0.05,
    l2: float = 0.01,
    optimize_threshold: bool = True,
    min_trade_rate: float = 0.15,
    executed_only: bool = True,
    label_mode: str = "hybrid",
    top_quantile: float = 0.65,
    cost_buffer_fraction: float = 0.25,
) -> dict:
    training_dataset = dataset.copy()
    if executed_only and "trade_taken" in training_dataset.columns:
        executed_mask = pd.to_numeric(training_dataset["trade_taken"], errors="coerce").fillna(0.0) > 0.0
        executed_dataset = training_dataset.loc[executed_mask].copy()
        if not executed_dataset.empty:
            training_dataset = executed_dataset

    features = build_policy_feature_frame(training_dataset)
    if features.empty:
        raise ValueError("Dataset is empty.")

    target, target_summary = _compute_filter_targets(
        training_dataset,
        positive_return_cutoff=float(positive_return_cutoff),
        label_mode=label_mode,
        top_quantile=float(top_quantile),
        cost_buffer_fraction=float(cost_buffer_fraction),
    )
    if len(np.unique(target)) < 2:
        raise ValueError("Filter model needs both positive and negative outcomes.")

    x, means, stds = _standardize_features(features)
    positives = float(target.sum())
    negatives = float(len(target) - positives)
    if positives <= 0.0 or negatives <= 0.0:
        raise ValueError("Filter model needs both positive and negative outcomes.")
    calibration_artifact, raw_probabilities = _fit_probability_calibrator(x, target)
    temperature = float(calibration_artifact.get("score_temperature", 1.0))
    raw_probabilities = _sigmoid(_logit(raw_probabilities) / max(temperature, 1e-6))
    probabilities = _apply_probability_calibration(
        raw_probabilities,
        calibration_artifact.get("calibration_type", "none"),
        calibration_artifact.get("calibration_model", {}),
    )
    selected_threshold = float(threshold)
    if optimize_threshold and len(probabilities) >= 25:
        profits = _safe_series(training_dataset, "realized_net_profit", 0.0).to_numpy(dtype=float)
        min_count = max(10, int(np.ceil(len(probabilities) * float(min_trade_rate))))
        best_score = float("-inf")
        for candidate in np.linspace(0.05, 0.95, 19):
            accepted = probabilities >= float(candidate)
            count = int(np.sum(accepted))
            if count < min_count:
                continue
            accepted_profits = profits[accepted]
            score = float(np.sum(accepted_profits) / np.sqrt(max(count, 1)))
            if score > best_score:
                best_score = score
                selected_threshold = float(candidate)
    profits = _safe_series(training_dataset, "realized_net_profit", 0.0).to_numpy(dtype=float)
    thresholds_by_symbol = _fit_group_thresholds(
        training_dataset,
        probabilities,
        profits,
        min_trade_rate=float(min_trade_rate),
        default_threshold=float(selected_threshold),
    )
    metrics = _classification_metrics(target, probabilities, float(selected_threshold))
    metrics["avg_probability"] = float(probabilities.mean())
    metrics["class_balance"] = float(target.mean())

    return {
        "kind": "filter",
        "feature_names": list(features.columns),
        "feature_means": means.tolist(),
        "feature_stds": stds.tolist(),
        "coefficients": list(calibration_artifact["base_coefficients"]),
        "intercept": float(calibration_artifact["base_intercept"]),
        "probability_threshold": float(selected_threshold),
        "threshold_by_symbol": thresholds_by_symbol,
        "positive_return_cutoff": float(positive_return_cutoff),
        "label_mode": str(label_mode),
        "top_quantile": float(top_quantile),
        "cost_buffer_fraction": float(cost_buffer_fraction),
        "model_type": "sklearn_logistic",
        "score_temperature": float(calibration_artifact.get("score_temperature", 1.0)),
        "calibration_type": str(calibration_artifact.get("calibration_type", "none")),
        "calibration_model": dict(calibration_artifact.get("calibration_model", {})),
        "metrics": metrics,
        "target_summary": target_summary,
        "sample_size": int(len(features)),
        "executed_only": bool(executed_only),
    }


def fit_sizing_model(
    dataset: pd.DataFrame,
    *,
    min_multiplier: float = 0.50,
    max_multiplier: float = 1.50,
    l2: float = 1.0,
) -> dict:
    features = build_policy_feature_frame(dataset)
    if features.empty:
        raise ValueError("Dataset is empty.")

    target = _safe_series(dataset, "realized_net_profit", 0.0).to_numpy(dtype=float)
    if len(target) < 3:
        raise ValueError("Sizing model needs at least 3 samples.")

    x, means, stds = _standardize_features(features)
    x_design = np.column_stack([x, np.ones(len(x), dtype=float)])
    ridge = np.eye(x_design.shape[1], dtype=float) * float(l2)
    ridge[-1, -1] = 0.0
    coefs = np.linalg.solve(x_design.T @ x_design + ridge, x_design.T @ target)

    predictions = x_design @ coefs
    mse = float(np.mean((predictions - target) ** 2))
    denom = float(np.sum((target - target.mean()) ** 2))
    r2 = 0.0 if denom < 1e-9 else float(1.0 - np.sum((predictions - target) ** 2) / denom)
    scale = float(np.std(target, ddof=0))
    if scale < 1e-6:
        scale = max(abs(float(target.mean())), 1.0)

    return {
        "kind": "sizing",
        "feature_names": list(features.columns),
        "feature_means": means.tolist(),
        "feature_stds": stds.tolist(),
        "coefficients": coefs[:-1].tolist(),
        "intercept": float(coefs[-1]),
        "target_scale": float(scale),
        "min_multiplier": float(min_multiplier),
        "max_multiplier": float(max_multiplier),
        "metrics": {
            "mse": mse,
            "r2": r2,
            "avg_predicted_profit": float(predictions.mean()),
        },
        "sample_size": int(len(features)),
    }


def predict_filter_probabilities(dataset: pd.DataFrame, model: dict) -> pd.Series:
    features = build_policy_feature_frame(dataset).reindex(columns=model["feature_names"], fill_value=0.0)
    values = features.to_numpy(dtype=float)
    means = np.asarray(model["feature_means"], dtype=float)
    stds = np.asarray(model["feature_stds"], dtype=float)
    stds[stds < 1e-9] = 1.0
    x = (values - means) / stds
    raw = _sigmoid(x @ np.asarray(model["coefficients"], dtype=float) + float(model["intercept"]))
    raw = _sigmoid(_logit(raw) / max(float(model.get("score_temperature", 1.0)), 1e-6))
    probs = _apply_probability_calibration(
        raw,
        str(model.get("calibration_type", "none")),
        dict(model.get("calibration_model", {})),
    )
    return pd.Series(probs, index=dataset.index, dtype=float)


def predict_sizing_signal(dataset: pd.DataFrame, model: dict) -> pd.Series:
    features = build_policy_feature_frame(dataset).reindex(columns=model["feature_names"], fill_value=0.0)
    values = features.to_numpy(dtype=float)
    means = np.asarray(model["feature_means"], dtype=float)
    stds = np.asarray(model["feature_stds"], dtype=float)
    stds[stds < 1e-9] = 1.0
    x = (values - means) / stds
    preds = x @ np.asarray(model["coefficients"], dtype=float) + float(model["intercept"])
    return pd.Series(preds, index=dataset.index, dtype=float)


@dataclass
class OverlayResearchArtifact:
    filter_model: dict
    sizing_model: dict
    dataset_summary: dict
    benchmark_name: str
    benchmark_settings: dict

    def to_dict(self) -> dict:
        return {
            "filter_model": self.filter_model,
            "sizing_model": self.sizing_model,
            "dataset_summary": self.dataset_summary,
            "benchmark_name": self.benchmark_name,
            "benchmark_settings": self.benchmark_settings,
        }
