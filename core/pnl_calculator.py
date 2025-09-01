"""PNL Calculator module.

This module contains the PNLCalculator class for calculating profit and loss for trades.
"""

import pandas as pd


class PNLCalculator:
    """Calculates PNL for each trade."""

    def __init__(self, market_data, trade_before, trade_after):
        self.market_data = market_data
        self.trade_before = trade_before
        self.trade_after = trade_after
        self.fee_rate = 0.0006

    def calculate_pnl(self):
        """Calculate PNL per trade."""
        pnls = []
        trade_dates = sorted(set(self.trade_before['交易时间']).union(set(self.trade_after['交易时间'])))

        for i in range(len(trade_dates)):
            if i == 0:
                continue
            date_before = trade_dates[i-1]
            date_after = trade_dates[i]
            before_positions = self.trade_before[self.trade_before['交易时间'] == date_before]
            after_positions = self.trade_after[self.trade_after['交易时间'] == date_after]
            if before_positions.empty or after_positions.empty:
                continue

            total_pnl = 0
            total_fee = 0
            # 合并前后持仓数据以计算变化
            before_dict = dict(zip(before_positions['标的'], before_positions['数量']))
            after_dict = dict(zip(after_positions['标的'], after_positions['价格']))
            codes = set(before_dict.keys()).union(set(after_dict.keys()))

            for code in codes:
                qty_before = before_dict.get(code, 0)
                qty_after = after_dict.get(code, 0)
                if qty_before != qty_after:
                    price = after_dict.get(code, self.market_data.loc[(date_after, code), 'open'] if (date_after, code) in self.market_data.index else 0)
                    if price > 0:
                        qty_change = qty_after - qty_before
                        if qty_change < 0:  # 卖出
                            pnl = (price - before_positions[before_positions['标的'] == code]['价格'].iloc[0] if not before_positions[before_positions['标的'] == code].empty else 0) * abs(qty_change)
                            total_pnl += pnl
                        fee = abs(qty_change) * price * self.fee_rate
                        total_fee += fee

            total_pnl -= total_fee
            pnls.append({'date': date_after, 'pnl': total_pnl, 'fee': total_fee})

        return pd.DataFrame(pnls)
