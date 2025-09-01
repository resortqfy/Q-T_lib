"""Unit tests for PNLCalculator class."""

import unittest
import pandas as pd
from core.pnl_calculator import PNLCalculator

class TestPNLCalculator(unittest.TestCase):
    def setUp(self):
        # 创建测试数据
        market_data = pd.DataFrame({
            'open': [10, 11, 12, 13, 14],
        }, index=pd.MultiIndex.from_tuples([
            (pd.to_datetime('2023-01-01'), '000001'),
            (pd.to_datetime('2023-01-02'), '000001'),
            (pd.to_datetime('2023-01-03'), '000001'),
            (pd.to_datetime('2023-01-04'), '000001'),
            (pd.to_datetime('2023-01-05'), '000001')
        ], names=['date', 'code']))
        trade_before = pd.DataFrame({
            '交易时间': [pd.to_datetime('2023-01-01'), pd.to_datetime('2023-01-03')],
            '标的': ['000001', '000001'],
            '价格': [10, 12],
            '数量': [200, 100]
        })
        trade_after = pd.DataFrame({
            '交易时间': [pd.to_datetime('2023-01-02'), pd.to_datetime('2023-01-04')],
            '标的': ['000001', '000001'],
            '价格': [11, 13],
            '数量': [100, 0]
        })
        self.calculator = PNLCalculator(market_data, trade_before, trade_after)

    def test_calculate_pnl(self):
        pnls = self.calculator.calculate_pnl()
        self.assertIsInstance(pnls, pd.DataFrame)
        self.assertIn('date', pnls.columns)
        self.assertIn('pnl', pnls.columns)
        self.assertIn('fee', pnls.columns)
        self.assertGreater(len(pnls), 0)

if __name__ == '__main__':
    unittest.main()
