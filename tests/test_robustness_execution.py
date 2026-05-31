import pandas as pd
import numpy as np
from engine.backtester import Backtester
from engine.base_strategy import BaseStrategy
from research.monte_carlo import run_monte_carlo
from research.param_search import grid_search, stability_mapping, check_stability

class SimpleStrategy(BaseStrategy):
    params = {"lots": 1.0}
    warmup = 0
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
    def on_bar(self, ctx):
        if ctx.bar_index % 10 == 0 and not ctx.has_position:
            ctx.buy_market(sl=0, tp=0, lots=self.params["lots"])
        elif ctx.has_position:
            ctx.close_all()

def test_monte_carlo_skip_trades():
    index = pd.date_range("2024-01-01", periods=100, freq="1h")
    df = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100}, index=index)
    
    bt = Backtester()
    res = bt.run(SimpleStrategy(), df)
    
    mc = run_monte_carlo(res, n_simulations=10, method="skip_trades", skip_pct=0.5)
    assert mc.n_simulations == 10
    assert mc.equity_paths.shape[1] < len(res.profits)

def test_market_impact():
    index = pd.date_range("2024-01-01", periods=100, freq="1h")
    df = pd.DataFrame({"open": 100, "high": 101, "low": 99, "close": 100}, index=index)
    
    # No impact
    bt1 = Backtester(market_impact_coef=0.0)
    res1 = bt1.run(SimpleStrategy(lots=10.0), df)
    
    # High impact
    bt2 = Backtester(market_impact_coef=0.01) # 1% impact per lot
    res2 = bt2.run(SimpleStrategy(lots=10.0), df)
    
    assert res1.n_trades > 0
    assert res2.n_trades > 0
    assert res2.trades[0].entry_price > res1.trades[0].entry_price
    assert res2.trades[0].entry_price >= res1.trades[0].entry_price + 10.0

def test_volume_limit():
    index = pd.date_range("2024-01-01", periods=100, freq="1h")
    df = pd.DataFrame({
        "open": 100, "high": 101, "low": 99, "close": 100,
        "tick_volume": [5.0] * 100
    }, index=index)
    
    bt = Backtester(max_volume_pct=0.5)
    res = bt.run(SimpleStrategy(lots=10.0), df)
    
    assert res.n_trades == 0

def test_stability_mapping():
    # 10 results, one outlier
    data = [{"sharpe_ratio": 1.0}] * 9
    data.append({"sharpe_ratio": 10.0})
    results = pd.DataFrame(data)
    results["p1"] = range(10)
    results["p2"] = 1
    
    stability = check_stability(results.sort_values("sharpe_ratio", ascending=False))
    assert stability["is_fragile"] == True
