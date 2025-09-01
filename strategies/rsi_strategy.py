"""RSI Strategy module.

This module contains the RSIStrategy class for generating trades based on the Relative Strength Index (RSI).
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """Generates trades based on RSI strategy."""

    def __init__(self, market_data, initial_capital=100000, min_trade_unit=100, rsi_period=14, rsi_overbought=70, rsi_oversold=30):
        super().__init__(name="RSIStrategy")
        self.market_data = market_data
        self.initial_capital = initial_capital
        self.min_trade_unit = min_trade_unit
        self.current_capital = initial_capital
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    def calculate_rsi(self, prices, period):
        """Calculate the Relative Strength Index (RSI) for given prices."""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum()/period
        down = -seed[seed < 0].sum()/period
        rs = up/down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100./(1. + rs)

        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up/down if down != 0 else 0
            rsi[i] = 100. - 100./(1. + rs)

        return rsi

    def generate_trades(self):
        """Generate trade before and after positions based on RSI."""
        prices = self.market_data['open'].unstack('code')
        rsi_values = pd.DataFrame(index=prices.index, columns=prices.columns)
        for code in prices.columns:
            rsi_values[code] = self.calculate_rsi(prices[code].values, self.rsi_period)

        trade_dates = prices.index
        trades_before = []
        trades_after = []
        current_positions = {}

        for i in range(len(trade_dates)):
            date = trade_dates[i]
            if i > 0:
                prev_date = trade_dates[i-1]
                for code, qty in current_positions.items():
                    if qty > 0:
                        price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                        trades_before.append([date.strftime('%Y%m%d'), code, price, qty])

            rsi = rsi_values.loc[date].dropna()
            if len(rsi) == 0:
                continue

            oversold = rsi[rsi < self.rsi_oversold].index
            overbought = rsi[rsi > self.rsi_overbought].index

            available_capital = self.current_capital
            if available_capital < 0:
                available_capital = 0
            capital_per_etf = available_capital / len(oversold) if available_capital > 0 and len(oversold) > 0 else 0
            new_positions = {}
            total_invested = 0

            for code in oversold:
                price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                if price > 0:
                    qty = (capital_per_etf // (price * self.min_trade_unit)) * self.min_trade_unit
                    if qty > 0:
                        cost = qty * price
                        total_invested += cost
                        new_positions[code] = qty

            for code, qty in current_positions.items():
                if code in overbought and qty > 0:
                    price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                    if price > 0:
                        revenue = qty * price
                        self.current_capital += revenue
                        trades_after.append([date.strftime('%Y%m%d'), code, price, 0])
                elif code not in new_positions and qty > 0:
                    price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                    if price > 0:
                        revenue = qty * price
                        self.current_capital += revenue
                        trades_after.append([date.strftime('%Y%m%d'), code, price, 0])

            for code, qty in new_positions.items():
                price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                if price > 0:
                    cost = qty * price
                    self.current_capital -= cost
                    trades_after.append([date.strftime('%Y%m%d'), code, price, qty])

            current_positions = new_positions.copy()
            self.current_capital -= total_invested * 0.0006

        trades_before_df = pd.DataFrame(trades_before, columns=['交易时间', '标的', '价格', '数量'])
        trades_after_df = pd.DataFrame(trades_after, columns=['交易时间', '标的', '价格', '数量'])
        trades_before_df.to_csv('trade_before.csv', index=False)
        trades_after_df.to_csv('trade_after.csv', index=False)
        return trades_before_df, trades_after_df
