"""RSI Strategy module.

This module contains the RSIStrategy class for generating trades based on the Relative Strength Index (RSI).
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """
    RSI 策略 (改进版)

    逻辑：
    - RSI < rsi_oversold: 买入（若尚未持有），或可选择加仓（此处为只在空仓->建仓）
    - RSI > rsi_overbought: 卖出
    - 介于区间：保持原持仓

    输出格式同动量策略（before / after 快照）。
    """

    def __init__(self,
                 market_data: pd.DataFrame,
                 initial_capital: float = 100000,
                 min_trade_unit: int = 100,
                 rsi_period: int = 14,
                 rsi_overbought: float = 70,
                 rsi_oversold: float = 30,
                 fee_rate: float = 0.0006):
        super().__init__(name="RSIStrategy")
        if not isinstance(market_data.index, pd.MultiIndex):
            raise ValueError("market_data 必须是 MultiIndex (date, code)")
        if 'open' not in market_data.columns:
            raise ValueError("market_data 需要包含列 'open'")
        self.market_data = market_data.sort_index()
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.min_trade_unit = min_trade_unit
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.fee_rate = fee_rate

        self.positions = {}    # code -> qty
        self.cost_basis = {}   # code -> price

    def _format_date(self, date_val):
        if isinstance(date_val, (pd.Timestamp, np.datetime64)):
            return pd.Timestamp(date_val).strftime("%Y%m%d")
        s = str(date_val)
        if '-' in s:
            return s.replace('-', '')
        return s

    def _compute_rsi(self, series: pd.Series) -> pd.Series:
        """
        经典 Wilder RSI 实现
        """
        prices = series.astype(float)
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1/self.rsi_period, adjust=False, min_periods=self.rsi_period).mean()
        avg_loss = loss.ewm(alpha=1/self.rsi_period, adjust=False, min_periods=self.rsi_period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_trades(self):
        prices = self.market_data['open'].unstack('code')
        rsi_df = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)

        # 计算每个标的 RSI
        for code in prices.columns:
            rsi_df[code] = self._compute_rsi(prices[code])

        all_dates = prices.index
        max_date = self.market_data.index.get_level_values('date').max()
        all_dates = all_dates[all_dates <= max_date]

        trade_before_rows = []
        trade_after_rows = []

        for date in all_dates:
            day_prices = prices.loc[date]
            day_rsi = rsi_df.loc[date]

            # 若当日 RSI 全缺失，跳过（但需要写维持不变的 after 吗？如果你想严格每日都有 after，可补）
            if day_rsi.isna().all():
                continue

            # -------- 1. before 快照 --------
            if self.positions:
                for code, qty in self.positions.items():
                    if qty > 0:
                        trade_before_rows.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            qty
                        ])

            # -------- 2. 生成买卖信号 --------
            buy_candidates = day_rsi[day_rsi < self.rsi_oversold].dropna().index.tolist()
            sell_candidates = day_rsi[day_rsi > self.rsi_overbought].dropna().index.tolist()

            # 先卖出
            for code in list(self.positions.keys()):
                if code in sell_candidates:
                    qty = self.positions.get(code, 0)
                    if qty <= 0:
                        continue
                    px = day_prices.get(code, np.nan)
                    if np.isnan(px) or px <= 0:
                        continue
                    gross = qty * px
                    fee = gross * self.fee_rate
                    self.cash += (gross - fee)
                    trade_after_rows.append([
                        self._format_date(date),
                        code,
                        px,
                        0
                    ])
                    self.positions.pop(code, None)
                    self.cost_basis.pop(code, None)

            # 重新计算可用现金
            available_cash = self.cash
            # 买入（只对当前未持有的标的开仓；如果想加仓可自行扩展）
            new_buys = [c for c in buy_candidates if c not in self.positions]

            if new_buys:
                alloc_each = available_cash / len(new_buys)
            else:
                alloc_each = 0

            for code in new_buys:
                px = day_prices.get(code, np.nan)
                if np.isnan(px) or px <= 0:
                    continue
                raw_qty = alloc_each // (px * self.min_trade_unit) * self.min_trade_unit
                qty = int(raw_qty)
                if qty <= 0:
                    continue
                cost = qty * px
                fee = cost * self.fee_rate
                total_cost = cost + fee
                if total_cost > self.cash + 1e-9:
                    continue
                self.cash -= total_cost
                self.positions[code] = qty
                self.cost_basis[code] = px
                trade_after_rows.append([
                    self._format_date(date),
                    code,
                    px,
                    qty
                ])

            # 补写仍持有但今天未记录 after 的标的（保持不变）
            recorded_after_codes = {r[1] for r in trade_after_rows if r[0] == self._format_date(date)}
            for code, qty in self.positions.items():
                if qty > 0 and code not in recorded_after_codes:
                    trade_after_rows.append([
                        self._format_date(date),
                        code,
                        self.cost_basis[code],
                        qty
                    ])

        trade_before_df = pd.DataFrame(trade_before_rows, columns=["交易时间", "标的", "价格", "数量"])
        trade_after_df = pd.DataFrame(trade_after_rows, columns=["交易时间", "标的", "价格", "数量"])
        trade_before_df.to_csv('trade_before.csv', index=False)
        trade_after_df.to_csv('trade_after.csv', index=False)
        return trade_before_df, trade_after_df