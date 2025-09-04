import pandas as pd

class PNLCalculator:
    """
    计算每次交易产生的已实现 PNL 与手续费。
    
    假设:
    - trade_before 与 trade_after 各包含多个交易日期的快照。
    - 同一个交易日期在两个表中分别表示交易前、交易后的持仓状态。
    - 单标的卖出部分用 trade_before 的价格作为成本；卖出价格用 trade_after 的价格（若存在），
      若清仓后没有 after 记录则回退到 market_data 的开盘价 (或其他指定价格源)。
    - 买入不在当前时点产生已实现 PNL，只产生手续费。
    """
    def __init__(self, market_data: pd.DataFrame, trade_before: pd.DataFrame, trade_after: pd.DataFrame, 
                 fee_rate: float = 0.0006):
        """
        Parameters
        ----------
        market_data : DataFrame
            MultiIndex: (交易时间, 标的) 或包含列 ['交易时间','标的','open']，至少能提供 (date, code) -> open 价格
        trade_before : DataFrame
            列至少包含 ['交易时间','标的','价格','数量']
        trade_after : DataFrame
            列至少包含 ['交易时间','标的','价格','数量']
        fee_rate : float
            手续费率（双边）
        """
        # 若 market_data 不是 MultiIndex，转换
        if not isinstance(market_data.index, pd.MultiIndex):
            if set(['交易时间','标的']).issubset(market_data.columns):
                market_data = market_data.set_index(['交易时间','标的'])
            else:
                raise ValueError("market_data 需要 MultiIndex (交易时间, 标的) 或包含对应列。")
        self.market_data = market_data
        self.trade_before = trade_before.copy()
        self.trade_after = trade_after.copy()
        self.fee_rate = fee_rate

    def _get_price_from_market(self, date, code):
        """兜底价格：用 market_data 的 open。若缺失返回 None。"""
        try:
            return self.market_data.loc[(date, code), 'open']
        except KeyError:
            return None

    def calculate_pnl(self, return_details: bool = True) -> pd.DataFrame:
        """
        按交易日期计算当次交易的已实现 PNL、手续费与总 PNL。
        
        Returns
        -------
        DataFrame
            列包含:
            - 交易时间
            - realized_pnl
            - fee
            - total_pnl
            - details (可选，包含每个标的的明细 list[dict])
        """
        results = []
        # 仅处理两个表都出现的日期（如果需要 union 可改）
        dates = sorted(set(self.trade_before['交易时间']).intersection(set(self.trade_after['交易时间'])))

        for date in dates:
            before_df = self.trade_before[self.trade_before['交易时间'] == date]
            after_df = self.trade_after[self.trade_after['交易时间'] == date]
            if before_df.empty and after_df.empty:
                continue

            before_map_qty = dict(zip(before_df['标的'], before_df['数量']))
            before_map_price = dict(zip(before_df['标的'], before_df['价格']))

            after_map_qty = dict(zip(after_df['标的'], after_df['数量']))
            after_map_price = dict(zip(after_df['标的'], after_df['价格']))

            symbols = set(before_map_qty.keys()).union(after_map_qty.keys())

            realized_pnl = 0.0
            total_fee = 0.0
            symbol_details = []

            for code in symbols:
                qty_before = before_map_qty.get(code, 0)
                qty_after = after_map_qty.get(code, 0)
                delta = qty_after - qty_before

                # 无变动
                if delta == 0:
                    continue

                # 买入
                if delta > 0:
                    buy_qty = delta
                    buy_price = after_map_price.get(code)
                    if buy_price is None:
                        # 兜底用市场价格
                        buy_price = self._get_price_from_market(date, code)
                        if buy_price is None:
                            raise ValueError(f"{date} {code} 买入无法获取价格")
                    buy_amount = buy_qty * buy_price
                    fee = buy_amount * self.fee_rate
                    total_fee += fee
                    symbol_details.append({
                        '标的': code,
                        '动作': '买入',
                        '数量': buy_qty,
                        '成交价': buy_price,
                        '卖出成本价': None,
                        '卖出价': None,
                        '该标的已实现PNL': 0.0,
                        '手续费': fee
                    })

                # 卖出
                else:
                    sell_qty = -delta  # delta < 0
                    cost_price = before_map_price.get(code)
                    if cost_price is None:
                        raise ValueError(f"{date} {code} 无法找到卖出持仓的成本价 (trade_before 缺失)")
                    # 卖出价
                    sell_price = after_map_price.get(code)
                    # 若完全清仓后 after 没有此标的
                    if sell_price is None:
                        sell_price = self._get_price_from_market(date, code)
                        if sell_price is None:
                            raise ValueError(f"{date} {code} 卖出无法找到成交价( after 缺失且 market_data 缺失 )")

                    sell_amount = sell_qty * sell_price
                    fee = sell_amount * self.fee_rate
                    pnl_symbol = (sell_price - cost_price) * sell_qty
                    realized_pnl += pnl_symbol
                    total_fee += fee
                    symbol_details.append({
                        '标的': code,
                        '动作': '卖出',
                        '数量': sell_qty,
                        '成交价': sell_price,
                        '卖出成本价': cost_price,
                        '卖出价': sell_price,
                        '该标的已实现PNL': pnl_symbol,
                        '手续费': fee
                    })

            total_pnl = realized_pnl - total_fee
            row = {
                '交易时间': date,
                'realized_pnl': realized_pnl,
                'fee': total_fee,
                'total_pnl': total_pnl
            }
            if return_details:
                row['details'] = symbol_details
            results.append(row)

        return pd.DataFrame(results)
