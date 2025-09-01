"""Unit tests for trading strategies."""

import unittest
import pandas as pd
from strategies.momentum_strategy import TradingStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy

class TestStrategies(unittest.TestCase):
    def setUp(self):
        # 创建测试数据
        market_data = pd.DataFrame({
            'open': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        }, index=pd.MultiIndex.from_tuples([
            (pd.to_datetime('2023-01-01'), '000001'),
            (pd.to_datetime('2023-01-02'), '000001'),
            (pd.to_datetime('2023-01-03'), '000001'),
            (pd.to_datetime('2023-01-04'), '000001'),
            (pd.to_datetime('2023-01-05'), '000001'),
            (pd.to_datetime('2023-01-01'), '000002'),
            (pd.to_datetime('2023-01-02'), '000002'),
            (pd.to_datetime('2023-01-03'), '000002'),
            (pd.to_datetime('2023-01-04'), '000002'),
            (pd.to_datetime('2023-01-05'), '000002')
        ], names=['date', 'code']))
        self.momentum_strategy = TradingStrategy(market_data)
        self.mean_reversion_strategy = MeanReversionStrategy(market_data)

    def test_momentum_strategy_generate_trades(self):
        trades_before, trades_after = self.momentum_strategy.generate_trades()
        self.assertIsInstance(trades_before, pd.DataFrame)
        self.assertIsInstance(trades_after, pd.DataFrame)
        self.assertIn('交易时间', trades_before.columns)
        self.assertIn('标的', trades_before.columns)
        self.assertIn('价格', trades_before.columns)
        self.assertIn('数量', trades_before.columns)
        self.assertIn('交易时间', trades_after.columns)
        self.assertIn('标的', trades_after.columns)
        self.assertIn('价格', trades_after.columns)
        self.assertIn('数量', trades_after.columns)

    def test_mean_reversion_strategy_generate_trades(self):
        trades_before, trades_after = self.mean_reversion_strategy.generate_trades()
        self.assertIsInstance(trades_before, pd.DataFrame)
        self.assertIsInstance(trades_after, pd.DataFrame)
        self.assertIn('交易时间', trades_before.columns)
        self.assertIn('标的', trades_before.columns)
        self.assertIn('价格', trades_before.columns)
        self.assertIn('数量', trades_before.columns)
        self.assertIn('交易时间', trades_after.columns)
        self.assertIn('标的', trades_after.columns)
        self.assertIn('价格', trades_after.columns)
        self.assertIn('数量', trades_after.columns)

if __name__ == '__main__':
    unittest.main()
