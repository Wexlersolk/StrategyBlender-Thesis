import pandas as pd

from engine.backtester import Backtester
from engine.base_strategy import BaseStrategy


class NoTradeStrategy(BaseStrategy):
    params = {}

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def on_bar(self, ctx):
        return


def test_no_trade_strategy_keeps_balance_constant():
    index = pd.date_range("2024-01-01", periods=6, freq="1h")
    df = pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105],
            "high": [101, 102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103, 104],
            "close": [100, 101, 102, 103, 104, 105],
            "volume": [1, 1, 1, 1, 1, 1],
        },
        index=index,
    )

    result = Backtester(initial_capital=50_000).run(NoTradeStrategy(), df)

    assert result.n_trades == 0
    assert result.net_profit == 0.0
    assert result.win_rate == 0.0
    assert result.max_drawdown == (0.0, 0.0)
    assert len(result.equity_curve) == 6
    assert result.equity_curve.iloc[0] == 50_000.0


class LookaheadCheatStrategy(BaseStrategy):
    """Tries to cheat by looking at the current bar close."""
    params = {}
    warmup = 0
    def compute_indicators(self, df):
        df["future_win"] = df["close"] > df["open"]
        return df
    def on_bar(self, ctx):
        # Accessing ctx.df should only give data up to i-1
        if ctx.has_position:
            ctx.close_all()
            return
        df = ctx.df
        try:
            # This should refer to i-1
            if df["future_win"].iloc[-1]:
                ctx.buy_market(sl=0, tp=0, lots=1)
        except (IndexError, KeyError):
            pass

def test_lookahead_bias_is_prevented():
    # Price alternates: Up, Down, Up, Down
    df = pd.DataFrame({
        "open":  [1.0, 1.1, 1.0, 1.1, 1.0],
        "high":  [1.2, 1.2, 1.2, 1.2, 1.2],
        "low":   [0.9, 0.9, 0.9, 0.9, 0.9],
        "close": [1.1, 1.0, 1.1, 1.0, 1.1],
        "volume": [1, 1, 1, 1, 1]
    }, index=pd.date_range("2024-01-01", periods=5, freq="h"))

    bt = Backtester(initial_capital=1000, lot_value=1000)
    result = bt.run(LookaheadCheatStrategy(), df)

    # If it could cheat, it would buy at 1.0 and sell at 1.1 (Bar 0, 2, 4)
    # But it can only see the PREVIOUS bar.
    # Bar 0: Win. Bar 1: Decision to buy based on Bar 0. Entry 1.1. 
    # Bar 2: Close at 1.0. Result: -0.1 (Loss).
    # Net Profit should be negative or zero, definitely not the cheated +300.
    assert result.net_profit < 0
