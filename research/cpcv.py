"""
research/cpcv.py

Combinatorial Purged Cross-Validation (CPCV).
Implements the method described by Marcos Lopez de Prado in 
"Advances in Financial Machine Learning".

CPCV splits the data into N groups and tests on all combinations of k groups,
ensuring purging and embargo between train and test sets.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import itertools
from dataclasses import dataclass
from typing import List, Callable, Type
from engine.backtester import Backtester
from engine.base_strategy import BaseStrategy
from engine.results import BacktestResults


@dataclass
class CPCVSplit:
    split_id: int
    train_ranges: List[tuple[pd.Timestamp, pd.Timestamp]]
    test_ranges: List[tuple[pd.Timestamp, pd.Timestamp]]


class CPCV:
    def __init__(
        self,
        n_groups: int = 6,
        k_test_groups: int = 2,
        embargo_pct: float = 0.01,
    ):
        self.n_groups = n_groups
        self.k_test_groups = k_test_groups
        self.embargo_pct = embargo_pct

    def generate_splits(self, index: pd.Index) -> List[CPCVSplit]:
        n = len(index)
        group_size = n // self.n_groups
        group_indices = [
            (i * group_size, (i + 1) * group_size) for i in range(self.n_groups)
        ]
        # Adjust last group to end of index
        group_indices[-1] = (group_indices[-1][0], n)

        group_ranges = [
            (index[start], index[end - 1]) for start, end in group_indices
        ]

        combos = list(itertools.combinations(range(self.n_groups), self.k_test_groups))
        splits = []

        for i, test_indices in enumerate(combos):
            test_ranges = [group_ranges[idx] for idx in test_indices]
            
            # Train indices are those not in test
            train_indices = [idx for idx in range(self.n_groups) if idx not in test_indices]
            
            # Purging & Embargo: 
            # In AFML, we purge the end of training sets that overlap with test sets.
            # Here we simplify: train on non-test groups, with a small embargo buffer.
            embargo_bars = int(n * self.embargo_pct)
            
            train_ranges = []
            for idx in train_indices:
                g_start_idx, g_end_idx = group_indices[idx]
                
                # If a test group follows this train group, embargo the end of train
                if (idx + 1) in test_indices:
                    g_end_idx = max(g_start_idx, g_end_idx - embargo_bars)
                
                # If a test group precedes this train group, purge the start of train
                if (idx - 1) in test_indices:
                    g_start_idx = min(g_end_idx, g_start_idx + embargo_bars)
                
                if g_end_idx > g_start_idx:
                    train_ranges.append((index[g_start_idx], index[g_end_idx - 1]))

            splits.append(CPCVSplit(
                split_id=i,
                train_ranges=train_ranges,
                test_ranges=test_ranges
            ))

        return splits

    def run(
        self,
        strategy_class: Type[BaseStrategy],
        df: pd.DataFrame,
        backtester_kwargs: dict = None,
    ) -> List[BacktestResults]:
        """
        Run CPCV. Returns a list of BacktestResults, one for each test path.
        Note: AFML CPCV actually produces 'paths' by concatenating test results.
        With N=6, k=2, we have 15 combinations. Each combination tests 2/6 = 33% of data.
        Each bar in the dataset will be part of the test set in exactly 
        binom(N-1, k-1) combinations.
        """
        if backtester_kwargs is None:
            backtester_kwargs = {}

        splits = self.generate_splits(df.index)
        results = []

        print(f"Running CPCV with {self.n_groups} groups, testing on {self.k_test_groups} groups.")
        print(f"Total combinations: {len(splits)}")

        for split in splits:
            # 1. Train (Optional: Optimize parameters on train_ranges)
            # In this simple implementation, we just use the provided strategy_class
            # as is, or we could run an optimizer here.
            
            # 2. Test
            # Combine all test ranges into one DF for the backtester
            # Note: Backtester usually expects continuous data. 
            # We might need to run backtester on each range separately and combine.
            
            test_trades = []
            for start, end in split.test_ranges:
                test_df = df[(df.index >= start) & (df.index <= end)].copy()
                if test_df.empty:
                    continue
                
                bt = Backtester(**backtester_kwargs)
                res = bt.run(strategy_class(), test_df)
                test_trades.extend(res.trades)
            
            # Create a combined result for this split
            # (Simplified: just storing the trades)
            combined_res = BacktestResults(
                trades=test_trades,
                initial_capital=backtester_kwargs.get("initial_capital", 100000.0),
                symbol=getattr(strategy_class, "symbol", "CPCV"),
                timeframe="",
                date_from=df.index[0],
                date_to=df.index[-1],
                params={}
            )
            results.append(combined_res)

        return results
