import os
import pandas as pd
import numpy as np

class TradingStrategy:
    """
    动量等权调仓策略：
    - 依据过去 lookback_period 天开盘价收益率选取 top_n 标的等权持有
    - 生成 trade_before（调仓前成本快照）与 trade_after（调仓后成交结果）
    
    trade_before: 每个有调仓动作的日期（或已有持仓的日期），记录当日开盘前持仓（价格=成本）
    trade_after : 当日调仓完成后的持仓；卖光的标的写数量=0 且价格=成交价；部分卖出/买入的标的价格为成交价；未变化保留成本价
    
    内部状态:
    - positions: {code -> quantity}
    - cost_basis: {code -> average cost}
    - cash: 剩余现金
    
    注意：
    - 手续费 (0.0006) 这里扣在现金上（用于资金约束），但在 PNLCalculator 中仍会重新计算交易金额来求 fee。
      如果你不希望双重计算，可在 PNL 端去掉手续费，或这里改为不扣手续费（把 fee_sell / fee_buy 设为 0）。
    """
    def __init__(self,
                 market_data: pd.DataFrame,
                 initial_capital: float = 100000.0,
                 min_trade_unit: int = 100,
                 lookback_period: int = 30,
                 top_n: int = 3,
                 fee_rate: float = 0.0006):
        """
        Parameters
        ----------
        market_data : MultiIndex DataFrame (date, code)，至少包含列 ['open']
        initial_capital : 初始资金
        min_trade_unit : 最小交易单位（整数股），下取整到该单位倍数
        lookback_period : 动量回看天数
        top_n : 选择的标的数量
        fee_rate : 手续费率（双边）
        """
        if not isinstance(market_data.index, pd.MultiIndex):
            raise ValueError("market_data 必须是 MultiIndex (date, code)")
        if 'open' not in market_data.columns:
            raise ValueError("market_data 需要包含列 'open'")
        self.market_data = market_data.sort_index()
        self.initial_capital = initial_capital
        self.min_trade_unit = min_trade_unit
        self.lookback_period = lookback_period
        self.top_n = top_n
        self.fee_rate = fee_rate

        self.positions = {}      # code -> qty
        self.cost_basis = {}     # code -> avg cost
        self.cash = initial_capital

    # ----------------- 内部工具方法 -----------------
    def _format_date(self, date_val):
        """输出 yyyymmdd 字符串"""
        if isinstance(date_val, (pd.Timestamp, np.datetime64)):
            return pd.Timestamp(date_val).strftime("%Y%m%d")
        s = str(date_val)
        if '-' in s:
            return s.replace('-', '')
        return s

    def _select_universe(self, date):
        """返回当日所有 code 的开盘价 Series"""
        try:
            day_slice = self.market_data.loc[date]
            return day_slice['open']
        except KeyError:
            return pd.Series(dtype=float)

    def _compute_momentum(self):
        """计算过去 lookback_period 天的开盘价收益率表 (date x code)"""
        open_px = self.market_data['open'].unstack('code')
        returns = open_px.pct_change(self.lookback_period)
        return returns

    # ----------------- 主逻辑 -----------------
    def generate_trades(self,
                        save_csv: bool = False,
                        output_dir: str = ".",
                        before_filename: str = "trade_before.csv",
                        after_filename: str = "trade_after.csv",
                        overwrite: bool = True):
        """
        生成调仓前/后 DataFrame（并可选保存为 CSV）
        
        Parameters
        ----------
        save_csv : 是否保存 CSV
        output_dir : 输出目录
        before_filename : before CSV 文件名
        after_filename : after CSV 文件名
        overwrite : True 覆盖写；False 追加（注意避免重复日期）
        
        Returns
        -------
        trade_before_df, trade_after_df
        """
        returns = self._compute_momentum()
        all_dates = returns.index

        trade_before_rows = []
        trade_after_rows = []

        for date in all_dates:
            daily_rets = returns.loc[date]
            # 若该日没有可用动量（需要累计 lookback_period），跳过
            if daily_rets.isna().all():
                continue

            # ========== 1. 记录 before 快照（已有持仓才写） ==========
            if self.positions:
                for code, qty in self.positions.items():
                    if qty > 0:
                        trade_before_rows.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            qty
                        ])

            # ========== 2. 选出 top_n ==========
            valid_rets = daily_rets.dropna()
            if valid_rets.empty:
                # 无可选标的，这里继续；after 只会在卖出或变化时记录
                continue
            top_codes = valid_rets.nlargest(min(self.top_n, len(valid_rets))).index.tolist()

            # ========== 3. 计算当前总资产（按今日 open 估值） ==========
            day_prices = self._select_universe(date)
            portfolio_value = self.cash
            for code, qty in self.positions.items():
                if qty > 0 and code in day_prices.index:
                    portfolio_value += qty * day_prices.loc[code]

            if portfolio_value <= 0:
                # 理论不应出现，兜底：写 after= before
                for code, qty in self.positions.items():
                    if qty > 0:
                        trade_after_rows.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            qty
                        ])
                continue

            target_weight = 1.0 / len(top_codes)
            # ========== 4. 计算目标持仓股数 ==========
            target_positions = {}
            for code in top_codes:
                if code not in day_prices.index:
                    continue
                px = day_prices.loc[code]
                alloc_cash = portfolio_value * target_weight
                # 下取整到最小单位
                raw_qty = alloc_cash // (px * self.min_trade_unit) * self.min_trade_unit
                qty = int(raw_qty)
                if qty > 0:
                    target_positions[code] = qty

            # ========== 5. 根据差异生成交易 ==========
            all_codes = set(self.positions.keys()).union(target_positions.keys())
            after_snapshot = []

            for code in all_codes:
                prev_qty = self.positions.get(code, 0)
                new_qty = target_positions.get(code, 0)

                if code not in day_prices.index:
                    # 当日没有价格 => 不交易
                    new_qty = prev_qty

                if prev_qty == new_qty:
                    # 不变：保持成本价
                    if new_qty > 0:
                        after_snapshot.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            new_qty
                        ])
                    continue

                px = day_prices.get(code, np.nan)
                if np.isnan(px) or px <= 0:
                    # 价格异常，放弃调整
                    if prev_qty > 0:
                        after_snapshot.append([
                            self._format_date(date),
                            code,
                            self.cost_basis[code],
                            prev_qty
                        ])
                    continue

                # ---------- 卖出 ----------
                if new_qty < prev_qty:
                    sell_qty = prev_qty - new_qty
                    sell_amount = sell_qty * px
                    fee_sell = sell_amount * self.fee_rate
                    self.cash += (sell_amount - fee_sell)

                    if new_qty == 0:
                        # 全部卖出 -> 数量=0, 价格=成交价
                        after_snapshot.append([
                            self._format_date(date),
                            code,
                            px,
                            0
                        ])
                        self.positions.pop(code, None)
                        self.cost_basis.pop(code, None)
                    else:
                        # 部分卖出 -> after 行写剩余数量 & 卖出价
                        after_snapshot.append([
                            self._format_date(date),
                            code,
                            px,
                            new_qty
                        ])
                        self.positions[code] = new_qty
                    continue

                # ---------- 买入 ----------
                if new_qty > prev_qty:
                    buy_qty = new_qty - prev_qty
                    buy_amount = buy_qty * px
                    fee_buy = buy_amount * self.fee_rate
                    total_cost = buy_amount + fee_buy

                    if total_cost > self.cash + 1e-9:
                        # 资金不足，回退买入数量
                        affordable_qty = int(
                            (self.cash / (px * (1 + self.fee_rate))) //
                            self.min_trade_unit * self.min_trade_unit
                        )
                        if affordable_qty <= 0:
                            # 买不起
                            if prev_qty > 0:
                                after_snapshot.append([
                                    self._format_date(date),
                                    code,
                                    self.cost_basis[code],
                                    prev_qty
                                ])
                            continue
                        new_qty = prev_qty + affordable_qty
                        buy_qty = affordable_qty
                        buy_amount = buy_qty * px
                        fee_buy = buy_amount * self.fee_rate
                        total_cost = buy_amount + fee_buy

                    self.cash -= total_cost

                    # 更新成本价（加权平均）
                    if prev_qty > 0:
                        old_cost = self.cost_basis[code]
                        old_val = old_cost * prev_qty
                        new_cost = (old_val + buy_amount) / (prev_qty + buy_qty)
                        self.cost_basis[code] = new_cost
                    else:
                        self.cost_basis[code] = px

                    self.positions[code] = new_qty

                    after_snapshot.append([
                        self._format_date(date),
                        code,
                        px,     # 买入成交价
                        new_qty
                    ])

            # 补齐未记录但仍持有的标的（理论上都已包含）
            recorded = {r[1] for r in after_snapshot}
            for code, qty in self.positions.items():
                if code not in recorded and qty > 0:
                    after_snapshot.append([
                        self._format_date(date),
                        code,
                        self.cost_basis[code],
                        qty
                    ])

            after_snapshot.sort(key=lambda x: x[1])
            trade_after_rows.extend(after_snapshot)

        trade_before_df = pd.DataFrame(trade_before_rows, columns=["交易时间", "标的", "价格", "数量"])
        trade_after_df = pd.DataFrame(trade_after_rows, columns=["交易时间", "标的", "价格", "数量"])
        trade_before_df.to_csv('trade_before.csv', index=False)
        trade_after_df.to_csv('trade_after.csv', index=False)
      
        return trade_before_df, trade_after_df

   