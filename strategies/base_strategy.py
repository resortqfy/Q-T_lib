"""Base Strategy module.

This module contains the base class for trading strategies.
"""

class BaseStrategy:
    """Base class for trading strategies."""

    def __init__(self, name):
        self.name = name

    def generate_trades(self, market_data, initial_capital=100000, min_trade_unit=100):
        """Generate trades based on the strategy.

        Args:
            market_data: Market data to base the trades on.
            initial_capital: Initial capital for trading.
            min_trade_unit: Minimum trade unit.

        Returns:
            Tuple of DataFrames: trades before and after.
        """
        raise NotImplementedError("generate_trades method must be implemented in subclass")
