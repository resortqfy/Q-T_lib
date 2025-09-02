"""Mean Reversion Strategy module.

This module contains the MeanReversionStrategy class for generating trades based on mean reversion.
"""

import pandas as pd
from .base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """Generates trades based on mean reversion strategy."""

    def __init__(self, market_data, initial_capital=100000, min_trade_unit=100, window=20, threshold=2.0):
        super().__init__(name="MeanReversionStrategy")
        self.market_data = market_data
        self.initial_capital = initial_capital
        self.min_trade_unit = min_trade_unit
        self.current_capital = initial_capital
        self.window = window
        self.threshold = threshold
        self.first_trade = True
        self.total_pnl = 0

    def generate_trades(self):
        """Generate trade before and after positions based on mean reversion."""
        # 计算每个ETF的均值和标准差
        prices = self.market_data['open'].unstack('code')
        mean_prices = prices.rolling(window=self.window).mean()
        std_prices = prices.rolling(window=self.window).std()
        z_scores = (prices - mean_prices) / std_prices
        
        # 获取所有交易日期
        trade_dates = prices.index
        # 确保交易日期不超过市场数据的最新日期
        max_date = self.market_data.index.get_level_values('date').max()
        trade_dates = trade_dates[trade_dates <= max_date]
        trades_before = []
        trades_after = []
        current_positions = {}

        for i in range(len(trade_dates)):
            date = trade_dates[i]
            if i > 0:
                prev_date = trade_dates[i-1]
                # 记录交易前的持仓
                for code, qty in current_positions.items():
                    if qty > 0:
                        price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                        trades_before.append([date.strftime('%Y%m%d'), code, price, qty])

            # 获取当前日期的z分数数据，考虑所有标的
            z_score = z_scores.loc[date].dropna()
            if len(z_score) == 0:
                continue
            # 选择z分数低于阈值的ETF（价格低于均值，预期会回升），综合考虑所有标的
            undervalued = z_score[z_score < -self.threshold].index
            # 计算可用于投资的金额
            available_capital = self.current_capital
            if self.first_trade:
                available_capital = min(self.initial_capital, 100000)
            else:
                available_capital = self.initial_capital + self.total_pnl
            if available_capital < 0:
                available_capital = 0

            capital_per_etf = available_capital / len(undervalued) if available_capital > 0 and len(undervalued) > 0 else 0
            new_positions = {}
            total_invested = 0

            # 决定新的持仓
            for code in undervalued:
                price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                if price > 0:
                    qty = (capital_per_etf // (price * self.min_trade_unit)) * self.min_trade_unit
                    if qty > 0:
                        cost = qty * price
                        total_invested += cost
                        new_positions[code] = qty

            # 卖出不在新持仓中的ETF
            for code, qty in current_positions.items():
                if code not in new_positions and qty > 0:
                    price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                    if price > 0:
                        revenue = qty * price
                        self.current_capital += revenue
                        self.total_pnl += revenue - (qty * price * 0.0006)  # 扣除交易手续费
                        trades_after.append([date.strftime('%Y%m%d'), code, price, 0])

            # 买入新的持仓
            for code, qty in new_positions.items():
                price = self.market_data.loc[(date, code), 'open'] if (date, code) in self.market_data.index else 0
                if price > 0:
                    cost = qty * price
                    self.current_capital -= cost
                    self.total_pnl -= cost + (cost * 0.0006)  # 扣除交易手续费
                    trades_after.append([date.strftime('%Y%m%d'), code, price, qty])

            current_positions = new_positions.copy()
            self.current_capital -= total_invested * 0.0006  # 扣除交易手续费
            if self.first_trade and total_invested > 0:
                self.first_trade = False

        trades_before_df = pd.DataFrame(trades_before, columns=['交易时间', '标的', '价格', '数量'])
        trades_after_df = pd.DataFrame(trades_after, columns=['交易时间', '标的', '价格', '数量'])
        trades_before_df.to_csv('trade_before.csv', index=False)
        trades_after_df.to_csv('trade_after.csv', index=False)

        return trades_before_df, trades_after_df
