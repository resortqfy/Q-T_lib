"""Mean Reversion Strategy module.

This module contains the MeanReversionStrategy class for generating trades based on mean reversion.
"""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略 (改进版)

    逻辑：
    1. 计算各标的 rolling mean / std，得到 z-score = (price - mean) / std
    2. 若 z < -threshold 视为低估 -> 目标持仓
    3. 若 z >  threshold 视为高估 -> 强制卖出
    4. 其他未进入低估集合的旧持仓也可选择卖出（这里实现为：如果不再低估则平仓，体现纯粹回归）
       如你想“持有到均值”可改为：只在 z > threshold 时卖出。

    输出：
    - trade_before: 当日调仓前的全部持仓（成本价）
    - trade_after : 当日调仓后的全部持仓（卖出写数量=0，价格=卖出价；持有不变写成本价；新买写买入价）
    """

    def __init__(self,
                 market_data: pd.DataFrame,
                 initial_capital: float = 100000,
                 min_trade_unit: int = 100,
                 window: int = 20,
                 threshold: float = 2.0,
                 fee_rate: float = 0.0006):
        super().__init__(name="MeanReversionStrategy")
        if not isinstance(market_data.index, pd.MultiIndex):
            raise ValueError("market_data 必须是 MultiIndex (date, code)")
        if 'open' not in market_data.columns:
            raise ValueError("market_data 需要包含列 'open'")
        self.market_data = market_data.sort_index()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.min_trade_unit = min_trade_unit
        self.window = window
        self.threshold = threshold
        self.fee_rate = fee_rate

        # 持仓与成本
        self.positions = {}     # code -> qty
        self.cost_basis = {}    # code -> avg cost
        self.cash = initial_capital

    def _format_date(self, date_val):
        if isinstance(date_val, (pd.Timestamp, np.datetime64)):
            return pd.Timestamp(date_val).strftime("%Y%m%d")
        s = str(date_val)
        if '-' in s:
            return s.replace('-', '')
        return s

    def generate_trades(self):
        # 构造 (date x code) 的开盘价透视
        prices = self.market_data['open'].unstack('code')
        # rolling 计算
        mean_prices = prices.rolling(window=self.window, min_periods=self.window).mean()
        std_prices = prices.rolling(window=self.window, min_periods=self.window).std()

        all_dates = prices.index
        max_date = self.market_data.index.get_level_values('date').max()
        all_dates = all_dates[all_dates <= max_date]

        trade_before_rows = []
        trade_after_rows = []

        for date in all_dates:
            # 跳过尚未形成完整窗口的日期
            if date not in mean_prices.index:
                continue
            if pd.isna(mean_prices.loc[date]).all():
                continue

            day_prices = prices.loc[date]
            day_mean = mean_prices.loc[date]
            day_std = std_prices.loc[date]

            # 计算 z-score
            z_scores = (day_prices - day_mean) / day_std
            # 去掉 std=0 的项（导致 NaN 或 inf）
            z_scores = z_scores.replace([np.inf, -np.inf], np.nan).dropna()

            # ========== 1. before 快照 ==========
            if self.positions:
                for code, qty in self.positions.items():
                    if qty > 0:
                        trade_before_rows.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            qty
                        ])

            if z_scores.empty:
                # 无法决策，当天 after 也需要写出（维持不变）
                if self.positions:
                    for code, qty in self.positions.items():
                        trade_after_rows.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            qty
                        ])
                continue

            # 低估与高估集合
            undervalued = z_scores[z_scores < -self.threshold].index.tolist()
            overvalued = z_scores[z_scores > self.threshold].index.tolist()

            # 策略：仅持有当天仍在低估集合的标的（体现“等反弹”思想）
            target_set = set(undervalued)

            # 计算今日总资产（用于等权分配）
            portfolio_value = self.cash
            for code, qty in self.positions.items():
                px = day_prices.get(code, np.nan)
                if qty > 0 and not np.isnan(px):
                    portfolio_value += qty * px

            # 需要买入的标的列表
            buy_codes = [c for c in undervalued if c not in self.positions]

            # 需要卖出的标的：1) 高估 2) 不在低估集合里（若你想只在 overvalued 卖出，可改成：set(overvalued)）
            sell_codes = [c for c in self.positions.keys() if c not in target_set or c in overvalued]

            # 先执行卖出
            for code in sell_codes:
                prev_qty = self.positions.get(code, 0)
                if prev_qty <= 0:
                    continue
                px = day_prices.get(code, np.nan)
                if np.isnan(px) or px <= 0:
                    # 无法成交，保留原持仓（写 after 维持原样）
                    continue
                gross = prev_qty * px
                fee = gross * self.fee_rate
                self.cash += (gross - fee)
                # 记录 after 行：数量=0, 价格=卖出价
                trade_after_rows.append([
                    self._format_date(date),
                    code,
                    px,
                    0
                ])
                # 移除持仓
                self.positions.pop(code, None)
                self.cost_basis.pop(code, None)

            # 更新 portfolio 价值（卖出后）
            portfolio_value = self.cash
            for code, qty in self.positions.items():
                px = day_prices.get(code, np.nan)
                if qty > 0 and not np.isnan(px):
                    portfolio_value += qty * px

            # 给剩余/新目标的可买入资金（这里可以只对新买入做分配；老持仓保持不变）
            # 资金分配：把当前现金按等权分给“需要新建仓”的标的
            if buy_codes:
                alloc_cash_each = self.cash / len(buy_codes)
            else:
                alloc_cash_each = 0

            # 执行买入
            for code in buy_codes:
                px = day_prices.get(code, np.nan)
                if np.isnan(px) or px <= 0:
                    continue
                raw_qty = alloc_cash_each // (px * self.min_trade_unit) * self.min_trade_unit
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

            # 为仍然持有且今天未写入 after 的标的补行（保持不变）
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
